"""Shared model for the openfoam-electronics-cooling skill.

One YAML file (see assets/example-case.yaml) describes the hardware. This module loads it,
fills defaults, computes device losses and the first-order thermal network that every CFD
result is checked against. hand_calc.py prints it; make_case.py builds the OpenFOAM case
from the same numbers so the two can never drift apart.

Geometry convention (all lengths in the YAML are mm, stored here in m):
  z  vertical, gravity -z. Fins run along z, so air rises through the channels.
  y  across the fins (sink width).
  x  out of the sink: base x in [0, base], fins x in [base, base+fin_height].
     The board (an IMS, a Cu-core board, ...; stored as cfg.ims, CFD region 'ims') sits on the
     back face (x < 0), devices sit on the board (further -x). Only the board's spreader is
     meshed; the layers above and below it are thin thermal resistances (see load_board).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SIGMA = 5.670374e-8
G = 9.81
MM = 1e-3
UM = 1e-6


# ---------------------------------------------------------------- air properties

def air_props(T: float) -> dict:
    """Dry air at 1 atm, valid ~250-450 K. Sutherland viscosity, ideal-gas density."""
    mu = 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)
    rho = 101325.0 / (287.05 * T)
    cp = 1007.0
    k = 0.0241 * (T / 273.15) ** 0.9
    return {"mu": mu, "rho": rho, "cp": cp, "k": k, "nu": mu / rho,
            "alpha": k / (rho * cp), "Pr": mu * cp / k, "beta": 1.0 / T}


# ---------------------------------------------------------------- config

@dataclass
class Device:
    name: str
    size: tuple          # (y, z, x-thickness) m
    centre: tuple        # (y, z) m on the board / base back face
    rth_jc: float        # K/W junction to case (exposed pad)
    k_package: float     # effective package conductivity for the CFD block
    emissivity: float
    tj_max: float        # degC
    power_W: float | None = None   # fixed power; None = from electrical
    conducts: bool = True          # carries the load current (False = idle part)


@dataclass
class Config:
    name: str
    ambient_C: float
    sink: dict
    ims: dict
    tim: dict
    devices: list
    electrical: dict
    mesh: dict
    solver: dict
    raw: dict = field(repr=False, default_factory=dict)
    solids: list = field(default_factory=list)     # extra solid parts (load_solids)
    airflow: dict = field(default_factory=lambda: {"mode": "free"})   # load_airflow


def _req(d: dict, key: str, where: str):
    if key not in d:
        raise KeyError(f"missing '{key}' in {where}")
    return d[key]


def _layer(d: dict, where: str) -> dict:
    """{name, thickness_um, k} or {name, R_m2K_W} (a contact or anything given as a resistance
    per area). A resistance-only layer is carried as 10 um at k = 10 um / R, which is what the
    CFD's thin-layer condition needs."""
    name = _req(d, "name", where)
    if "R_m2K_W" in d:
        t = d.get("thickness_um", 10) * UM
        return {"name": name, "t": t, "k": t / d["R_m2K_W"], "R": d["R_m2K_W"]}
    return {"name": name, "t": _req(d, "thickness_um", f"{where} '{name}'") * UM,
            "k": _req(d, "k", f"{where} '{name}'")}


def layers_R(layers: list) -> float:
    """Series resistance per unit area, m2K/W."""
    return sum(l["t"] / l["k"] for l in layers)


