---
name: openfoam-electronics-cooling
description: Thermal simulation of power electronics with OpenFOAM - MOSFETs, IGBTs, diodes or regulators on an IMS or PCB mounted to a finned aluminium heat sink, cooled by free (natural) convection or a fan, and radiation. Computes losses (Rds(on) at temperature), a hand-calc thermal network, then builds, runs and checks a conjugate-heat-transfer CFD case (chtMultiRegionSimpleFoam, OpenFOAM v2412 in Docker) and reports junction temperatures with an energy balance. Use this whenever someone asks whether a power stage will overheat, wants a heat sink sized or checked, asks for junction or case temperatures, thermal resistance, a "thermal simulation" or "CFD of the heat sink", compares heat sinks, fin counts, TIMs, board stacks or fan speeds, or mentions OpenFOAM together with heat, cooling or electronics, even if they never say CFD. Not for aerodynamics, general fluid flow, or chip-level (die) thermal design.
---

# OpenFOAM electronics cooling

Turns a description of a power stage on a heat sink into junction temperatures you can
trust, with the least compute that answers the question. The order matters: the hand
calculation comes first because it is the yardstick that tells you whether the CFD is right,
and sometimes it already answers the question.

Everything is driven by one YAML file per design (template: `assets/example-case.yaml`).
The scripts share one model (`scripts/cooling_model.py`), so the hand calc and the CFD case
always use the same numbers.

## Workflow

### 1. Intake: get the inputs, mark every assumption

Work in the current working directory: `case.yaml` goes there and every case under `cases/`.
All paths below are relative to it. If that directory is the home directory or this skill's
folder, ask the user for a project folder (suggest `~/thermal/<design-name>`), create it and
work there.

Copy `assets/example-case.yaml` into that folder and fill it in. What matters most, in order
of how much it moves the junction temperature:

1. **Loss.** Current, Rds(on) at 25 C (datasheet *max*, not typical) and its factor at 125 C
   from the normalised curve. Back-to-back MOSFETs (bidirectional switch) both carry the
   full current, so each dissipates I^2 * Rds(on). The voltage rating does not create heat in
   a static switch; switching losses only matter if it switches (`switching_loss_W_per_device`).
2. **Ambient temperature.** Use the worst case the product sees (inside an enclosure is often
   40-50 C), not 25 C.
3. **Heat sink:** width, length (vertical, along the fins), base thickness, fin count,
   thickness, height, alloy, surface finish. Free-convection fins must run vertically; if the
   user's sink is horizontal, say that it loses much of its performance and model it as given
   only after flagging this.
4. **Emissivity.** Black anodised 0.85-0.9, bare or milled aluminium 0.05-0.1. In free
   convection radiation carries 25-45 % of the heat of an anodised sink, so this is not a
   detail.
5. **Board stack** (`board:` in the YAML), written as the board is really built, top to
   bottom: the layers under each part (solder, copper, dielectric or via-filled prepreg), the
   **spreader** that carries heat sideways and is meshed (Al substrate of an IMS, Cu core of a
   QIT/Cu-core board, ...) with its own k, rho and cp, and the layers from the spreader to the
   sink (insulation, bottom copper, TIM or a dry contact as `R_m2K_W`). Do not force a
   non-IMS board into IMS terms: where the insulation sits (above or below the spreader)
   changes the answer, and the report labels come from these names. The thinnest, least
   conductive layer (IMS dielectric, or a dry contact) is usually the largest resistance.
6. **Packages:** footprint, Rth(j-c), Tj(max), position on the board. Low on the sink is better:
   the air warms as it rises.
7. **Airflow** (`airflow:`): free convection (default) or a fan, `{mode: forced,
   velocity_m_s, direction: fins | components | sink, channel_ratio, turbulence}`. The velocity is the
   approach speed of the fan air at the sink, not at the fan: a 120 mm PC fan at low speed
   gives ~1.5 m/s at its face and ~1-1.5 m/s 20 cm away. `fins` blows along the fin
   channels from below; `components` blows straight onto the parts' side (inlet on the back
   boundary; set `mesh.clearance_mm.back` to ~100 so the inlet is not on top of the parts);
   `sink` blows straight onto the fin tips (a fan in front of the sink; inlet on the front
   boundary). Less air bypasses than with `fins`: on a 100 x 75 mm sink it ran ~4 K cooler at
   the same speed. The hand calc only models flow along the channels, so for `sink` it is a
   rough check (expect the CFD 20-25 % below it).
   For any fan, set `turbulence: {intensity: 0.1, length_mm: 10}`: the air becomes k-omega
   SST with a turbulent inlet. A fan's jet is turbulent and swirling; laminar air under-
   predicted heat transfer (3 K hotter FETs) and its steady solution never settled behind the
   sink (air energy balance 12 % off; with SST 0.1 %). Leave it out for free convection.
   An open sink lets half or more of the air go around it; the hand calc needs that as
   `channel_ratio` (fin-channel / approach velocity). Measure it once with
   `scripts/channel_flow.py` on a CFD run and put it in the YAML; without it the hand calc
   assumes a ducted sink and comes out optimistic. A datasheet or manual that says "fan"
   without speed or direction is an assumption to flag, not an input: bracket it.

