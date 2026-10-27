#!/usr/bin/env python3
"""Thermal report as Word + PDF, with figures and a heat-up video.

    <venv>/bin/python make_report.py CASE_DIR            # after a CFD run
    <venv>/bin/python make_report.py case.yaml --out DIR  # hand calc only (no CFD sections)

Needs the skill's environment (scripts/setup_env.sh: pyvista, python-docx, matplotlib,
imageio) and LibreOffice for the PDF. Writes into <case>-report/ next to the case (or --out):
  thermal-report.docx, thermal-report.pdf, heatup.mp4, figures/*.png, warmup.csv, and copies of
  case.yaml, case-meta.json and report.md. The case folder itself is tagged as a cache
  (CACHEDIR.TAG) and left out of backups; this folder is what gets backed up.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import textwrap
import sys
from pathlib import Path

# Render through EGL (GPU, no X server). Through X/GLX the renders failed with BadAlloc while the
# desktop and a CFD run were using the GPU; EGL needs no display. Override by setting the
# variable yourself (vtkOSOpenGLRenderWindow needs libOSMesa installed).
os.environ.setdefault("VTK_DEFAULT_OPENGL_WINDOW", "vtkEGLRenderWindow")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cooling_model import MM, load_config, network  # noqa: E402
from make_case import solids  # noqa: E402
import warmup  # noqa: E402

COLORS = {"heatsink": "#b8bec6", "ims": "#3f8f5a", "device": "#1d1d1f", "solid": "#d98c2b"}
CMAP = "inferno"


# ---------------------------------------------------------------- helpers

def c(v):
    return v - 273.15


def part_color(name, cfg):
    if name in {d.name for d in cfg.devices}:
        return COLORS["device"]
    if name in {p["name"] for p in cfg.solids}:
        return COLORS["solid"]
    if name in {i["name"] for i in cfg.ims.get("islands", [])}:
        return COLORS["ims"]                 # board copper, like the rest of the spreader
    return COLORS.get(name, "#888888")


def layer_text(l):
    """'top Cu 70 um, 390 W/mK' for one board layer (dict with name, t in m, k), or
    'dry contact, R'' 3.3e-04 m2K/W' for a layer given as a resistance per area."""
    if "R" in l:
        return f"{l['name']}, R'' {l['R']:.2g} m2K/W"
    return f"{l['name']} {l['t'] / 1e-6:.0f} um, {l['k']:.3g} W/mK"


def layer_color(name):
    n = name.lower()
    if "solder" in n:
        return "#c9c9c9", "k"
    if any(w in n for w in ("prepreg", "dielectric", "insulat", "laminate", "fr4")):
        return "#e8d36a", "k"
    if any(w in n for w in ("contact", "tim", "paste", "pad", "grease")):
        return "#8fb3d9", "k"
    if "cu" in n.split() or "copper" in n:
        return "#c87533", "w"
    return "#e8d36a", "k"


def spreader_label(cfg):
    sp = cfg.ims["spreader"]
    return f"{sp['name']} {sp['t'] / MM:g} mm"


def gates_from_report(case: Path):
    """Run report.py and read its checks table back (one source of truth for the gates)."""
    subprocess.run([sys.executable, str(HERE / "report.py"), str(case), "--quiet"], check=False)
    rows, verdict = [], ""
    md = (case / "report.md").read_text() if (case / "report.md").exists() else ""
    in_checks = False
    for line in md.splitlines():
        if line.startswith("## Checks"):
            in_checks = True
            continue
        if in_checks and line.startswith("| ") and not line.startswith("| Check") and "---" not in line:
            cells = [x.strip() for x in line.strip("|").split("|")]
            rows.append(cells[:3])
        if line.startswith("Verdict:"):
            verdict = line.removeprefix("Verdict:").strip()
    return rows, verdict


def check_assumptions(yaml_path: Path):
    """Lines of the YAML marked '# CHECK' -> human-readable list."""
    out = []
    for line in yaml_path.read_text().splitlines():
        if "CHECK" in line and "#" in line:
            code, comment = line.split("#", 1)
            key = code.strip().rstrip(":").strip()
            out.append(f"{key or '(see file)'}: {comment.replace('CHECK:', '').strip()}")
    return out


# ---------------------------------------------------------------- figures: geometry

def fig_layout(cfg, path: Path):
    boxes = solids(cfg)
    s = cfg.sink
    fig, ax = plt.subplots(1, 3, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1.0, 1.25, 0.7]})

    # (a) back view, y-z: where the parts sit on the sink
    a = ax[0]
    a.add_patch(plt.Rectangle((0, 0), s["width"] / MM, s["length"] / MM, fc=COLORS["heatsink"], ec="k"))
    for name in ["ims"] + [d.name for d in cfg.devices]:
        (x0, x1), (y0, y1), (z0, z1) = boxes[name][0]
        a.add_patch(plt.Rectangle((y0 / MM, z0 / MM), (y1 - y0) / MM, (z1 - z0) / MM,
                                  fc=part_color(name, cfg), ec="k", lw=0.8, alpha=0.95))
        if name != "ims":
            a.text((y0 + y1) / 2 / MM, (z0 + z1) / 2 / MM, name, color="w", ha="center", va="center",
                   fontsize=9, weight="bold")
    for p in cfg.solids:                     # lugs, cables ...: outlines, they sit above the parts
        for (x0, x1), (y0, y1), (z0, z1) in boxes[p["name"]]:
            a.add_patch(plt.Rectangle((y0 / MM, z0 / MM), (y1 - y0) / MM, (z1 - z0) / MM,
                                      fill=False, ec=COLORS["solid"], lw=1.2))
    (_, _), (iy0, iy1), (iz0, iz1) = boxes["ims"][0]
    a.text((iy0 + iy1) / 2 / MM, iz1 / MM + 3, cfg.ims["label"], ha="center", va="bottom", fontsize=9)
    a.annotate("", xy=(-8, s["length"] / MM), xytext=(-8, 0), arrowprops=dict(arrowstyle="<->"))
    a.text(-13, s["length"] / MM / 2, f"{s['length'] / MM:.0f} mm", rotation=90, ha="right", va="center",
           backgroundcolor="w")
    a.annotate("", xy=(s["width"] / MM, -8), xytext=(0, -8), arrowprops=dict(arrowstyle="<->"))
    a.text(s["width"] / MM / 2, -11, f"{s['width'] / MM:.0f} mm", ha="center", va="top")
    a.annotate("air", xy=(s["width"] / MM + 12, s["length"] / MM * 0.8),
               xytext=(s["width"] / MM + 12, s["length"] / MM * 0.2),
               arrowprops=dict(arrowstyle="->", color="tab:blue", lw=2), color="tab:blue", ha="center")
    a.set_title("Back view (mounting face): device placement")
    a.set_xlabel("y (mm)")
    a.set_ylabel("z, up (mm)")

    # (b) section seen from above, x-y: fin comb, base, board spreader, packages
    b = ax[1]
    for name, bxs in boxes.items():
        for (x0, x1), (y0, y1), _ in bxs:
            b.add_patch(plt.Rectangle((y0 / MM, x0 / MM), (y1 - y0) / MM, (x1 - x0) / MM,
                                      fc=part_color(name, cfg), ec="k", lw=0.5))
    b.text(s["width"] / MM / 2, (s["base"] + s["fin_h"]) / MM + 2,
           f"{s['n_fins']} fins x {s['fin_t'] / MM:g} mm, gap {s['gap'] / MM:.1f} mm, "
           f"height {s['fin_h'] / MM:g} mm", ha="center", va="bottom", fontsize=9)
    b.text(s["width"] / MM + 3, s["base"] / MM / 2, f"base {s['base'] / MM:g} mm", va="center", fontsize=9)
    b.set_title("Section through the devices, seen from above")
    b.set_xlabel("y (mm)")
    b.set_ylabel("x, out of the fins (mm)")

    # (c) stack-up, not to scale: the layers the heat crosses
    st = ax[2]
    im = cfg.ims
    sp = im["spreader"]
    layers = ([("Package (Rth j-c " + f"{cfg.devices[0].rth_jc:g} K/W)", COLORS["device"], "w")]
              + [(layer_text(l), *layer_color(l["name"])) for l in im["under"]]
              + [(f"{spreader_label(cfg)}, {sp['k']:g} W/mK (meshed spreader)", COLORS["ims"], "w")]
              + [(layer_text(l), *layer_color(l["name"])) for l in im["below"]]
              + [(f"Heat sink base {s['base'] / MM:g} mm + fins", COLORS["heatsink"], "k")])
    for i, (txt, fc, tc) in enumerate(layers):
        y = len(layers) - i
        st.add_patch(plt.Rectangle((0, y), 1, 0.9, fc=fc, ec="k"))
        st.text(0.5, y + 0.45, textwrap.fill(txt, 30), ha="center", va="center", color=tc, fontsize=8,
                linespacing=1.1)
    st.annotate("heat", xy=(1.08, 1.4), xytext=(1.08, len(layers) + 0.5),
                arrowprops=dict(arrowstyle="->", color="tab:red", lw=2), color="tab:red", rotation=90,
                va="top", ha="left")
    st.set_xlim(-0.05, 1.3)
    st.set_ylim(0.8, len(layers) + 1)
    st.axis("off")
    st.set_title("Stack-up (not to scale)")

    for a_ in ax[:2]:
        a_.set_aspect("equal")
        a_.autoscale_view()
        a_.margins(0.08)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _pv():
    import pyvista as pv
    pv.OFF_SCREEN = True
    return pv


def frame(p, direction, zoom=1.25):
    """Look along `direction` (from camera towards the scene), fit everything, then zoom in."""
    p.camera_position = [tuple(np.array(direction) * 1000.0), (0, 0, 0), (0, 0, 1)]
    p.reset_camera()
    p.camera.zoom(zoom)


def fig_assembly_3d(cfg, path: Path):
    pv = _pv()
    boxes = solids(cfg)
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1600, 700), border=False)
    for col, (view, title) in enumerate([((1, -1.2, 0.8), "Fin side"), ((-1, -1.2, 0.7), "Device side")]):
        p.subplot(0, col)
        for name, bxs in boxes.items():
            for (x0, x1), (y0, y1), (z0, z1) in bxs:
                p.add_mesh(pv.Box(bounds=(x0 / MM, x1 / MM, y0 / MM, y1 / MM, z0 / MM, z1 / MM)),
                           color=part_color(name, cfg), smooth_shading=False, show_edges=False)
        p.add_text(title, font_size=12)
        frame(p, view)
        p.add_axes(line_width=2, labels_off=False)
    p.screenshot(str(path))
    p.close()


# ---------------------------------------------------------------- figures: CFD

def load_cfd(case: Path):
    pv = _pv()
    vtk = case / "VTK"
    regions = {}
    for rdir in sorted(p for p in vtk.iterdir() if p.is_dir()):
        steps = sorted((p for p in rdir.glob("case_*") if p.is_dir()),
                       key=lambda p: float(p.name.split("_")[1]))
        if steps and (steps[-1] / "internal.vtu").exists():
            m = pv.read(str(steps[-1] / "internal.vtu"))
            m = m.cell_data_to_point_data() if "T" in m.cell_data and "T" not in m.point_data else m
            regions[rdir.name] = m
    return regions


def solid_meshes(regions):
    """Solid regions in mm with their steady temperature in C as 'Tss'."""
    out = {}
    for name, m in regions.items():
        if name == "air":
            continue
        mm = m.copy()
        mm.points *= 1 / MM
        mm.point_data["Tss"] = mm.point_data["T"] - 273.15
        out[name] = mm
    return out


def warmup_node(cfg, name):
    """The warm-up curve a region follows in the video: sink, board (spreader and islands),
    its own device node, or for an extra solid the device it hangs on (else the board)."""
    if name == "heatsink":
        return "T_sink_C"
    if name in {d.name for d in cfg.devices}:
        return f"T_case_{name}_C"
    part = next((p for p in cfg.solids if p["name"] == name), None)
    dev = warmup.attached_to(cfg, part) if part else None
    return f"T_case_{dev}_C" if dev else "T_ims_C"


# ---------------------------------------------------------------- IR-camera style
# A thermal camera's palette (grey for cool, magenta, red-orange, orange, yellow, pale yellow),
# auto-ranged like a camera from the coldest to the hottest point in view. report: in the YAML
# sets the view: view_up z | -z (which way is up on screen), mirror (flip left-right, e.g. to
# match a photo of a board the model has mirrored), ir_floor_K (bottom of the scale above
# ambient; a camera sees the room a few K above the air), ir_range [lo, hi] C (fixed scale).
IR = matplotlib.colors.LinearSegmentedColormap.from_list("ir", [
    (0.000, "#d4d4d4"), (0.383, "#8c8c8c"), (0.432, "#a0158f"), (0.523, "#c8178f"),
    (0.613, "#e5306a"), (0.697, "#f2541f"), (0.779, "#ff7a10"), (0.863, "#ffa500"),
    (0.940, "#ffd21a"), (1.000, "#fff9b0")])
IR_OVER, IR_UNDER = "#ffffff", "#d4d4d4"
STYLE = {"style": "ir", "view_up": "z", "mirror": False, "ir_floor_K": 0.0, "ir_range": None, "ir_blur_mm": 1.0,
         "ir_edges": True, "ir_board_blur_mm": 3.0}


def ir_clim(Ta, tmax):
    if STYLE["ir_range"]:
        return tuple(STYLE["ir_range"])
    return (Ta + STYLE["ir_floor_K"], tmax + 0.3)


def _gauss_blur(a, sigma_px):
    """Separable Gaussian blur of a 2D array (numpy only)."""
    r = max(1, int(3 * sigma_px))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_px) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, a)


def render_side(cfg, pv, meshes, scalars, clim, side, size=(900, 700)):
    """Orthographic view square onto the component side (side -1) or the fins (+1), as a
    thermal camera would show it.

    The temperature is rendered as a linear grey image (lighting off), turned back into
    temperature, blurred over STYLE['ir_blur_mm'] (default 1 mm: a camera sees the surface,
    where solder mask, top copper and prepreg spread heat sideways over the steps the CFD
    has inside the board at slots and layers, plus its own optical blur), and only then
    coloured. The blur is weighted by the parts' mask, so the background does not bleed into
    the board edges. It is a display effect; the CFD numbers are not changed."""
    lo, hi = clim[0] - 25.0, clim[1] + 5.0                 # grey range: a little beyond the colours
    grey = matplotlib.colors.LinearSegmentedColormap.from_list("g", ["#010101", "#ffffff"])
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("black")
    for mm in meshes.values():
        p.add_mesh(mm, scalars=scalars, cmap=grey, clim=(lo, hi), show_scalar_bar=False,
                   lighting=False, interpolate_before_map=True)
    _ir_camera(p, cfg, side, size)
    g = p.screenshot(return_img=True)[..., :3].astype(float).mean(axis=2)
    px_per_mm = size[1] / (2 * p.camera.parallel_scale)
    p.close()
    mask = (g >= 0.5).astype(float)                         # parts (the background is black)
    T = lo + (np.clip(g, 1, 255) - 1) / 254 * (hi - lo)
    # The outermost pixel ring is anti-aliased against the black background and reads cold:
    # take only pixels whose 8 neighbours are parts as data, and fill the ring from them.
    valid = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            valid = np.minimum(valid, np.roll(np.roll(mask, dy, 0), dx, 1))
    # Two blur widths: the board's surface (solder mask over top copper and prepreg, on a
    # continuous bottom copper plane and the sink base) smooths the steps between copper islands
    # over several mm (ir_board_blur_mm, default 3); parts are separate objects, blurred only
    # by the camera optics (ir_blur_mm, default 1). Each is blurred within its own area.
    ids, board = part_ids(cfg, pv, side, size)
    out = T.copy()
    for area, mm_ in ((board, STYLE.get("ir_board_blur_mm", 3.0)), (~board, STYLE.get("ir_blur_mm", 1.0))):
        v = valid * area
        if not v.any():
            continue
        sigma = max(float(mm_) * px_per_mm, 1.0)
        b = _gauss_blur(T * v, sigma) / np.maximum(_gauss_blur(v, sigma), 1e-6)
        out = np.where((mask > 0) & area, b, out)
    T = out
    cmap = IR.with_extremes(over=IR_OVER, under=IR_UNDER)
    img = (cmap(matplotlib.colors.Normalize(*clim)(T))[..., :3] * 255).astype(np.uint8)
    img[mask == 0] = (np.array(matplotlib.colors.to_rgb(IR_UNDER)) * 255).astype(np.uint8)
    if STYLE.get("ir_edges", True):                        # "photo mode": part outlines on top
        e = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
        e[0, :] = e[:, 0] = False
        e = e | np.roll(e, 1, 0) | np.roll(e, 1, 1)         # 2 px lines
        img[e] = (img[e] * 0.35).astype(np.uint8)
    return np.fliplr(img) if STYLE["mirror"] else img


def _ir_camera(p, cfg, side, size):
    """Orthographic camera square onto the component side (side -1) or the fins (+1)."""
    s = cfg.sink
    W, L = s["width"] / MM, s["length"] / MM
    up = (0, 0, -1) if STYLE["view_up"] == "-z" else (0, 0, 1)
    p.enable_parallel_projection()
    p.camera_position = [(side * 10 * max(W, L), W / 2, L / 2), (0, W / 2, L / 2), up]
    p.reset_camera()
    p.camera.parallel_scale = max(L, W * size[1] / size[0]) / 2 * 1.06


_IDS = {}


def part_ids(cfg, pv, side, size):
    """Which part each pixel shows, as a thermal camera's photo overlay would outline them
    (FLIR calls it MSX): every device, every extra solid box (lug palm, crimp barrel, cable),
    the board as one plate and each fin, rendered flat with one colour per box under the same
    camera. Copper islands under the solder mask are left out (a photo does not show them).
    Returns (id image, board-surface mask), cached per view."""
    key = (id(cfg), side, size)
    if key in _IDS:
        return _IDS[key]
    isl = {i["name"] for i in cfg.ims.get("islands", [])}
    board_ids = set()
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("black")
    try:
        p.disable_anti_aliasing()
    except Exception:
        pass
    k = 0
    for name, bxs in solids(cfg).items():
        if name in isl:
            continue
        for (x0, x1), (y0, y1), (z0, z1) in bxs:
            k += 1
            r, g = k % 200 + 30, k // 200 * 40 + 30
            if name == "ims":
                board_ids.add(r + 256 * g + 65536 * 255)
            p.add_mesh(pv.Box(bounds=(x0 / MM, x1 / MM, y0 / MM, y1 / MM, z0 / MM, z1 / MM)),
                       color=(r / 255, g / 255, 1.0), lighting=False)
    _ir_camera(p, cfg, side, size)
    img = p.screenshot(return_img=True)[..., :3].astype(int)
    p.close()
    ids = img[..., 0] + 256 * img[..., 1] + 65536 * img[..., 2]
    board = np.isin(ids, list(board_ids))
    _IDS[key] = (ids, board)
    return ids, board


def ir_panels(fig, gs, img_dev, img_fin, clim, title, cfg):
    a0, a1 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    for a, img, t in ((a0, img_dev, "Component side"), (a1, img_fin, "Heat sink fin side")):
        a.imshow(img)
        a.set_title(t, fontsize=12)
        a.axis("off")
    if cfg.airflow["mode"] == "forced":
        down = (cfg.airflow["direction"] == "fins") == (STYLE["view_up"] == "-z")
        lab = "fan air" if cfg.airflow["direction"] == "fins" else "fan air onto\nthe parts"
        if cfg.airflow["direction"] == "fins":
            a1.annotate(lab, xy=(1.03, 0.25 if down else 0.75), xytext=(1.03, 0.75 if down else 0.25),
                        xycoords="axes fraction", textcoords="axes fraction", ha="center",
                        arrowprops=dict(arrowstyle="->", color="tab:blue", lw=2), color="tab:blue")
        elif cfg.airflow["direction"] == "sink":
            a1.text(0.5, -0.06, "fan air onto the fin tips (into the page)", transform=a1.transAxes,
                    ha="center", color="tab:blue")
        else:
            a0.text(0.5, -0.06, lab.replace("\n", " ") + " (into the page)", transform=a0.transAxes,
                    ha="center", color="tab:blue")
    cax = fig.add_axes([0.93, 0.42, 0.015, 0.45])
    cb = fig.colorbar(plt.cm.ScalarMappable(matplotlib.colors.Normalize(*clim), IR.with_extremes(over=IR_OVER)),
                      cax=cax, label="T (C)", extend="max", extendfrac=0.04)
    ticks = np.linspace(*clim, 12)
    cb.set_ticks(ticks)
    cb.ax.set_yticklabels([f"{t:.1f}" for t in ticks], fontsize=8)
    fig.suptitle(title, fontsize=13)


def fig_cfd_solids(cfg, regions, path: Path, clim):
    if STYLE["style"] != "ir":
        return fig_cfd_solids_3d(cfg, regions, path, clim)
    pv = _pv()
    meshes = solid_meshes(regions)
    tmax = max(float(m.point_data["Tss"].max()) for m in meshes.values())
    clim = ir_clim(cfg.ambient_C, tmax)
    dev = render_side(cfg, pv, meshes, "Tss", clim, -1)
    fin = render_side(cfg, pv, meshes, "Tss", clim, +1)
    fig = plt.figure(figsize=(15, 6.2))
    gs = fig.add_gridspec(1, 2, left=0.02, right=0.9, wspace=0.05)
    ir_panels(fig, gs, dev, fin, clim, f"CFD steady state, surface max {tmax:.1f} C", cfg)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_cfd_solids_3d(cfg, regions, path: Path, clim):
    pv = _pv()
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1600, 750), border=False)
    views = [((1, -1.2, 0.8), "Fin side"), ((-1, -1.1, 0.6), "Device side")]
    for col, (view, title) in enumerate(views):
        p.subplot(0, col)
        for name, m in regions.items():
            if name == "air":
                continue
            mm = m.copy()
            mm.points *= 1 / MM
            mm["T (C)"] = mm["T"] - 273.15
            p.add_mesh(mm, scalars="T (C)", cmap=CMAP, clim=clim, show_scalar_bar=(col == 1),
                       scalar_bar_args={"title": "T (C)", "vertical": True, "position_x": 0.86,
                                        "position_y": 0.15, "height": 0.7, "width": 0.06})
        p.add_text(title, font_size=12)
        frame(p, view, 1.0)
    p.screenshot(str(path))
    p.close()


def fig_cfd_plume(cfg, regions, path: Path):
    pv = _pv()
    air = regions["air"].copy()
    air.points *= 1 / MM
    # through the conducting devices (the heat sources), 0.37 mm off so the cut misses grid faces
    hot = [d for d in cfg.devices if d.power_W is None] or cfg.devices
    y0 = np.mean([d.centre[0] for d in hot]) / MM + 0.37
    s_ = cfg.sink
    near = (-60.0, (s_["base"] + s_["fin_h"]) / MM + 60.0, -1e9, 1e9, -40.0, s_["length"] / MM + 220.0)
    sl = air.slice(normal="y", origin=(0, y0, 0)).clip_box(near, invert=False)
    sl["T (C)"] = sl["T"] - 273.15
    p = pv.Plotter(off_screen=True, window_size=(900, 1200))
    p.add_mesh(sl, scalars="T (C)", cmap=CMAP,
               scalar_bar_args={"title": "Air T (C)", "vertical": True, "position_x": 0.85,
                                "position_y": 0.2, "height": 0.6, "width": 0.07})
    if "U" in sl.point_data and sl.n_points:
        # every n-th point directly; extract_points(adjacent_cells=False) keeps only cells whose
        # points are all picked and returns nothing for some strides
        k = max(1, sl.n_points // 900)
        pts = pv.PolyData(sl.points[::k])
        pts["U"] = sl.point_data["U"][::k]
        p.add_mesh(pts.glyph(orient="U", scale=False, factor=4.0), color="cyan", opacity=0.55)
    for name in solids(cfg):
        if name in regions:
            m = regions[name].copy()
            m.points *= 1 / MM
            cut = m.slice(normal="y", origin=(0, y0, 0))
            if cut.n_points:
                p.add_mesh(cut, color=part_color(name, cfg))
    frame(p, (0, -1, 0), 1.05)   # camera at -y looking +y: x (out of the fins) to the right, z up
    p.add_text(f"Vertical section through the devices (y = {y0:.0f} mm)\n"
               "left: device side, right: fin side; arrows: air flow", font_size=10)
    p.screenshot(str(path))
    p.close()


# ---------------------------------------------------------------- warm-up figure and video

def fig_warmup(cfg, rows, summ, path: Path):
    t = np.array([r["t_s"] for r in rows]) / 60
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for d in cfg.devices:
        ax.plot(t, [r[f"Tj_{d.name}_C"] for r in rows], lw=2, label=f"Tj {d.name}")
    ax.plot(t, [r["T_ims_C"] for r in rows], "--", label=cfg.ims["spreader"]["name"])
    ax.plot(t, [r["T_sink_C"] for r in rows], ":", lw=2, label="Heat sink")
    ax.axhline(cfg.ambient_C, color="grey", lw=0.8)
    for key, lab in (("t63_s", "63 %"), ("t90_s", "90 %")):
        if summ.get(key):
            ax.axvline(summ[key] / 60, color="grey", ls="--", lw=0.8)
            ax.text(summ[key] / 60, ax.get_ylim()[0] + 0.5, f" {lab}", fontsize=8, color="grey")
    ax.set_xlabel("time from switch-on (min)")
    ax.set_ylabel("temperature (C)")
    ax.set_title(f"Warm-up at {sum(rows[-1][k] for k in ['P_W']):.1f} W total, "
                 f"{cfg.ambient_C:g} C ambient ({summ['calibrated_to']}-calibrated)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7 if len(cfg.devices) > 10 else 9, ncol=2 if len(cfg.devices) > 10 else 1)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _frames(cfg, regions, rows, summ, fps, seconds):
    """Per frame: time, warm-up row and every region's field (its CFD steady pattern scaled
    by the warm-up curve of its node; metal parts are nearly isothermal)."""
    Ta = cfg.ambient_C
    tgt = summ["steady_target"]
    meshes = solid_meshes(regions)
    t_all = np.array([r["t_s"] for r in rows])
    t_end = min(t_all[-1], (summ.get("t99_s") or t_all[-1]) * 1.2)
    times = t_end * (np.linspace(0, 1, fps * seconds) ** 1.6)   # more frames early, where it changes fast

    def scale(r, name):
        col = warmup_node(cfg, name)
        ss = tgt.get(col, Ta)
        return (r[col] - Ta) / (ss - Ta) if abs(ss - Ta) > 1e-9 else 1.0

    def row(tt):
        return rows[min(int(np.searchsorted(t_all, tt)), len(rows) - 1)]

    # top of the scale = the hottest value any frame shows, so the picture never saturates
    peak = max(Ta + (float(mm.point_data["Tss"].max()) - Ta) * scale(row(tt), n)
               for tt in times for n, mm in meshes.items())
    return meshes, times, t_all, t_end, row, scale, peak


def video_heatup(cfg, regions, rows, summ, path: Path, fps=12, seconds=12):
    if STYLE["style"] != "ir":
        return video_heatup_3d(cfg, regions, rows, summ, path, fps, seconds)
    import imageio.v2 as imageio
    pv = _pv()
    Ta = cfg.ambient_C
    meshes, times, t_all, t_end, row, scale, peak = _frames(cfg, regions, rows, summ, fps, seconds)
    clim = ir_clim(Ta, peak)
    tj_cols = [f"Tj_{d.name}_C" for d in cfg.devices]
    writer = imageio.get_writer(str(path), fps=fps, codec="libx264", quality=8, macro_block_size=8)
    try:
        for tt in times:
            r = row(tt)
            for name, mm in meshes.items():
                mm.point_data["Tnow"] = Ta + (mm.point_data["Tss"] - Ta) * scale(r, name)
            dev = render_side(cfg, pv, meshes, "Tnow", clim, -1, (800, 620))
            fin = render_side(cfg, pv, meshes, "Tnow", clim, +1, (800, 620))
            tmax = max(float(m.point_data["Tnow"].max()) for m in meshes.values())
            fig = plt.figure(figsize=(14, 8))
            gs = fig.add_gridspec(2, 2, height_ratios=[3, 1.1], left=0.06, right=0.9, bottom=0.08,
                                  wspace=0.05, hspace=0.25)
            ir_panels(fig, [gs[0, 0], gs[0, 1]], dev, fin, clim,
                      f"t = {tt / 60:5.1f} min   surface max {tmax:5.1f} C   "
                      f"hottest Tj {max(r[c_] for c_ in tj_cols):5.1f} C", cfg)
            ax = fig.add_subplot(gs[1, :])
            tm = t_all / 60
            ax.plot(tm, [max(rr[c_] for c_ in tj_cols) for rr in rows], lw=2, color="#f05a28", label="hottest Tj")
            ax.plot(tm, [rr["T_sink_C"] for rr in rows], ":", lw=2, color="0.4", label="heat sink")
            ax.axvline(tt / 60, color="tab:red")
            ax.set_xlim(0, t_end / 60)
            ax.set_xlabel("time (min)")
            ax.set_ylabel("T (C)")
            ax.grid(alpha=0.3)
            ax.legend(loc="lower right")
            fig.canvas.draw()
            writer.append_data(np.asarray(fig.canvas.buffer_rgba())[..., :3])
            plt.close(fig)
    finally:
        writer.close()


def video_heatup_3d(cfg, regions, rows, summ, path: Path, fps=12, seconds=10):
    """3D view, inferno palette (report style 3d)."""
    import imageio.v2 as imageio
    pv = _pv()
    Ta = cfg.ambient_C
    meshes, times, t_all, t_end, row, scale, peak = _frames(cfg, regions, rows, summ, fps, seconds)
    clim = (Ta, peak)
    tj_cols = [f"Tj_{d.name}_C" for d in cfg.devices]

    p = pv.Plotter(off_screen=True, window_size=(900, 760))
    for name, mm in meshes.items():
        mm.point_data["T (C)"] = np.full(mm.n_points, Ta)
        p.add_mesh(mm, scalars="T (C)", cmap=CMAP, clim=clim,
                   scalar_bar_args={"title": "T (C)", "vertical": True, "position_x": 0.86,
                                    "position_y": 0.15, "height": 0.7, "width": 0.06})
    frame(p, (-1, -1.1, 0.6), 1.0)
    label = p.add_text(" ", position="upper_left", font_size=12)

    writer = imageio.get_writer(str(path), fps=fps, codec="libx264", quality=8, macro_block_size=8)
    try:
        for tt in times:
            r = row(tt)
            for name, mm in meshes.items():
                # write into the array the renderer holds; assigning a new array would not show
                mm.point_data["T (C)"][:] = Ta + (mm.point_data["Tss"] - Ta) * scale(r, name)
                mm.Modified()
            label.set_text("upper_left", f"t = {tt / 60:5.1f} min   hottest Tj = {max(r[c_] for c_ in tj_cols):.1f} C")
            p.render()
            frame3d = p.screenshot(return_img=True)
            fig, ax = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1.15, 1]})
            ax[0].imshow(frame3d)
            ax[0].axis("off")
            tm = t_all / 60
            ax[1].plot(tm, [max(rr[c_] for c_ in tj_cols) for rr in rows], lw=2, label="hottest Tj")
            ax[1].plot(tm, [rr["T_sink_C"] for rr in rows], ":", lw=2, label="sink")
            ax[1].axvline(tt / 60, color="tab:red")
            ax[1].set_xlim(0, t_end / 60)
            ax[1].set_xlabel("time (min)")
            ax[1].set_ylabel("temperature (C)")
            ax[1].grid(alpha=0.3)
            ax[1].legend(loc="lower right")
            fig.tight_layout()
            fig.canvas.draw()
            img = np.asarray(fig.canvas.buffer_rgba())[..., :3]
            plt.close(fig)
            writer.append_data(img)
    finally:
        writer.close()
        p.close()


def fig_temperature_path(cfg, hc, cfd, path: Path):
    """Ambient -> sink -> board spreader -> case -> junction for the hottest device, hand calc vs CFD."""
    d = max(hc["devices"], key=lambda r: r["T_j_C"])
    labels = ["ambient", "sink (mean)", cfg.ims["spreader"]["name"], "case", "junction"]
    hand = [cfg.ambient_C, hc["T_sink_C"], hc["T_base_under_ims_C"] + hc["P_tot"] * hc["R_tim"],
            d["T_case_C"], d["T_j_C"]]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(labels))
    ax.plot(x, hand, "o-", label="hand calc")
    if cfd:
        ax.plot(x, [cfg.ambient_C, cfd["T_sink_C"], cfd["T_ims_C"], cfd["T_case_C"], cfd["Tj_C"]],
                "s-", label="CFD")
    ax.set_xticks(x, labels)
    ax.set_ylabel("temperature (C)")
    ax.set_title(f"Temperature along the heat path, {d['name']}")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- document

def build_docx(path: Path, cfg, hc, meta, gates, verdict, figs, cfd, summ, assumptions, has_video):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)

    def table(rows, header, widths=None):
        t = doc.add_table(rows=1, cols=len(header))
        t.style = "Light Grid Accent 1"
        for i, h in enumerate(header):
            t.rows[0].cells[i].text = h
        for r in rows:
            cells = t.add_row().cells
            for i, v in enumerate(r):
                cells[i].text = str(v)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        doc.add_paragraph()
        return t

    def figure(key, caption, width=16.5):
        if key in figs and figs[key].exists():
            doc.add_picture(str(figs[key]), width=Cm(width))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp = doc.add_paragraph(caption)
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.runs[0].italic = True

    doc.add_heading(f"Thermal report: {cfg.name}", 0)
    doc.add_paragraph(f"{dt.date.today().isoformat()} · OpenFOAM v2412 conjugate heat transfer · "
                      f"generated by the openfoam-electronics-cooling skill")

    # 1. answer
    doc.add_heading("1. Result", 1)
    rows = []
    for d in hc["devices"]:
        cf = cfd["devices"].get(d["name"]) if cfd else None
        tj = cf["Tj"] if cf else d["T_j_C"]
        rows.append([d["name"], f"{d['P']:.2f}", f"{d['T_j_C']:.1f}",
                     f"{cf['Tj']:.1f}" if cf else "not run", f"{d['tj_max']:.0f}", f"{d['tj_max'] - tj:.0f}"])
    table(rows, ["Device", "Loss (W)", "Tj hand calc (C)", "Tj CFD (C)", "Tj max (C)", "Margin (K)"])
    worst = min(float(r[-1]) for r in rows)
    msg = (f"At {cfg.ambient_C:g} C ambient the hottest junction stays {worst:.0f} K below its limit. "
           + ("That is above the usual 25 K design margin." if worst >= 25 else
              "That is BELOW the usual 25 K design margin."))
    doc.add_paragraph(msg)
    if verdict:
        doc.add_paragraph(f"CFD checks: {verdict}")
    if summ:
        doc.add_paragraph(f"Warm-up from cold: 90 % of the final temperature rise after "
                          f"{(summ['t90_s'] or 0) / 60:.0f} min, steady after about {(summ['t99_s'] or 0) / 60:.0f} min.")

    # 2. inputs
    doc.add_heading("2. Inputs", 1)
    s, im, el = cfg.sink, cfg.ims, cfg.electrical
    inp = [["Ambient (worst case)", f"{cfg.ambient_C:g} C"],
           ["Current", f"{el['current']} A" if el["current"] is not None else "per device power"],
           ["Rds(on) 25 C / factor at 125 C", f"{el['rds25'] * 1e3:g} mOhm / x{el['f125']:g}" if el["rds25"] else "-"],
           ["Switching loss per device", f"{el['switching_W']:g} W"],
           ["Heat sink", f"{s['width'] / MM:g} x {s['length'] / MM:g} mm, base {s['base'] / MM:g} mm, "
                         f"{s['n_fins']} fins {s['fin_t'] / MM:g} x {s['fin_h'] / MM:g} mm (gap {s['gap'] / MM:.1f} mm), "
                         f"k {s['k']:g} W/mK, emissivity {s['emissivity']:g}, back {s['back']}"],
           ["Board", f"{im['label']}, {im['size'][0] / MM:g} x {im['size'][1] / MM:g} mm"],
           ["  part to spreader", "; ".join(layer_text(l) for l in im["under"]) or "-"],
           ["  spreader (meshed)", f"{spreader_label(cfg)}, k {im['spreader']['k']:g} W/mK"],
           ["  spreader to sink", "; ".join(layer_text(l) for l in im["below"])]]
    for d in cfg.devices:
        inp.append([f"Device {d.name}", f"{d.size[0] / MM:g} x {d.size[1] / MM:g} x {d.size[2] / MM:g} mm at "
                                        f"({d.centre[0] / MM:g}, {d.centre[1] / MM:g}) mm, Rth j-c {d.rth_jc:g} K/W, "
                                        f"Tj max {d.tj_max:g} C"])
    table(inp, ["Quantity", "Value"], [5, 12])
    if assumptions:
        doc.add_paragraph("Values marked for checking in the input file:")
        for a in assumptions:
            doc.add_paragraph(a, style="List Bullet")

    # 3. arrangement
    doc.add_heading("3. Arrangement", 1)
    figure("layout", "Figure 1: device placement on the sink, section through the devices, and the "
                     "layers the heat crosses.")
    figure("assembly", "Figure 2: 3D view of the modelled assembly (grey heat sink, green board, black packages).")

    # 4. setup
    doc.add_heading("4. Simulation setup", 1)
    if meta:
        ec = meta["expected_cells"]
        mode = meta["config"].get("solver", {}).get("mode", "steady")
        rows = [["Solver", "chtMultiRegionFoam (transient)" if mode == "transient" else "chtMultiRegionSimpleFoam (steady)"],
                ["Mesh", f"{ec['_total']:,} cells, resolution {meta['resolution']}; " +
                         ", ".join(f"{r} {ec[r]:,}" for r in meta["regions"])],
                ["Air", "laminar, buoyant, ideal gas; open boundaries on all sides (room at ambient)"],
                ["Radiation", "fvDOM surface radiation, grey diffuse surfaces, black surroundings at ambient"
                 if meta["config"].get("solver", {}).get("radiation", True) else "off"],
                ["Board", f"{cfg.ims['spreader']['name']} meshed; the layers above it (part side) and below "
                          "it (sink side) as thin thermal resistances on those interfaces"],
                ["Heat sources", ", ".join(f"{k} {v:.2f} W" for k, v in meta["power_W"].items())],
                ["Junction temperature", "hottest point of the package contact face + loss x Rth(j-c)"]]
        table(rows, ["Item", "Setting"], [4, 13])
    else:
        doc.add_paragraph("No CFD case was run; results below are from the hand calculation.")

    # 5. results
    doc.add_heading("5. Thermal results", 1)
    figure("path", "Figure 3: temperature along the heat path of the hottest device.", 14)
    if cfd:
        figure("cfd_solids", "Figure 4: CFD temperature of all solid parts (same colour scale both views).")
        figure("plume", "Figure 5: air temperature and flow in a vertical section through the devices.", 13)
        rows = [["Heat put in", f"{cfd['P_in']:.2f} W"], ["Heat leaving the solids", f"{cfd['Q_out']:.2f} W"],
                ["of which radiation", f"{cfd['Q_rad']:.2f} W ({100 * cfd['Q_rad'] / max(cfd['Q_out'], 1e-9):.0f} %)"
                 if cfd.get("Q_rad") is not None else "not modelled"],
                ["Mean sink temperature", f"{cfd['T_sink_C']:.1f} C (hand calc {hc['T_sink_C']:.1f} C)"]]
        table(rows, ["Quantity", "CFD"], [6, 11])
    else:
        sh = hc["sink"]
        table([["Sink mean temperature", f"{hc['T_sink_C']:.1f} C"],
               ["Convection / radiation", f"{sh['q_conv']:.2f} W / {sh['q_rad']:.2f} W"],
               ["Sink to air", f"{hc['R_sa']:.3f} K/W"]], ["Quantity", "Hand calc"], [6, 11])

    # 6. warm-up
    if summ:
        doc.add_heading("6. Warm-up", 1)
        figure("warmup", "Figure 6: temperatures from switch-on at full load.", 15)
        doc.add_paragraph(
            "Lumped model with the real heat capacities (heat sink "
            f"{summ['C_sink_J_K']:.0f} J/K, {cfg.ims['spreader']['name']} {summ['C_ims_J_K']:.1f} J/K), "
            "calibrated so its end point equals "
            f"the {summ['calibrated_to']} steady state; losses rise with junction temperature along the way."
            + (" The heat-up video (heatup.mp4, delivered with this report) shows the same warm-up on the 3D "
               "temperature field." if has_video else ""))

    # 7. checks
    if gates:
        doc.add_heading("7. Checks on the CFD result", 1)
        table(gates, ["Check", "Result", "Detail"], [5.5, 1.6, 9.9])

    # 8. limits
    doc.add_heading("8. Limits", 1)
    for t in ["Tj is case temperature plus loss x Rth(j-c); the die itself is not modelled.",
              "Thin layers conduct only through their thickness; copper spreading under the pad is ignored (conservative).",
              "The surroundings radiate as a black room at ambient; nearby hot walls or an enclosure are not modelled.",
              "Air is laminar with constant properties at the film temperature; solids have constant conductivity.",
              "The warm-up assumes full load from a cold start; short pulses (inrush, faults) need the datasheet Zth curves."]:
        doc.add_paragraph(t, style="List Bullet")
    doc.save(str(path))


def to_pdf(docx: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice not found; PDF skipped", file=sys.stderr)
        return None
    profile = docx.parent / ".lo-profile"   # private profile: works even with LibreOffice open
    subprocess.run([soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", "pdf",
                    "--outdir", str(docx.parent), str(docx)], check=True, capture_output=True, timeout=300)
    shutil.rmtree(profile, ignore_errors=True)
    pdf = docx.with_suffix(".pdf")
    return pdf if pdf.exists() else None


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="case directory, or a case YAML for a hand-calc-only report")
    ap.add_argument("--out", help="output directory (default <case>/report)")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--hours", type=float, default=2.0, help="warm-up span")
    ap.add_argument("--style", choices=["ir", "3d"], help="CFD figure and video: thermal-camera "
                    "views of both sides (default) or a 3D view; also report.style in the YAML")
    a = ap.parse_args()
    src = Path(a.source)
    case = src if src.is_dir() else None
    cfg_path = case / "case.yaml" if case else src
    cfg = load_config(cfg_path)
    rep = cfg.raw.get("report") or {}
    STYLE.update({k: rep[k] for k in ("style", "view_up", "mirror", "ir_floor_K", "ir_range", "ir_blur_mm",
                                      "ir_edges", "ir_board_blur_mm")
                  if k in rep})
    if a.style:
        STYLE["style"] = a.style
    # Outside the case folder: the case carries a CACHEDIR.TAG and is left out of backups, the
    # report and the configs that reproduce it are not.
    out = Path(a.out) if a.out else (case.parent / f"{case.name}-report" if case else Path("report"))
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    hc = network(cfg)

    meta = json.loads((case / "case-meta.json").read_text()) if case else None
    has_cfd = bool(case and (case / "VTK").is_dir() and (case / "postProcessing").is_dir())

    figs = {"layout": figdir / "layout.png", "assembly": figdir / "assembly-3d.png",
            "path": figdir / "temperature-path.png", "warmup": figdir / "warmup.png",
            "cfd_solids": figdir / "cfd-solids.png", "plume": figdir / "cfd-plume.png"}
    fig_layout(cfg, figs["layout"])
    fig_assembly_3d(cfg, figs["assembly"])

    rows, summ = warmup.simulate(cfg, case if has_cfd else None, a.hours)
    with (out / "warmup.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    fig_warmup(cfg, rows, summ, figs["warmup"])

    cfd, gates, verdict, regions = None, [], "", {}
    if has_cfd:
        gates, verdict = gates_from_report(case)
        regions = load_cfd(case)
        tg = summ["steady_target"]
        dev = {}
        for d in cfg.devices:
            tcase = warmup.last_value(case, d.name, f"case_{d.name}", "surfaceFieldValue.dat")
            if tcase:
                dev[d.name] = {"T_case": c(tcase), "Tj": c(tcase) + meta["power_W"][d.name] * d.rth_jc}
        hot = max(dev, key=lambda k: dev[k]["Tj"]) if dev else None
        from report import series, tail_mean, wall_heat  # same parsing and means as the gates
        q_air = [(t, sum(v for k, v in d.items() if k.startswith("air_to_"))) for t, d in wall_heat(case).items()]
        q_out = tail_mean(q_air)[0] if q_air else float("nan")
        for r_, fe in (meta.get("far_end") or {}).items():     # plus the cable ends
            iT = tail_mean(series(case, r_, f"farEnd_{r_}", "surfaceFieldValue.dat"))[0]
            q_out += fe["h"] * (iT - fe["T_inf_K"] * fe["A_m2"]) if iT is not None else 0.0
        rad = series(case, "air", "radiationShare", "surfaceFieldValue.dat")
        cfd = {"devices": dev, "P_in": sum(meta["power_W"].values()), "Q_out": q_out,
               "Q_rad": -tail_mean(rad)[0] if rad else None, "T_sink_C": tg["T_sink_C"], "T_ims_C": tg["T_ims_C"],
               "T_case_C": dev[hot]["T_case"] if hot else None, "Tj_C": dev[hot]["Tj"] if hot else None}
        all_T = [float(m["T"].max()) - 273.15 for n, m in regions.items() if n != "air"]
        clim = (cfg.ambient_C, max(all_T))
        fig_cfd_solids(cfg, regions, figs["cfd_solids"], clim)
        if "air" in regions:
            fig_cfd_plume(cfg, regions, figs["plume"])
    fig_temperature_path(cfg, hc, cfd if cfd and cfd.get("Tj_C") else None, figs["path"])

    has_video = False
    if not a.no_video and regions:
        video_heatup(cfg, regions, rows, summ, out / "heatup.mp4")
        has_video = True

    docx = out / "thermal-report.docx"
    build_docx(docx, cfg, hc, meta, gates, verdict, figs, cfd, summ,
               check_assumptions(cfg_path), has_video)
    pdf = to_pdf(docx)
    if case:   # the configs that reproduce this run, next to its report
        for f in ("case.yaml", "case-meta.json", "report.md"):
            if (case / f).exists():
                shutil.copy(case / f, out / f)
    print(f"Report written to {out}:")
    for p in [docx, pdf, out / "heatup.mp4" if has_video else None]:
        if p:
            print(f"  {p.name}  ({p.stat().st_size / 1e6:.1f} MB)")
    print(f"  figures/: {', '.join(sorted(f.name for f in figdir.glob('*.png')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
