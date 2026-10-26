#!/usr/bin/env bash
# One-time setup of the Python environment for reports, renders and Gerber import.
# Creates ~/.local/share/openfoam-electronics-cooling/venv (override with OEC_VENV).
# The case generator and hand calc do not need it; make_report.py and gerber tools do.
set -euo pipefail
venv=${OEC_VENV:-$HOME/.local/share/openfoam-electronics-cooling/venv}
command -v uv >/dev/null || { echo "setup_env.sh: needs uv (https://docs.astral.sh/uv/)" >&2; exit 2; }
[ -x "$venv/bin/python" ] || uv venv --python 3.12 "$venv"
# pyvista (MIT): offscreen 3D renders of the VTK output; python-docx (MIT): Word report;
# gerbonara (Apache-2.0): Gerber/Excellon reader; matplotlib, numpy, pyyaml, imageio for figures and video.
uv pip install --python "$venv/bin/python" \
    "pyvista>=0.44" "python-docx>=1.1" "gerbonara>=1.4" matplotlib numpy pyyaml "imageio[ffmpeg]"
"$venv/bin/python" -c "import pyvista, docx, gerbonara; print('ok:', pyvista.__version__)"
echo "$venv/bin/python"