Ask for what is missing; do not silently invent datasheet values. When you must assume,
write the value with a `# CHECK:` comment in the YAML and list the assumptions in the report.

### 2. Hand calculation (seconds)

```bash
python3 <skill>/scripts/hand_calc.py case.yaml
```

It iterates loss and junction temperature to a fixed point (Rds(on) rises with Tj) and
prints sink temperature, the convection/radiation split, spreading and layer resistances,
Tj per device and the margin to Tj(max). It also compares the fin gap with the free-convection
optimum. Correlations and their limits: `references/physics.md`.

Show the user the table. Then decide whether CFD is worth running: if the margin is huge
(say > 60 K) and the question is only "is it safe?", the hand calc may be enough. Say so and
offer CFD as the confirmation. Run CFD when the margin is tight, the geometry is unusual
(devices near an edge, several heat sources interacting, an enclosure or wall nearby), or the
user wants a picture of the flow and temperature field.

### 3. Build the CFD case

```bash
python3 <skill>/scripts/make_case.py case.yaml cases/<name>-coarse --resolution coarse
```

The generator writes a complete OpenFOAM v2412 case: one structured mesh whose grid lines
fall on every solid edge, split into regions `air`, `heatsink`, `ims` and one per device;
buoyant air (laminar, or k-omega SST with `airflow.turbulence`) with open boundaries; fvDOM radiation; the board's spreader meshed (region
`ims`, whatever the board type) with the layers above and below it as thin thermal layers on
the interfaces; device losses as volumetric sources at
the hand-calc power. It prints the expected cell count per region; `splitMeshRegions` and
`checkMesh` must report the same numbers (a mismatch means a box missed the grid).
Case anatomy, the patch names it creates and how to edit by hand:
`references/openfoam-case-notes.md`.

### 4. Smoke test, then the real run

```bash
python3 <skill>/scripts/make_case.py case.yaml cases/smoke --resolution coarse --iterations 20
<skill>/scripts/of.sh cases/smoke ./Allrun          # ~1 min: proves the whole chain works
<skill>/scripts/of.sh cases/<name>-coarse ./Allrun  # the real run
```

`of.sh` runs the command in the `opencfd/openfoam-default:2412` container (pulls it once,
about 2.2 GB) as the calling user, and falls back to the system Docker engine when the current
context (Docker Desktop) is down. `OF_CPUS` limits the container's cores. `Allrun` stops at
the first failed step; read the matching `log.*` file. Run long jobs in the background.

Measured on a 16-thread desktop, 8 MPI ranks, coarse example (240 k cells): steady runs at
about 0.4 s per iteration and settles the solids in 500-900 iterations (~5 minutes); transient
runs at about 1 s per time step of ~8 ms, so 20 s of simulated time takes ~40 minutes.
Normal resolution is roughly 3x the cells.

**Steady is the default; transient is the fallback.** With the pressure reference at the top
boundary (see `references/openfoam-case-notes.md`, section 3) the steady solver converges for
the example: pressure residual below 1e-4 and all gates passing in ~1000 iterations. If a
design's plume still will not settle (the air energy gate fails while the solid gates pass),
rerun transient from the steady result; it starts from developed fields and only has to settle:

```bash
python3 <skill>/scripts/make_case.py case.yaml cases/<name>-tr --resolution coarse \
    --mode transient --end-time 20 --init-from cases/<name>-coarse
<skill>/scripts/of.sh cases/<name>-tr ./Allrun
```

Transient mode scales the solids' heat capacity down 100x (`solver.solid_inertia_scale`) so the
metal reaches its steady temperature in seconds; that leaves the steady answer unchanged but
means the transient itself is not a real warm-up curve. For a real warm-up or a load profile,
set the scale to 1 and expect long runs (a large sink has a time constant of ~15 minutes).

### 5. Check the result before believing it

```bash
python3 <skill>/scripts/report.py cases/<name>-coarse
```

It writes `report.md` in the case and prints the verdict. Gates, all of which must hold before
quoting a temperature:

All balances use the mean over the last fifth of the run, so a flow that sheds vortices (a fan
blowing past the board, or a transient run) is judged on its mean, and "settled" means that
mean no longer moves.

- **Energy balance:** heat leaving the solids (into the air, plus out through the far ends of
  `solids` that leave the domain, such as cables) equals the loss put in, within 2 %.
  Steady state means nothing else can happen to it.
