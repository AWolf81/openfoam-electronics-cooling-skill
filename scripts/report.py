#!/usr/bin/env python3
"""Check a finished (or running) case and write report.md into it.

    python3 report.py CASE_DIR [--quiet]

Gates (see SKILL.md step 5): energy balance within 2 %, heat flow and case temperatures
settled over the last fifth of the run, sink temperature rise within ~25 % of the hand calc.
Exit code 0 = all gates pass, 1 = a gate fails (numbers are still written), 2 = no data.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_dat(path: Path):
    """Rows of a function-object .dat file, as lists of strings; columns from the last header."""
    cols, rows = [], []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            parts = [p.strip() for p in line[1:].split("\t") if p.strip()]
            if parts and parts[0] == "Time":
                cols = parts
            continue
        if line.strip():
            rows.append(line.split())
    return cols, rows


def latest_file(case: Path, region: str, fo: str, name: str):
    """postProcessing/<region>/<fo>/<startTime>/<name>; restarts create new start-time dirs."""
    base = case / "postProcessing" / region / fo
    if not base.is_dir():
        return []
    files = sorted(base.glob(f"*/{name}"), key=lambda p: float(p.parent.name))
    return files


def series(case, region, fo, name):
    """[(time, value)] for a single-value function object, concatenated across restarts."""
    out = {}
    for f in latest_file(case, region, fo, name):
        _, rows = read_dat(f)
        for r in rows:
            try:
                out[float(r[0])] = float(r[1])
            except (ValueError, IndexError):
                pass
    return sorted(out.items())


def wall_heat(case):
    """{time: {patch: integral W}} from wallHeatFlux."""
    out = defaultdict(dict)
    for f in latest_file(case, "air", "airWallHeatFlux", "wallHeatFlux.dat"):
        _, rows = read_dat(f)
        for r in rows:
            if len(r) >= 5:
                out[float(r[0])][r[1]] = float(r[4])
    return dict(sorted(out.items()))


def settle(vals, frac=0.2):
    """(first, last, min, max) of the trailing fraction of a series."""
    if len(vals) < 3:
        return None
    t_end = vals[-1][0]
    t0 = vals[0][0] + (1 - frac) * (t_end - vals[0][0])
    tail = [v for t, v in vals if t >= t0]
    return (tail[0], tail[-1], min(tail), max(tail)) if len(tail) >= 2 else None


def tail_mean(vals, frac=0.2):
    """Mean of the trailing fraction of a series, and the drift of that mean: mean of the last
    half of the window minus mean of the first half. A flow that sheds vortices (forced air
    past a bluff board, or a transient run) oscillates around a steady mean; its balances are
    judged on the mean, and 'settled' means the mean no longer moves, not that it stopped
    oscillating."""
    if not vals:
        return None, None
    t_end = vals[-1][0]
    t0 = vals[0][0] + (1 - frac) * (t_end - vals[0][0])
    tail = [v for t, v in vals if t >= t0] or [vals[-1][1]]
    h = len(tail) // 2
    drift = (sum(tail[h:]) / len(tail[h:]) - sum(tail[:h]) / h) if h else 0.0
    return sum(tail) / len(tail), drift


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    case = Path(a.case)
    meta = json.loads((case / "case-meta.json").read_text())
    hc = meta["hand_calc"]
    cfg = meta["config"]
    Ta = cfg.get("ambient_C", 25.0)
    P_in = sum(meta["power_W"].values())

    wh = wall_heat(case)
    if not wh:
        print("no wallHeatFlux data yet; has the solver run?")
        return 2
    t_last = max(wh)
    q_air_series = [(t, sum(v for k, v in d.items() if k.startswith("air_to_"))) for t, d in wh.items()]
    Q_air, _ = tail_mean(q_air_series)

    rad = series(case, "air", "radiationShare", "surfaceFieldValue.dat")
    Q_rad = -tail_mean(rad)[0] if rad else None     # qr is positive into the wall

    # Parts that leave the domain (cables): heat out through their far end, h (int T dA - T_inf A).
    end_series = defaultdict(float)
    for r, fe in (meta.get("far_end") or {}).items():
        for t, iT in series(case, r, f"farEnd_{r}", "surfaceFieldValue.dat"):
            end_series[t] += fe["h"] * (iT - fe["T_inf_K"] * fe["A_m2"])
    end_series = sorted(end_series.items())
    Q_end = tail_mean(end_series)[0] if end_series else 0.0
    q_tot_series = [(t, q + dict(end_series).get(t, 0.0)) for t, q in q_air_series]
    Q_out = Q_air + Q_end

    T_sink = series(case, "heatsink", "Tavg_heatsink", "volFieldValue.dat")
    T_sink_mean = tail_mean(T_sink)[0] if T_sink else None
    devs = []
    gates = []  # filled below
    for d in cfg.get("devices") or []:
        n = d["name"]
        s = series(case, n, f"case_{n}", "surfaceFieldValue.dat")
        if not s:
            continue
        T_case, drift = tail_mean(s)
        T_case -= 273.15
        P = meta["power_W"][n]
        rjc = d.get("rth_jc", 0.5)
        hc_row = next(r for r in hc["devices"] if r["name"] == n)
        devs.append({"name": n, "P": P, "T_case": T_case, "Tj": T_case + P * rjc,
                     "tj_max": d.get("tj_max_C", 175.0), "Tj_hand": hc_row["T_j_C"], "drift": drift})
    # No devices (bare heat sink heated through the board): the result is the base temperature
    # (mean over the sink's contact face with the board) and the board maximum.
    bare = None
    if not cfg.get("devices"):
        s_base = series(case, "heatsink", "Tbase_heatsink", "surfaceFieldValue.dat")
        s_board = series(case, "ims", "Tmax_ims", "volFieldValue.dat")
        if s_base and s_board:
            T_base, drift_base = tail_mean(s_base)
            bare = {"T_base": T_base - 273.15, "drift": drift_base,
                    "T_board": tail_mean(s_board)[0] - 273.15,
                    "T_base_hand": hc["T_base_under_ims_C"],
                    "T_board_hand": hc["T_base_under_ims_C"] + hc["P_tot"] * hc["R_tim"]}

    # ---- physical sanity: the defects this setup has actually had show up here first
    U_s, Tair_s = [], []
    for f in latest_file(case, "air", "airMinMax", "fieldMinMax.dat"):
        for line in f.read_text().splitlines():
            if line.startswith("#") or not line.strip():
                continue
            c = [x.strip() for x in line.split("\t")]
            if len(c) >= 6:
                (U_s if c[1] == "mag(U)" else Tair_s if c[1] == "T" else []).append((float(c[0]), float(c[5])))
    T_solid_max = max(tail_mean(series(case, r, f"Tmax_{r}", "volFieldValue.dat"))[0] or 0.0
                      for r in meta["regions"] if r != "air")
    # Free convection: metres per second mean a spurious draft. With a fan (forced_air in
    # case-meta.json) the reference is the inlet speed; flow squeezed past the sink reaches
    # 1.5-2.5x it, much more means a pressure or boundary defect.
    U_in = (meta.get("forced_air") or {}).get("U_approach_m_s")
    U_lim = 3.0 * U_in if U_in else 1.0
    if U_s:
        U_max = max(v for _, v in U_s[-max(1, len(U_s) // 5):])
        gates.append((f"Air speed plausible ({'< 3x fan inlet ' + format(U_in, 'g') + ' m/s' if U_in else 'free convection, < 1 m/s'})",
                      U_max < U_lim, f"peak {U_max:.3f} m/s (limit {U_lim:.2f}); far above it means a "
                      "spurious draft (open-boundary pressure, hydrostatic start)"))
    if Tair_s:
        T_air_max = tail_mean(Tair_s)[0]
        gates.append(("No air hotter than the hottest solid", T_air_max <= T_solid_max + 0.5,
                      f"air max {T_air_max - 273.15:.1f} C, solid max {T_solid_max - 273.15:.1f} C "
                      "(means over the end of the run)"))
    flows = {}
    for f in sorted((case / "postProcessing" / "air").glob("massFlow_*")):
        v = series(case, "air", f.name, "surfaceFieldValue.dat")
        if v:
            flows[f.name.removeprefix("massFlow_")] = tail_mean(v)[0]
    if flows:
        through = sum(abs(v) for v in flows.values()) / 2
        net = sum(flows.values())
        gates.append(("Mass balance over the open boundaries", abs(net) <= 0.02 * max(through, 1e-12),
                      f"net {net:.2e} kg/s of {through:.2e} kg/s through-flow; "
                      + ", ".join(f"{k} {v:+.2e}" for k, v in flows.items())))

    # Air energy balance: convective heat put into the air must leave through the open
    # boundaries (radiation passes through the transparent air). If it does not, the air flow
    # has not settled and the solid temperatures rest on a flow field that is still wrong.
    H = []
    for f in sorted((case / "postProcessing" / "air").glob("enthalpyFlow_*")):
        v = series(case, "air", f.name, "surfaceFieldValue.dat")
        if v:
            H.append(tail_mean(v)[0])
    # Conduction through the open boundaries (where inflow is pinned at ambient next to warm
    # cells) also carries heat out; add it so the balance counts every path.
    K = []
    for f in sorted((case / "postProcessing" / "air").glob("condFlow_*")):
        v = series(case, "air", f.name, "surfaceFieldValue.dat")
        if v:
            K.append(-meta.get("air_kappa", 0.0273) * tail_mean(v)[0])
    if H:
        H_out = sum(H) + sum(K)
        Q_conv = Q_air - (Q_rad or 0.0)
        gates.append(("Air energy balance (convective heat leaves through the boundaries)",
                      abs(H_out - Q_conv) <= 0.10 * max(P_in, 1e-9),
                      f"{H_out:.2f} W carried out by the air ({sum(H):.2f} W flow, {sum(K):.2f} W boundary conduction) "
                      f"vs {Q_conv:.2f} W convected from the solids"))

    bal = (Q_out - P_in) / P_in if P_in else 0.0
    gates.append(("Energy balance within 2 %", abs(bal) <= 0.02,
                  f"{Q_out:.3f} W out of the solids ({Q_air:.3f} W into the air"
                  + (f", {Q_end:.3f} W through cable ends" if end_series else "")
                  + f") vs {P_in:.3f} W in ({100 * bal:+.1f} %)"))
    st = settle(q_tot_series)
    mean_q, drift_q = tail_mean(q_tot_series)
    if st:
        ch = abs(drift_q) / max(P_in, 1e-9)
        band = (st[3] - st[2]) / max(P_in, 1e-9)
        gates.append(("Heat flow settled (mean over the last 20 % of run)", ch <= 0.005,
                      f"mean moved {100 * ch:.2f} % of the loss, oscillation band {100 * band:.2f} %"))
    drifts = [d["drift"] for d in devs if d["drift"] is not None]
    if bare:
        gates.append(("Base temperature settled (mean over the last 20 % of run)", abs(bare["drift"]) <= 0.5,
                      f"drift of the mean {abs(bare['drift']):.2f} K"))
    if drifts:
        gates.append(("Case temperatures settled (mean over the last 20 % of run)",
                      max(abs(x) for x in drifts) <= 0.5,
                      f"largest drift of the mean {max(abs(x) for x in drifts):.2f} K"))
    if T_sink:
        rise_cfd = T_sink_mean - 273.15 - Ta
        rise_hc = hc["T_sink_C"] - Ta
        dev = (rise_cfd - rise_hc) / rise_hc
        gates.append(("Sink rise within 25 % of hand calc", abs(dev) <= 0.25,
                      f"CFD {rise_cfd:.2f} K vs hand calc {rise_hc:.2f} K ({100 * dev:+.0f} %)"))

    ok = all(g[1] for g in gates)
    L = [f"# Thermal result: {cfg.get('name', case.name)}", "",
         f"Case `{case}`, resolution {meta['resolution']}, iteration {t_last:g}, ambient {Ta:g} C.", ""]
    if not cfg.get("devices"):
        L += ["## Board and base temperature", "",
              "No devices: result is the board/base temperature (the heat enters through the board).", ""]
        if bare:
            R = lambda T: (T - Ta) / P_in if P_in else float("nan")  # noqa: E731
            L += ["| Quantity | CFD C | R to ambient K/W | Hand calc C |", "|---|---|---|---|",
                  f"| Base under the board (mean of the sink's contact face) | {bare['T_base']:.1f} | "
                  f"{R(bare['T_base']):.3f} | {bare['T_base_hand']:.1f} |",
                  f"| Board maximum | {bare['T_board']:.1f} | {R(bare['T_board']):.3f} | {bare['T_board_hand']:.1f} |"]
            if T_sink:
                L.append(f"| Heat sink mean | {T_sink_mean - 273.15:.1f} | {R(T_sink_mean - 273.15):.3f} | "
                         f"{hc['T_sink_C']:.1f} |")
        else:
            L.append("No base temperature data (Tbase_heatsink) yet.")
        L.append("")
    else:
        L += ["## Junction temperatures", "",
              "| Device | Loss W | T case C | Tj C | Tj max C | Margin K | Hand calc Tj C |",
              "|---|---|---|---|---|---|---|"]
        for d in devs:
            L.append(f"| {d['name']} | {d['P']:.2f} | {d['T_case']:.1f} | {d['Tj']:.1f} | {d['tj_max']:.0f} | "
                     f"{d['tj_max'] - d['Tj']:.0f} | {d['Tj_hand']:.1f} |")
        L += ["", "Tj = hottest point of the package contact face + loss x Rth(j-c).", ""]
    L += ["## Heat path", "", f"- Loss put in: {P_in:.2f} W",
          f"- Heat leaving the solids into the air: {Q_air:.2f} W"]
    if Q_rad is not None:
        L.append(f"- of which radiation: {Q_rad:.2f} W ({100 * Q_rad / max(Q_air, 1e-9):.0f} %); "
                 f"hand calc {hc['sink']['q_rad']:.2f} W ({100 * hc['sink']['q_rad'] / hc['P_tot']:.0f} %)")
    if end_series:
        L.append(f"- Heat leaving through the cable ends (far_end): {Q_end:.2f} W")
    if T_sink:
        L.append(f"- Mean sink temperature: {T_sink_mean - 273.15:.1f} C (hand calc {hc['T_sink_C']:.1f} C)")
    L.append("- Values are means over the last 20 % of the run.")
    L += ["", "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    for name, passed, detail in gates:
        L.append(f"| {name} | {'pass' if passed else 'FAIL'} | {detail} |")
    L += ["", "Verdict: " + ("all checks pass." if ok else
                             "not yet trustworthy; fix or explain the failing check first."), ""]
    (case / "report.md").write_text("\n".join(L))
    if not a.quiet:
        print("\n".join(L))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