def load_board(raw: dict, hs: dict) -> dict:
    """The board the parts sit on, as a generic stack (stored as cfg.ims; the CFD region keeps
    the name 'ims'):

      under     layers from a part's pad down to the spreader (thin resistances per part)
      spreader  the plate that spreads heat in-plane and is meshed (Al of an IMS, Cu core, ...)
      below     layers from the spreader down to the heat sink (insulation, contact, TIM)

    New files use `board:`; the older `ims:` + `tim:` form is converted to the same stack."""
    centre_default = [hs["width_mm"] / 2, hs["length_mm"] / 2]
    if "board" in raw:
        b = raw["board"]
        sp = _req(b, "spreader", "board")
        board = {
            "label": b.get("label", "board"),
            "size": tuple(v * MM for v in _req(b, "size_mm", "board")),
            "centre": tuple(v * MM for v in b.get("centre_mm", centre_default)),
            "emissivity": b.get("emissivity", 0.9),
            "spreader": {"name": _req(sp, "name", "board.spreader"),
                         "t": _req(sp, "thickness_mm", "board.spreader") * MM,
                         "k": _req(sp, "k", "board.spreader"),
                         "rho": sp.get("rho", 2700.0), "cp": sp.get("cp", 900.0)},
            "under": [_layer(l, "board.layers_under_parts") for l in b.get("layers_under_parts", [])],
            "below": [_layer(l, "board.layers_to_sink") for l in _req(b, "layers_to_sink", "board")],
        }
    else:
        im = _req(raw, "ims", "root (give `board:` or the older `ims:`)")
        t = raw.get("tim", {})
        board = {
            "label": "IMS",
            "size": tuple(v * MM for v in _req(im, "size_mm", "ims")),
            "centre": tuple(v * MM for v in im.get("centre_mm", centre_default)),
            "emissivity": im.get("emissivity", 0.9),
            "spreader": {"name": "Al substrate", "t": im.get("substrate_mm", 1.5) * MM,
                         "k": im.get("k_substrate", 200.0), "rho": 2700.0, "cp": 900.0},
            "under": [
                {"name": "solder", "t": im.get("solder_um", 75) * UM, "k": im.get("solder_k", 50.0)},
                {"name": "copper", "t": im.get("copper_um", 70) * UM, "k": 390.0},
                {"name": "dielectric", "t": im.get("dielectric", {}).get("thickness_um", 100) * UM,
                 "k": im.get("dielectric", {}).get("k", 2.2)},
            ],
            "below": [{"name": "TIM", "t": t.get("thickness_um", 100) * UM, "k": t.get("k", 3.0)}],
        }
    if not board["below"]:
        raise ValueError("board: give at least one layer between spreader and heat sink")
    # A patterned spreader (the Cu core of a QIT board is cut into tracks): islands are separate
    # regions at the spreader's level; the part of the board they leave free stays region 'ims'.
    # Between islands (and island-ims) heat crosses the isolation slot, given as 'gap' layers,
    # except for pairs listed in 'bridges' (copper continues, e.g. a narrow sense track).
    #   islands: [{name: bat_p_pad, boxes: [{y_mm: [..], z_mm: [..]}], power_W: 2.2}, ...]
    #   gap: [{name: slot, thickness_um: 600, k: 0.5}]      bridges: [[bat_p_pad, sense], ...]
    b = raw.get("board", {}) if "board" in raw else {}
    board["islands"] = []
    for i in b.get("islands", []) or []:
        where = f"board.islands '{i.get('name', '?')}'"
        board["islands"].append({
            "name": _req(i, "name", "board.islands[]"),
            "boxes": [(bx["y_mm"][0] * MM, bx["y_mm"][1] * MM, bx["z_mm"][0] * MM, bx["z_mm"][1] * MM)
                      for bx in _req(i, "boxes", where)],
            "power_W": float(i.get("power_W", 0.0)),
        })
    board["gap"] = [_layer(l, "board.gap") for l in b.get("gap", [{"name": "isolation slot",
                                                                   "thickness_um": 600, "k": 0.5}])]
    board["bridges"] = {frozenset(p) for p in b.get("bridges", []) or []}
    # Loss in the remainder region 'ims' (with islands: the one connected piece they leave free;
    # splitMeshRegions cannot keep a region whose cells are not connected). Bridges to it use 'ims'.
    board["power_W"] = float(b.get("power_W", 0.0))
    board["substrate"] = board["spreader"]["t"]       # short names used across the scripts
    board["k_substrate"] = board["spreader"]["k"]
    return board


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    hs = _req(raw, "heatsink", "root")
    fin = _req(hs, "fin", "heatsink")
    sink = {
        "width": _req(hs, "width_mm", "heatsink") * MM,
        "length": _req(hs, "length_mm", "heatsink") * MM,
        "base": _req(hs, "base_mm", "heatsink") * MM,
        "n_fins": int(_req(fin, "count", "heatsink.fin")),
        "fin_t": _req(fin, "thickness_mm", "heatsink.fin") * MM,
        "fin_h": _req(fin, "height_mm", "heatsink.fin") * MM,
        "k": hs.get("k", 200.0),
        "emissivity": hs.get("emissivity", 0.85),
        "back": hs.get("back", "free"),        # free | wall
    }
    if sink["n_fins"] < 2:
        raise ValueError("need at least 2 fins")
    sink["gap"] = (sink["width"] - sink["n_fins"] * sink["fin_t"]) / (sink["n_fins"] - 1)
    if sink["gap"] <= 0:
        raise ValueError("fins do not fit in the sink width")

    ims = load_board(raw, hs)
    # Equivalent single layer of everything between spreader and sink (kept for scripts that
    # read cfg.tim); the model itself uses the layer list in ims["below"].
    t_below = sum(l["t"] for l in ims["below"])
    tim = {"t": t_below, "k": t_below / layers_R(ims["below"])}

    devices = []
    for d in raw.get("devices") or []:
        sz = d.get("size_mm", [10, 15, 4.5])
        devices.append(Device(
            name=_req(d, "name", "devices[]"),
            size=(sz[0] * MM, sz[1] * MM, sz[2] * MM),
            centre=tuple(v * MM for v in _req(d, "centre_mm", "devices[]")),
            rth_jc=d.get("rth_jc", 0.5),
            k_package=d.get("k_package", 20.0),
            emissivity=d.get("emissivity", 0.9),
            tj_max=d.get("tj_max_C", 175.0),
            power_W=d.get("power_W"),
            conducts=d.get("conducts", True),
        ))
    # A bare heat-sink case (datasheet R_sa check, calorimetry benchmark) has no devices: its heat
    # goes into the board through board.power_W or the islands' power_W.
    if not devices and not (ims["power_W"] > 0 or any(i["power_W"] > 0 for i in ims["islands"])):
        raise ValueError("no heat source: add devices or board.power_W")

    el = raw.get("electrical", {})
    electrical = {
        "current": el.get("current_A"),
        "rds25": el.get("rds_on_25C_mohm", 0) * 1e-3,
        "f125": el.get("rds_on_factor_at_125C", 1.7),
        "switching_W": el.get("switching_loss_W_per_device", 0.0),
    }
    mesh = {"resolution": "normal", **raw.get("mesh", {})}
    mesh.setdefault("clearance_mm", {})
    solver = {"iterations": 4000, "radiation": True, "n_procs": 8, **raw.get("solver", {})}

    cfg = Config(raw.get("name", Path(path).stem), raw.get("ambient_C", 25.0),
                 sink, ims, tim, devices, electrical, mesh, solver, raw)
    cfg.solids = load_solids(raw, {d.name for d in devices})
    cfg.airflow = load_airflow(raw)
    _check_footprints(cfg)
    return cfg


