# openfoam-electronics-cooling

A [Claude Code](https://claude.com/claude-code) skill for thermal simulation of power electronics:
MOSFETs, IGBTs, diodes or regulators on an IMS or PCB, mounted to a finned aluminium heat sink and
cooled by free convection or a fan, with radiation.

You describe the design in one YAML file. The skill then works through these steps:

1. **Losses**, with Rds(on) at temperature.
2. **Hand calculation** with a thermal network. It is the yardstick for the CFD, and sometimes it
   already answers the question.
3. **CFD** of conjugate heat transfer (`chtMultiRegionSimpleFoam`, OpenFOAM v2412 in Docker).
4. **Checks**: energy balance, convergence, and hand calc against CFD.
5. **Report** in Word/PDF with junction temperatures, margins, figures and a warm-up video.

## Install

```bash
git clone https://github.com/AWolf81/openfoam-electronics-cooling-skill ~/.claude/skills/openfoam-electronics-cooling
bash ~/.claude/skills/openfoam-electronics-cooling/scripts/setup_env.sh
```

The target folder must be named `openfoam-electronics-cooling`, the skill's name.

Requirements:
- Docker. The OpenFOAM image `opencfd/openfoam-default:2412` (about 2.2 GB) is pulled on first run.
- [uv](https://docs.astral.sh/uv/), for the Python environment used by reports and renders.

Then ask Claude Code something like *"Will 10 MOSFETs at 300 A on this heat sink overheat?"*.

## Example

[`assets/example-case.yaml`](assets/example-case.yaml) is the input template. It was tested on the
Infineon 48 V battery switch reference design (R 48V BATT SWITCH10) at 300 A.
