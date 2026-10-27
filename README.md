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

## Usage

Start Claude Code in a new folder for your design. The skill writes `case.yaml` and all CFD cases
under `cases/` there.

```bash
mkdir -p ~/thermal/my-power-stage && cd ~/thermal/my-power-stage
claude
```

Then describe the design, with as many numbers as you have:

> Will my power stage overheat? 10 MOSFETs (IAUT300N08S5N011, TOLL) as 5 back-to-back pairs at
> 300 A continuous, 25 °C ambient. Copper-core board, 100 × 75 mm, on a Fischer SK 81 heat sink,
> black anodised. A 12 V PC fan blows along the fins. Do a hand calc first, then run the CFD
> and give me a report.

Datasheets, a reference manual (PDF or link) and the board layout help: Claude reads the values from
them. Anything missing is asked for or marked as an assumption (`# CHECK:` in `case.yaml`).

## Example: Infineon 48 V battery switch at 300 A

The skill was tested on the Infineon reference design R 48V BATT SWITCH10:
[UG-2021-20, *48V Battery Switch Reference Design*](https://www.farnell.com/datasheets/3739859.pdf).
It has 10 back-to-back IAUT300N08S5N011 MOSFETs on a copper-core board and a finned heat sink, cooled
by a low-speed 12 V PC fan 20 cm away. In the user guide's test (section 4.1), the board settles at a
maximum of 80 °C after 30 minutes at 300 A and 25 °C ambient.

**Measurement** (UG Fig. 46, IR image after 30 min at 300 A, © Infineon Technologies):

![Infineon IR image](docs/infineon-fig46-ir.png)

**Simulation** (CFD steady state, 2.4 m/s fan blowing onto the fin tips, k-ω SST, lugs and 50 mm²
cables, copper losses in the board; IR-style palette):

![CFD result](docs/cfd-result.png)

| Fan (not given in the user guide) | Hottest FET case | Measured board max |
|---|---|---|
| 1.5 m/s onto the fin tips (a low-speed fan) | 99 °C | 80 °C |
| 2.4 m/s onto the fin tips | 86 °C | 80 °C |
| about 2.8 m/s onto the fin tips | about 80 °C | 80 °C |
| 2.4 m/s along the fins | 89 °C (normal mesh) | 80 °C |

**The model matches the measurement at about 2.8 m/s, which is a fit, not a prediction.** The
user guide gives neither the fan speed nor its direction. At 2.4 m/s the model is 6 K hot. At a
truly low fan speed it would be about 19 K hot.

Steps that brought the model from about 21 K to 6 K hot:
- cables sized from their temperature in the IR image (50 mm² instead of 35 mm²): −5.5 K
- turbulent air (k-ω SST) instead of laminar: −3 K, and the air-side energy balance closed
- the fan blowing onto the fins instead of along them: −4 K at the same speed

Checks: solids energy balance within 2 %, and the normal mesh within 1 K of the coarse one.

**Still open:** the simulated warm-up reaches 90 % in about 5 min (with the heat capacity of the lugs and
cables included), while the measurement (UG Fig. 47)
takes about 9 min.

[`assets/example-case.yaml`](assets/example-case.yaml) is the input template.

## License

MIT, see [LICENSE](LICENSE). The Infineon IR image in `docs/` is © Infineon Technologies, reproduced from
UG-2021-20 for comparison, and is not covered by the MIT license.