AIRFLOW_DIRECTIONS = {   # inlet boundary and flow direction of a fan
    "fins": ("bottom", (0, 0, 1)),          # up along the fins, from below the sink
    "components": ("back", (1, 0, 0)),      # straight onto the component side
    "sink": ("front", (-1, 0, 0)),          # straight onto the fin tips (fan in front of the sink);
                                            # the hand calc still assumes flow along the channels
}


def load_airflow(raw: dict) -> dict:
    """airflow: {mode: free}  (default)  or
       airflow: {mode: forced, velocity_m_s: 1.5, direction: fins, channel_ratio: 0.45}
    direction: fins (along the fin channels) or components (onto the parts' side).
    channel_ratio: fin-channel velocity / approach velocity for the hand calc (measure it in a
    CFD run with channel_flow.py; an open sink lets half or more of the air bypass).
    turbulence: {intensity: 0.1, length_mm: 10} (optional, forced only): k-omega SST air with a
    turbulent fan inlet (intensity = u'/U, length_mm = mixing length). Without it the air is
    laminar, which under-predicts heat transfer in a fan's swirling, turbulent jet."""
    a = raw.get("airflow") or {"mode": "free"}
    mode = a.get("mode", "free")
    if mode == "free":
        return {"mode": "free"}
    if mode != "forced":
        raise ValueError("airflow.mode: free or forced")
    d = a.get("direction", "fins")
    if d not in AIRFLOW_DIRECTIONS:
        raise ValueError(f"airflow.direction: one of {', '.join(AIRFLOW_DIRECTIONS)}")
    t = a.get("turbulence")
    if t:
        t = {"model": t.get("model", "kOmegaSST"), "intensity": float(t.get("intensity", 0.1)),
             "length_mm": float(t.get("length_mm", 10))}
    return {"mode": "forced", "velocity": float(_req(a, "velocity_m_s", "airflow")), "direction": d,
            "channel_ratio": a.get("channel_ratio"), "turbulence": t}


