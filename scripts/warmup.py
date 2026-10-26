#!/usr/bin/env python3
"""Warm-up from cold: how fast the junctions approach their steady temperature.

    python3 warmup.py CASE_DIR [--hours 2] [--out warmup.csv]
    python3 warmup.py case.yaml            # without CFD: calibrated to the hand calc only

A lumped model with real heat capacities: heat sink, board spreader and one node per device (its case
temperature; the die follows within milliseconds and is added as P * Rth(j-c)). Resistances
between the nodes and the sink's heat-rejection curve are calibrated so the end point equals
the converged CFD (or the hand calc), while the curve's shape comes from the free-convection
and radiation laws (h grows with temperature rise) and the loss grows with Tj. Running a full
CFD transient with real heat capacity would take hours for a sink with a ~15 minute time
constant; this takes a second and lands on the same steady state by construction.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cooling_model import Config, device_power, load_config, network, sink_heat  # noqa: E402

AL_RHO_CP = 2700 * 900          # J/(m3 K), aluminium
PKG_RHO_CP = 2.2e6              # J/(m3 K), copper tab + mould compound, rough


def last_value(case: Path, region: str, fo: str, name: str):
    files = sorted((case / "postProcessing" / region / fo).glob(f"*/{name}"),
                   key=lambda p: float(p.parent.name))
    for f in reversed(files):
        rows = [l.split() for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")]
        if rows:
            return float(rows[-1][1])
    return None


def attached_to(cfg: Config, part: dict):
    """The device an extra solid hangs on: solids.attached_to, or a name starting with the
    device's name and '_' (bat_p_lug, bat_p_cable -> bat_p). None = it heats the board."""
    if part.get("attached_to"):
        return part["attached_to"]
    return next((d.name for d in cfg.devices if part["name"].startswith(d.name + "_")), None)


def calibration(cfg: Config, case: Path | None):
    """Steady node temperatures (K) and powers the model must reproduce.

    The lumped model has a node per device, one board node and the sink. Powers that are not
    devices are mapped onto those nodes so the totals match the CFD:
      board copper (region ims, islands) and extra solids attached to nothing -> board node
      extra solids attached to a device (lug, cable) -> that device, minus the heat the CFD
      sends out through the part's far end (a cable leaving the model)
    P['_board'] carries the board node's power."""
    hc = network(cfg)
    P = {d["name"]: d["P"] for d in hc["devices"]}
    P["_board"] = sum(i["power_W"] for i in cfg.ims.get("islands", [])) + cfg.ims.get("power_W", 0.0)
    Ts = hc["T_sink_C"] + 273.15
    Ti = hc["T_base_under_ims_C"] + 273.15 + hc["P_tot"] * hc["R_tim"]
    Tc = {d["name"]: d["T_case_C"] + 273.15 for d in hc["devices"]}
    source = "hand calc"
    if case is not None:
        meta = json.loads((case / "case-meta.json").read_text())
        allP = dict(meta["power_W"])
        P = {d.name: allP.pop(d.name) for d in cfg.devices}
        P["_board"] = sum(allP.pop(n, 0.0) for n in ["ims"] + [i["name"] for i in cfg.ims.get("islands", [])])
        for part in cfg.solids:
            q = allP.pop(part["name"], 0.0)
            fe = (meta.get("far_end") or {}).get(part["name"])
            if fe:
                iT = last_value(case, part["name"], f"farEnd_{part['name']}", "surfaceFieldValue.dat")
                if iT is not None:
                    q -= fe["h"] * (iT - fe["T_inf_K"] * fe["A_m2"])
            P[attached_to(cfg, part) or "_board"] += q
        ts = last_value(case, "heatsink", "Tavg_heatsink", "volFieldValue.dat")
        ti = last_value(case, "ims", "Tmax_ims", "volFieldValue.dat")
        tc = {d.name: last_value(case, d.name, f"case_{d.name}", "surfaceFieldValue.dat") for d in cfg.devices}
        if ts and ti and all(tc.values()):
            Ts, Ti, Tc, source = ts, ti, tc, "CFD"
    return P, Ts, Ti, Tc, source