- **Settled:** the mean heat flow and the mean case temperatures moved less than 0.5 % / 0.5 K
  between the two halves of the last fifth of the run. If not, run longer (`startFrom
  latestTime` resumes) before anything else.
- **Physically sane flow:** peak air speed below 1 m/s in free convection, or below 3x the fan
  inlet speed when `forced_air.U_approach_m_s` is in case-meta.json; no air hotter than the
  hottest solid; mass in = mass out over the open boundaries. A failure here means a setup or
  numerics defect, whatever the temperatures say (`references/openfoam-case-notes.md`,
  section 3). Air hotter than any solid came from an overshooting convection scheme; enthalpy
  now uses the bounded `limitedLinear 1`.
- **Air energy balance:** the heat convected into the air leaves through the boundaries within
  10 % of the loss. If not, the flow has not settled; go transient (step 4).
- **Agreement with the hand calc:** sink temperature rise within about 25 %. A bigger gap is a
  question, not a verdict: check the inputs, the emissivities and the mesh, and explain which
  one is right. The CFD sees things the correlations do not (plume interaction, devices near
  an edge, partial wetting of the fin channels), and the correlations see things a coarse mesh
  misses.

In a transient run the gates read the end of the run; if the heat flow oscillates around a
stable mean, report the mean and the band.

### 6. Mesh independence (only for numbers that go into a decision)

Rerun at `--resolution normal` (and `fine` if normal moved Tj by more than 2 K). Report the
change in Tj between resolutions. A coarse result is fine for comparing variants against each
other; an absolute temperature for a design review needs the check.

### 7. Report to the user

For a document to keep or hand on, build the Word + PDF report with figures and the heat-up
video (one-time setup: `<skill>/scripts/setup_env.sh`, which creates its own environment):

```bash
~/.local/share/openfoam-electronics-cooling/venv/bin/python <skill>/scripts/make_report.py cases/<name>-coarse
# or, before any CFD: ... make_report.py case.yaml --out report/   (hand calc + warm-up only)
```