def load_solids(raw: dict, device_names: set) -> list:
    """Extra solid parts that are not devices on the board: terminal studs, cable lugs, crimp
    barrels, cables, busbars, brackets ... Each is one box (or several, same material):

      - name: x1_lug
        y_mm: [93.5, 111.5]        # across the fins, sink coordinates; .inf / -.inf = to the
        z_mm: [9, 21]              #   domain boundary (a cable that leaves the model)
        height_mm: [6, 8.5]        # above the board's top surface (the parts' side)
        k: 390                     # W/mK; rho, cp for heat capacity (transient, warm-up)
        rho: 8960
        cp: 385
        emissivity: 0.15
        power_W: 0.9               # loss in the part (crimp, contact, I2R), default 0
        contact: {x1: {R_m2K_W: 1.5e-4}}     # thin layers to named neighbours
        air_layers: [{name: PVC, thickness_um: 2000, k: 0.2}]   # e.g. cable insulation
        far_end: {h_W_m2K: 1400, T_C: 58}   # on faces at the domain boundary: the part
                                             #   continues beyond (a cable as a long fin)

    The hand calc does not see these parts; they are for the CFD (and their heat shows in the
    CFD energy balance). Give the parts' losses here, not under devices."""
    out = []
    for s in raw.get("solids", []) or []:
        where = f"solids '{s.get('name', '?')}'"
        name = _req(s, "name", "solids[]")
        if name in device_names or name in ("air", "heatsink", "ims"):
            raise ValueError(f"{where}: name already used")
        boxes = s.get("boxes") or [{"y_mm": _req(s, "y_mm", where), "z_mm": _req(s, "z_mm", where),
                                    "height_mm": _req(s, "height_mm", where)}]
        fe = s.get("far_end")
        out.append({
            "name": name,
            "boxes": [{"y": tuple(v * MM for v in b["y_mm"]), "z": tuple(v * MM for v in b["z_mm"]),
                       "h": tuple(v * MM for v in b["height_mm"])} for b in boxes],
            "k": _req(s, "k", where), "rho": s.get("rho", 8000.0), "cp": s.get("cp", 400.0),
            "emissivity": s.get("emissivity", 0.9), "power_W": float(s.get("power_W", 0.0)),
            "contact": {o: [_layer(l, f"{where}.contact") for l in (v if isinstance(v, list) else [v | {"name": f"{name}-{o}"}])]
                        for o, v in (s.get("contact") or {}).items()},
            "air_layers": [_layer(l, f"{where}.air_layers") for l in s.get("air_layers", [])],
            "far_end": {"h": fe["h_W_m2K"], "T": fe["T_C"] + 273.15} if fe else None,
        })
    return out


def _check_footprints(cfg: Config) -> None:
    W, L = cfg.sink["width"], cfg.sink["length"]

    def box(c, s):
        return (c[0] - s[0] / 2, c[0] + s[0] / 2, c[1] - s[1] / 2, c[1] + s[1] / 2)

    iy0, iy1, iz0, iz1 = box(cfg.ims["centre"], cfg.ims["size"])
    if iy0 < -1e-9 or iz0 < -1e-9 or iy1 > W + 1e-9 or iz1 > L + 1e-9:
        raise ValueError("the board does not fit on the heat sink back face")
    boxes = []
    for d in cfg.devices:
        b = box(d.centre, d.size)
        if b[0] < iy0 - 1e-9 or b[2] < iz0 - 1e-9 or b[1] > iy1 + 1e-9 or b[3] > iz1 + 1e-9:
            raise ValueError(f"device {d.name} does not fit on the board")
        for n, o in boxes:
            if b[0] < o[1] and o[0] < b[1] and b[2] < o[3] and o[2] < b[3]:
                raise ValueError(f"devices {d.name} and {n} overlap")
        boxes.append((d.name, b))


