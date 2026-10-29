#!/usr/bin/env python3
"""First-order thermal network for a case YAML. Run this before any CFD.

    python3 hand_calc.py case.yaml            # human-readable table
    python3 hand_calc.py case.yaml --json     # machine-readable, used by report.py

The numbers are what the CFD result must land near (typically within 15-25 % on sink
temperature rise). A larger gap means either the CFD case or the inputs are wrong.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cooling_model import load_config, network  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--velocity", type=float, help="fan approach velocity, m/s (overrides airflow; "
                    "turns a free-convection file into a fan case along the fins)")
    ap.add_argument("--calibrate", type=float, metavar="T_CASE_C",
                    help="find the fan velocity at which the hottest case reaches this temperature "
                         "(e.g. a measured board maximum)")
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.velocity is not None:
        cfg.airflow = {"mode": "forced", "direction": cfg.airflow.get("direction", "fins"),
                       "channel_ratio": cfg.airflow.get("channel_ratio"), "velocity": a.velocity}
    if a.calibrate is not None:
        if cfg.airflow["mode"] != "forced":
            cfg.airflow = {"mode": "forced", "direction": "fins", "channel_ratio": None, "velocity": 1.0}
        lo, hi = 0.05, 20.0
        for _ in range(50):
            cfg.airflow["velocity"] = mid = (lo * hi) ** 0.5
            r = network(cfg)
            # no devices: the hottest point is the board's heated face
            hot = max((d["T_case_C"] for d in r["devices"]),
                      default=r["T_base_under_ims_C"] + r["P_tot"] * r["R_tim"])
            lo, hi = (mid, hi) if hot > a.calibrate else (lo, mid)
        print(f"fan approach velocity {mid:.2f} m/s gives a hottest case of {a.calibrate:g} C "
              f"(channel_ratio {cfg.airflow.get('channel_ratio') or 'ducted'})")
        return 0
    r = network(cfg)
    if a.json:
        print(json.dumps(r, indent=2, default=float))
        return 0

    s = r["sink"]
    Ta = cfg.ambient_C
    print(f"Case: {cfg.name}   ambient {Ta:.1f} C")
    af = cfg.airflow
    print("Cooling: free convection + radiation" if af["mode"] == "free" else
          f"Cooling: fan {af['velocity']:g} m/s {af['direction']}, channel ratio "
          f"{af.get('channel_ratio') or 'ducted'} (channel {s.get('V_channel', 0):.2f} m/s) + radiation")
    print(f"Total loss            {r['P_tot']:8.2f} W")
    for d in r["devices"]:
        rds = f"  Rds(on)@Tj {d['rds_mohm']:.2f} mOhm" if d["rds_mohm"] else ""
        print(f"  {d['name']:<10} {d['P']:8.2f} W{rds}")
    print()
    print(f"Sink mean temperature {r['T_sink_C']:8.1f} C   (rise {r['T_sink_C'] - Ta:.1f} K)")
    print(f"  R_sink-air          {r['R_sa']:8.3f} K/W")
    print(f"  convection          {s['q_conv']:8.2f} W   h_channel {s['h_channel']:.2f}, "
          f"h_outer {s['h_outer']:.2f} W/m2K, fin efficiency {s['fin_eff']:.2f}")
    print(f"  radiation           {s['q_rad']:8.2f} W   ({100 * s['q_rad'] / s['q']:.0f} % of total, "
          f"envelope {s['A_env'] * 1e4:.0f} cm2)")
    if af["mode"] == "free":
        print(f"  fin gap             {r['gap'] * 1e3:8.2f} mm  (natural-convection optimum ~{r['gap_opt'] * 1e3:.1f} mm)")
    print(f"Base under board      {r['T_base_under_ims_C']:8.1f} C   spreading {r['R_sp_base']:.3f} K/W")
    print(f"Board to sink layers  {r['R_tim']:8.3f} K/W")
    print()
    if not r["devices"]:
        # bare heat sink: the heat enters through the board, so the result is a board/base temperature
        T_board = r["T_base_under_ims_C"] + r["P_tot"] * r["R_tim"]
        print("No devices: the heat enters through the board (board.power_W); the result is the")
        print("board/base temperature.")
        # base temperature and R_sink-air are printed above; here only what is new
        print(f"R base-air            {(r['T_base_under_ims_C'] - Ta) / r['P_tot']:8.3f} K/W  "
              f"(base under board {r['T_base_under_ims_C']:.1f} C, above)")
        print(f"Board (heated face)   {T_board:8.1f} C   R board-air "
              f"{(T_board - Ta) / r['P_tot']:.3f} K/W")
        print()
    worst = None
    if r["devices"]:
        print(f"{'device':<10} {'P W':>7} {'layers K/W':>11} {'spread K/W':>11} {'Tcase C':>8} {'Tj C':>7} {'margin':>7}")
        for d in r["devices"]:
            m = d["tj_max"] - d["T_j_C"]
            worst = m if worst is None else min(worst, m)
            print(f"{d['name']:<10} {d['P']:7.2f} {d['R_layers']:11.3f} {d['R_sp_ims']:11.3f} "
                  f"{d['T_case_C']:8.1f} {d['T_j_C']:7.1f} {m:7.1f}")
        print()
    if worst is not None and worst < 25:
        print(f"WARNING: junction margin {worst:.0f} K is below the usual 25 K design margin.")
    if af["mode"] == "free" and abs(r["gap"] - r["gap_opt"]) / r["gap_opt"] > 0.4:
        print("NOTE: fin gap is far from the natural-convection optimum; the sink is "
              "under-using its area (too tight chokes the flow, too wide wastes fins).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