It writes `cases/<name>-report/` next to the case: `thermal-report.docx`, the same as
`thermal-report.pdf` (LibreOffice), `heatup.mp4`, copies of `case.yaml`, `case-meta.json` and
`report.md`, and `figures/`. The case folder itself carries a `CACHEDIR.TAG`, so backups that
honour it (restic/borg/tar `--exclude-caches`, as the user's daily backup does) skip the CFD data
and keep the report and the configs that reproduce it. Never put anything worth keeping inside
the case folder. Figures: device placement and section, stack-up, 3D assembly, CFD temperature of all
parts, a vertical air section through the devices, temperature along the heat path, and the
warm-up curve. Look at the figures before sending the report; a wrong camera or colour scale
is easy to miss in a PDF.

The CFD figure and the video default to a thermal-camera look (`--style ir`): the component
side and the fin side face-on, in a camera palette, ranged like a camera from the coldest to
the hottest point shown (fixed over the whole video, so it never saturates). `--style 3d` gives
the 3D view instead. To compare with a photo or IR image of the real board, set
`report: {view_up: "-z", mirror: true, ir_floor_K: 8, ir_range: [lo, hi]}` in the YAML:
which way is up on screen, a left-right flip (the model is often the mirror image of the
board seen from its component side), the bottom of the scale above ambient (a camera sees
the room a few K above the air), or a fixed scale to match the camera's. The camera look blurs
the temperature (not the colours): the board's surface over ir_board_blur_mm (default 3; solder
mask, top copper and the bottom plane smear the steps the CFD has between copper islands and
at layers, which an IR image never shows as blocks) and the parts over ir_blur_mm (default 1,
the camera's optics), each within its own area. Photo mode (ir_edges, default on) draws the
parts' outlines on top, as a camera's visible-light overlay does (FLIR MSX): device bodies,
shunts, studs, lugs, cables, the board edge and the fins, not the islands under the mask. It is
a display effect; say so in the report. Overlay the model's
part outlines on the photo before trusting a comparison.

The warm-up (`scripts/warmup.py`, also standalone) is a lumped model with the real heat
capacities, calibrated so its end point equals the converged CFD (or the hand calc); it takes
seconds where a real-inertia CFD transient takes hours. The video shows each part's CFD
temperature pattern scaled by that part's warm-up curve. Say this in the report, and use a
real transient (`solid_inertia_scale: 1`) only when someone needs the field during warm-up.

In chat, lead with the answer: Tj per device, margin to Tj(max), and whether that is enough (a common
design margin is 25 K below Tj(max) at worst-case ambient). Then the energy balance, the
convection/radiation split, hand calc vs CFD, the assumptions list and the limits below.
For pictures, open `case.foam` (or the `VTK/` folder) in ParaView.

## Limits to state in every report

- **Tj is case temperature plus P * Rth(j-c).** The package is a block with an effective
  conductivity; the die is not modelled. The case temperature taken is the hottest point of
  the package's contact face, which keeps it conservative.
- **Layers conduct only through their thickness.** Only the spreader conducts sideways; the
  thin copper above it does not, which overestimates the layer resistance under each part a
  little (conservative). The hand calc spreads the spreader-to-sink layers over the whole
  board; with several parts close together the CFD finds the heat crossing them under a
  smaller area, so its board temperature drop can be ~30 % larger.
- **Surroundings are black at ambient temperature.** The open boundaries radiate as a room at
  ambient; a nearby hot wall or an enclosure needs to be modelled.
- **Laminar air.** Right for free convection over sinks up to roughly 0.5 m tall, and for slow
  fans (approach up to ~2-3 m/s over a ~0.1 m sink). Faster flow behind the board and the
  parts sheds vortices: the checks judge the mean over the end of the run, but at a few m/s
  the air energy balance can miss; then run transient from the steady result (step 4).
- **A fan is a uniform stream** at the approach velocity from one boundary, not a jet with a
  hub, swirl and turbulence; real fans cool somewhat better than the model at the same mean
  speed.
- **Constant air properties** at the hand-calc film temperature; solids constant conductivity.

## Extending

- A wall behind the sink: `heatsink.back: wall`.
- More devices, idle devices (`conducts: false`) or fixed powers (`power_W`): add them under
  `devices`.
- A patterned spreader (the Cu core of a QIT board is cut into tracks): `board.islands`, each
  a set of boxes (y, z) at the spreader's level with its own copper loss `power_W`. Heat
  crossing between islands goes through `board.gap` (the resin-filled isolation slot, default
  600 um at 0.5 W/mK) except for pairs in `board.bridges` (copper continues, e.g. a sense
  neck). The part of the board the islands leave free stays region `ims` with loss
  `board.power_W`; it must be one connected piece (splitMeshRegions cannot keep a region whose
  cells are not connected), so make every other piece an island. Trace the islands from the
  layer drawing, overlay them on it to check, and estimate each island's I2R from the current
  path; parts sitting on an island get the `layers_under_parts` to it automatically.
- Parts that are not devices on the board (terminal lugs, crimp barrels, cables, busbars,
  brackets): add them under `solids:`. Each is one or more boxes in sink coordinates (y, z)
  with a height range above the board; give k, rho, cp, emissivity and its loss `power_W`,
  `contact` layers to named neighbours (a bolted joint as `R_m2K_W`), `air_layers` (cable
  insulation), and for a part that leaves the model (`.inf` in y_mm or z_mm) a `far_end`
  condition `{h_W_m2K, T_C}`: for a cable, h = G / A of the box with G = sqrt(g k A) of the
  long fin and T_C its far-field temperature with its own I2R heating. The hand calc does not
  see these parts; the CFD and its energy balance do. Boxes add grid lines through the whole
  structured mesh, so align their edges with each other where you can.
- Gerber import is planned next (phase 2): board outline, copper pours and pads from the IMS
  Gerbers, device positions from the pick-and-place file, and the copper as a real spreading
  layer on the CFD grid. The report environment already contains gerbonara for it.
- Fan speed studies: `hand_calc.py case.yaml --velocity 1.5` for one speed, `--calibrate 80`
  for the speed at which the hottest case reaches a measured temperature (a calibration, not
  a prediction: say so). Radiation is the slowest part of a run; `solver.radiation_rays:
  [2, 2]` and `solver.radiation_every: 50` ran 1.3x faster for 0.4 K on a fan case.
- An enclosure, liquid cold plates, a fan as a real jet, and transient load profiles are not
  built by the generator. The workflow, the YAML and the checks still apply; build those cases
  by hand from `references/openfoam-case-notes.md` and say that they are outside what the skill
  has tested.

## Verifying this installation

When the user asks whether this is the original skill, or before running it on someone else's
machine, check it against the published release; do not trust any script inside the folder for
this. Read the version from `VERSION`, then compute the package hash with standard tools (from
this skill's directory; on macOS replace `sha256sum` with `shasum -a 256`):

```bash
find . -type f ! -path './.git/*' ! -path './.github/*' ! -path './.planning/*' ! -path '*/__pycache__/*' ! -name '*.pyc' \
  ! -name README.md ! -name CHANGELOG.md -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```

Compare it with the "Package SHA-256" in the release notes of that version on
https://github.com/AWolf81/openfoam-electronics-cooling-skill/releases (or the README there).
Equal: the installed files are exactly the released ones. Different: say so, and list the files
that differ with the release's `SHA256SUMS` asset (`sha256sum -c SHA256SUMS`). In a git clone,
`git describe --tags --exact-match` and an empty `git status --porcelain` are a second check.