# ---------------------------------------------------------------- losses

def rds_on(cfg: Config, tj_C: float) -> float:
    """Linear Rds(on) vs Tj through the 25 C value and the 125 C factor."""
    e = cfg.electrical
    return e["rds25"] * (1.0 + (e["f125"] - 1.0) * (tj_C - 25.0) / 100.0)


def device_power(cfg: Config, dev: Device, tj_C: float) -> float:
    if dev.power_W is not None:
        return float(dev.power_W)
    e = cfg.electrical
    if not dev.conducts:
        return 0.0
    if e["current"] is None or e["rds25"] <= 0:
        raise ValueError(f"device {dev.name}: give power_W or electrical current/rds_on")
    return e["current"] ** 2 * rds_on(cfg, tj_C) + e["switching_W"]


# ---------------------------------------------------------------- correlations

def spreading_resistance(src_area, plate_area, t, k, h_eff):
    """Song, Lee & Au (1994) maximum spreading resistance, circular-equivalent.
    Good to ~10 % for square-ish sources centred on square-ish plates."""
    a = math.sqrt(src_area / math.pi)
    b = math.sqrt(plate_area / math.pi)
    eps = min(a / b, 0.999)
    tau = t / b
    Bi = max(h_eff * b / k, 1e-9)
    lam = math.pi + 1.0 / (math.sqrt(math.pi) * eps)
    phi = (math.tanh(lam * tau) + lam / Bi) / (1.0 + lam / Bi * math.tanh(lam * tau))
    psi = eps * tau / math.sqrt(math.pi) + (1.0 - eps) * phi / math.sqrt(math.pi)
    return psi / (k * a * math.sqrt(math.pi))


def h_vertical_plate(Ts, Ta, L):
    """Churchill-Chu, isothermal vertical plate, full Ra range."""
    p = air_props((Ts + Ta) / 2)
    Ra = G * p["beta"] * max(Ts - Ta, 1e-6) * L ** 3 / (p["nu"] * p["alpha"])
    Nu = (0.825 + 0.387 * Ra ** (1 / 6) / (1 + (0.492 / p["Pr"]) ** (9 / 16)) ** (8 / 27)) ** 2
    return Nu * p["k"] / L


def h_channel(Ts, Ta, s, L):
    """Bar-Cohen & Rohsenow (1984), symmetric isothermal vertical parallel plates."""
    p = air_props((Ts + Ta) / 2)
    Ra_s = G * p["beta"] * max(Ts - Ta, 1e-6) * s ** 3 / (p["nu"] * p["alpha"])
    El = Ra_s * s / L
    Nu = (576.0 / El ** 2 + 2.873 / math.sqrt(El)) ** -0.5
    return Nu * p["k"] / s


def optimum_gap(Ts, Ta, L):
    p = air_props((Ts + Ta) / 2)
    Ra_L = G * p["beta"] * max(Ts - Ta, 1e-6) * L ** 3 / (p["nu"] * p["alpha"])
    return 2.714 * L * Ra_L ** -0.25


def h_rad(Ts, Ta, eps):
    return eps * SIGMA * (Ts ** 2 + Ta ** 2) * (Ts + Ta)


# ---------------------------------------------------------------- sink model

def sink_heat(cfg: Config, Ts: float) -> dict:
    """Heat (W) the sink rejects at a uniform base temperature Ts (K): free convection, or a
    fan when the YAML has airflow.mode: forced."""
    if cfg.airflow["mode"] == "forced":
        return sink_heat_forced(cfg, Ts)
    return sink_heat_free(cfg, Ts)