def simulate(cfg: Config, case: Path | None, hours: float, dt: float = 0.05):
    P0, Ts0, Ti0, Tc0, source = calibration(cfg, case)
    P_board = P0.pop("_board", 0.0)
    Tc0 = dict(Tc0)
    Ta = cfg.ambient_C + 273.15
    s, im = cfg.sink, cfg.ims
    P_tot = sum(P0.values()) + P_board
    k_cal = P_tot / sink_heat(cfg, Ts0)["q"]              # match CFD heat rejection at steady state
    R_is = max(Ti0 - Ts0, 1e-6) / P_tot

    V_sink = s["width"] * s["length"] * s["base"] + s["n_fins"] * s["fin_t"] * s["fin_h"] * s["length"]
    C_s = V_sink * AL_RHO_CP
    sp = im["spreader"]
    C_i = im["size"][0] * im["size"][1] * sp["t"] * sp["rho"] * sp["cp"]
    C_d = {d.name: d.size[0] * d.size[1] * d.size[2] * PKG_RHO_CP for d in cfg.devices}

    # Device-to-board resistance from the steady state, R = (Tc - Ti) / P. It can come out ~0
    # or negative: the board node is the board's hottest point, a small part away from it (a
    # sensor, a terminal) is cooler, and a terminal whose cable draws heat has P < 0 with
    # Tc < Ti (R positive again). Floor R at the explicit step's stability limit 1.2 dt / C
    # and move that part's target to match, so the steady state stays exact.
    R_d = {}
    for d in cfg.devices:
        p, dT = P0[d.name], Tc0[d.name] - Ti0
        R_min = 1.2 * dt / C_d[d.name]
        R = dT / p if abs(p) > 1e-9 else R_min
        if R < R_min:
            R = R_min
            Tc0[d.name] = Ti0 + p * R
        R_d[d.name] = R
    # Parts with lugs, cables ... folded in carry that extra loss as a constant.
    fold = {d.name: P0[d.name] - device_power(cfg, d, Tc0[d.name] - 273.15 + P0[d.name] * d.rth_jc)
            for d in cfg.devices if any(attached_to(cfg, p) == d.name for p in cfg.solids)}

    def loss(d, Tc):
        tj = Tc - 273.15 + P0[d.name] * d.rth_jc
        return device_power(cfg, d, tj) + fold.get(d.name, 0.0)

    Ts, Ti = Ta, Ta
    Tc = {d.name: Ta for d in cfg.devices}
    rows = []
    t, n_out = 0.0, max(1, int(10 / dt))   # sample every 10 s
    step = 0
    while t <= hours * 3600 + 1e-9:
        Pd = {d.name: loss(d, Tc[d.name]) for d in cfg.devices}
        if step % n_out == 0:
            rows.append({"t_s": round(t, 2), "T_sink_C": Ts - 273.15, "T_ims_C": Ti - 273.15,
                         **{f"T_case_{k}_C": v - 273.15 for k, v in Tc.items()},
                         **{f"Tj_{d.name}_C": Tc[d.name] - 273.15 + Pd[d.name] * d.rth_jc for d in cfg.devices},
                         "P_W": sum(Pd.values())})
        q_di = {k: (Tc[k] - Ti) / R_d[k] for k in Tc}
        q_is = (Ti - Ts) / R_is
        q_sa = k_cal * sink_heat(cfg, Ts)["q"] if Ts > Ta + 1e-6 else 0.0
        for k in Tc:
            Tc[k] += dt * (Pd[k] - q_di[k]) / C_d[k]
        Ti += dt * (sum(q_di.values()) + P_board - q_is) / C_i
        Ts += dt * (q_is - q_sa) / C_s
        t += dt
        step += 1

    tj_cols = [f"Tj_{d.name}_C" for d in cfg.devices]
    hottest = max(tj_cols, key=lambda c: rows[-1][c])
    T_end = rows[-1][hottest]
    rise = T_end - cfg.ambient_C

    def t_frac(f):
        for r in rows:
            if r[hottest] - cfg.ambient_C >= f * rise:
                return r["t_s"]
        return None

    summary = {"calibrated_to": source, "C_sink_J_K": C_s, "C_ims_J_K": C_i, "C_device_J_K": C_d,
               "R_ims_sink_K_W": R_is, "R_device_ims_K_W": R_d, "k_cal": k_cal,
               "hottest": hottest, "Tj_end_C": T_end, "t63_s": t_frac(0.632), "t90_s": t_frac(0.9),
               "t99_s": t_frac(0.99), "hours": hours,
               "steady_target": {"T_sink_C": Ts0 - 273.15, "T_ims_C": Ti0 - 273.15,
                                 **{f"T_case_{k}_C": v - 273.15 for k, v in Tc0.items()}}}
    return rows, summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="case directory (with case-meta.json) or a case YAML")
    ap.add_argument("--hours", type=float, default=2.0)
    ap.add_argument("--out", help="CSV path (default: <case>/warmup.csv)")
    a = ap.parse_args()
    src = Path(a.source)
    case = src if src.is_dir() else None
    cfg = load_config(src / "case.yaml" if case else src)
    rows, summ = simulate(cfg, case, a.hours)
    out = Path(a.out) if a.out else (case / "warmup.csv" if case else Path("warmup.csv"))
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    out.with_suffix(".json").write_text(json.dumps(summ, indent=2, default=float))
    m = lambda s: f"{s / 60:.1f} min" if s is not None else "not reached"  # noqa: E731
    print(f"Warm-up ({summ['calibrated_to']}-calibrated): hottest {summ['hottest']} ends at "
          f"{summ['Tj_end_C']:.1f} C after {a.hours:g} h")
    print(f"  63 % of the rise after {m(summ['t63_s'])}, 90 % after {m(summ['t90_s'])}, "
          f"99 % after {m(summ['t99_s'])}")
    print(f"  heat capacity: sink {summ['C_sink_J_K']:.0f} J/K, {cfg.ims['spreader']['name']} {summ['C_ims_J_K']:.1f} J/K")
    print(f"  wrote {out} and {out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
