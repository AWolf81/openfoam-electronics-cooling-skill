#!/usr/bin/env python3
"""Fan cases: how much of the approach air goes through the fin channels.

Samples the air inside the fin envelope (between base and fin tips, across the sink width)
in a band at mid-length and prints the mean velocity along the fins there, and its ratio to
the fan's approach velocity: the airflow.channel_ratio the hand calc uses. An open sink lets
half or more of the air go around it (0.43-0.49 measured for a 3.8 mm gap, 12 mm fins).

    <report venv python> channel_flow.py CASE_DIR
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cooling_model import MM, load_config  # noqa: E402


def main() -> int:
    import pyvista as pv
    case = Path(sys.argv[1])
    meta = json.loads((case / "case-meta.json").read_text())
    cfg = load_config(case / "case.yaml")
    steps = sorted((case / "VTK" / "air").glob("case_*/internal.vtu"),
                   key=lambda p: float(p.parent.name.split("_")[1]))
    if not steps:
        print("no VTK/air output; run the case (Allrun ends with foamToVTK)")
        return 2
    m = pv.read(str(steps[-1]))
    s = cfg.sink
    pts = m.cell_centers().points
    U = m.cell_data["U"]
    vol = m.compute_cell_sizes(length=False, area=False)["Volume"]
    L = s["length"]
    sel = ((pts[:, 0] > s["base"]) & (pts[:, 0] < s["base"] + s["fin_h"]) & (pts[:, 1] > 0)
           & (pts[:, 1] < s["width"]) & (np.abs(pts[:, 2] - L / 2) < 0.04 * L))
    Uz = U[sel, 2]
    v = vol[sel]
    mean = float(np.sum(Uz * v) / np.sum(v))
    print(f"fin channels at mid-length: mean velocity along the fins {mean:.3f} m/s, "
          f"max {Uz.max():.3f} m/s ({sel.sum()} cells)")
    fa = meta.get("forced_air") or {}
    U0 = fa.get("U_approach_m_s")
    if U0:
        print(f"approach {U0:g} m/s ({fa.get('direction', 'fins')}): channel_ratio = {mean / U0:.2f} "
              f"(ducted would be {1 + s['fin_t'] / s['gap']:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