def sink_heat_forced(cfg: Config, Ts: float) -> dict:
    """Fan air at approach velocity U.
      channels   Teertstra, Culham & Yovanovich (1999), developing laminar flow between plate
                 fins at channel velocity V = channel_ratio * U. An open sink lets much of the
                 air bypass (0.43-0.49 measured in CFD for a 3.8 mm gap, 12 mm fins); without a
                 ratio the channel is taken as ducted, V = U (1 + t/b), which is optimistic.
      outer fins, fin tips and the board's face: laminar flat plate, Nu = 0.664 Re^0.5 Pr^1/3
      radiation  as in the free-convection model, plus the board face (taken at Ts)."""
    af = cfg.airflow
    s, Ta = cfg.sink, cfg.ambient_C + 273.15
    p = air_props((Ts + Ta) / 2)
    W, L, H, t, n, b = s["width"], s["length"], s["fin_h"], s["fin_t"], s["n_fins"], s["gap"]
    U = af["velocity"]
    V = U * af["channel_ratio"] if af.get("channel_ratio") else U * (1 + t / b)
    Re_b = V * b / p["nu"] * (b / L)
    Pr = p["Pr"]
    nu_fd = Re_b * Pr / 2                                       # fully developed limit
    nu_dev = 0.664 * math.sqrt(Re_b) * Pr ** (1 / 3) * math.sqrt(1 + 3.65 / math.sqrt(Re_b))
    Nu = nu_fd * nu_dev / (nu_fd ** 3 + nu_dev ** 3) ** (1 / 3)   # (a^-3 + b^-3)^(-1/3), no overflow
    h_ch = Nu * p["k"] / b
    m = math.sqrt(2 * h_ch / (s["k"] * t))
    eta = math.tanh(m * H) / (m * H)
    A_ch = 2 * (n - 1) * H * L * eta + (n - 1) * b * L
    q_channel = h_ch * A_ch * (Ts - Ta)

    h_fp = 0.664 * math.sqrt(U * L / p["nu"]) * Pr ** (1 / 3) * p["k"] / L
    m_o = math.sqrt(2 * h_fp / (s["k"] * t))
    eta_o = math.tanh(m_o * H) / (m_o * H)
    A_outer = 2 * (H + s["base"]) * L * eta_o + n * t * L
    A_board = cfg.ims["size"][0] * cfg.ims["size"][1]
    q_outer = h_fp * (A_outer + A_board) * (Ts - Ta)

    A_env = W * L + 2 * (H + s["base"]) * L
    q_rad = (s["emissivity"] * A_env + cfg.ims["emissivity"] * A_board) * SIGMA * (Ts ** 4 - Ta ** 4)
    q_conv = q_channel + q_outer
    return {"q_conv": q_conv, "q_rad": q_rad, "q": q_conv + q_rad, "h_channel": h_ch,
            "h_outer": h_fp, "fin_eff": eta, "A_env": A_env, "V_channel": V, "Re_b_star": Re_b,
            "A_conv": A_ch + A_outer + A_board}


def sink_heat_free(cfg: Config, Ts: float) -> dict:
    """Free convection and radiation."""
    s, Ta = cfg.sink, cfg.ambient_C + 273.15
    W, L, H, t, n, gap = s["width"], s["length"], s["fin_h"], s["fin_t"], s["n_fins"], s["gap"]

    h_ch = h_channel(Ts, Ta, gap, L)
    m = math.sqrt(2 * h_ch / (s["k"] * t))
    eta = math.tanh(m * H) / (m * H)
    A_fin_inner = 2 * (n - 1) * H * L            # channel-facing fin faces
    A_floor = (n - 1) * gap * L
    q_channel = h_ch * (eta * A_fin_inner + A_floor) * (Ts - Ta)

    h_out = h_vertical_plate(Ts, Ta, L)
    m_o = math.sqrt(2 * h_out / (s["k"] * t))
    eta_o = math.tanh(m_o * H) / (m_o * H)
    A_outer = 2 * (H + s["base"]) * L            # two outside faces of the end fins
    A_tips = n * t * L
    q_outer = h_out * (eta_o * A_outer + A_tips) * (Ts - Ta)

    A_back = 0.0
    if s["back"] == "free":
        A_back = W * L - cfg.ims["size"][0] * cfg.ims["size"][1]
    q_back = h_out * A_back * (Ts - Ta)

    # Radiation: the fin array's outer envelope radiates as a flat surface with the surface
    # emissivity. Channel cavities really emit a bit more (apparent emissivity > eps), so
    # this errs low, which is the safe side for temperatures.
    A_env = W * L + 2 * (H + s["base"]) * L + A_back
    q_rad = s["emissivity"] * SIGMA * A_env * (Ts ** 4 - Ta ** 4)

    q_conv = q_channel + q_outer + q_back
    return {"q_conv": q_conv, "q_rad": q_rad, "q": q_conv + q_rad, "h_channel": h_ch,
            "h_outer": h_out, "fin_eff": eta, "A_env": A_env,
            "A_conv": eta * A_fin_inner + A_floor + eta_o * A_outer + A_tips + A_back}


def solve_sink_temp(cfg: Config, P: float) -> tuple[float, dict]:
    Ta = cfg.ambient_C + 273.15
    lo, hi = Ta + 1e-3, Ta + 400.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if sink_heat(cfg, mid)["q"] > P:
            hi = mid
        else:
            lo = mid
    return mid, sink_heat(cfg, mid)


# ---------------------------------------------------------------- full network

def network(cfg: Config) -> dict:
    """Iterate losses <-> junction temperature to a fixed point."""
    tj = {d.name: 100.0 for d in cfg.devices}
    for _ in range(100):
        P = {d.name: device_power(cfg, d, tj[d.name]) for d in cfg.devices}
        # copper losses in board islands heat the board and leave through the sink as well
        P_tot = (sum(P.values()) + sum(i["power_W"] for i in cfg.ims.get("islands", []))
                 + cfg.ims.get("power_W", 0.0))
        Ts, sh = solve_sink_temp(cfg, P_tot) if P_tot > 0 else (cfg.ambient_C + 273.15, sink_heat(cfg, cfg.ambient_C + 273.16))
        Ta = cfg.ambient_C + 273.15
        s, im = cfg.sink, cfg.ims
        R_sa = (Ts - Ta) / P_tot if P_tot > 0 else float("nan")
        A_base = s["width"] * s["length"]
        A_ims = im["size"][0] * im["size"][1]
        h_eff_base = 1.0 / (R_sa * A_base) if P_tot > 0 else 10.0
        R_sp_base = spreading_resistance(A_ims, A_base, s["base"], s["k"], h_eff_base)
        R_tim = layers_R(im["below"]) / A_ims
        T_base = Ts + P_tot * R_sp_base
        T_ims_back = T_base + P_tot * R_tim
        h_eff_ims = 1.0 / layers_R(im["below"])
        rows, new_tj = [], {}
        for d in cfg.devices:
            A_d = d.size[0] * d.size[1]
            R_layers = layers_R(im["under"]) / A_d
            R_sp_ims = spreading_resistance(A_d, A_ims, im["substrate"], im["k_substrate"], h_eff_ims)
            T_case = T_ims_back + P[d.name] * (R_layers + R_sp_ims) - 273.15
            T_j = T_case + P[d.name] * d.rth_jc
            new_tj[d.name] = T_j
            rows.append({"name": d.name, "P": P[d.name], "R_layers": R_layers, "R_sp_ims": R_sp_ims,
                         "T_case_C": T_case, "T_j_C": T_j, "tj_max": d.tj_max,
                         "rds_mohm": rds_on(cfg, T_j) * 1e3 if d.power_W is None and d.conducts else None})
        # no devices: nothing depends on Tj, one pass is the answer
        if not tj or max(abs(new_tj[k] - tj[k]) for k in tj) < 0.01:
            tj = new_tj
            break
        tj = new_tj
    return {"P_tot": P_tot, "T_sink_C": Ts - 273.15, "R_sa": R_sa, "R_sp_base": R_sp_base,
            "R_tim": R_tim, "T_base_under_ims_C": T_base - 273.15, "sink": sh, "devices": rows,
            "gap": cfg.sink["gap"], "gap_opt": optimum_gap(Ts, Ta, cfg.sink["length"]),
            "film_K": (Ts + Ta) / 2}
