# Changelog

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each release lists its **package SHA-256** (see "Verify your installation" in the README).

## [Unreleased]

### Added

- Validation case `assets/validation-plate-fin.yaml`: a plate-fin heat sink in free convection
  against the measurement in Kirinčić et al., Thermo 2025 (CC BY 4.0). Hand calc +3 %, CFD
  +1.2 % (coarse) / +1.5 % (normal) on the thermal resistance, inside the measurement's ±2u
  band; results table in the README.
- Cases without devices: `board.power_W` (or island power) can be the only heat source, for bare
  heat-sink benchmarks and datasheet R_sa checks. The hand calc and `report.py` then give the
  base and board temperature instead of junction temperatures. The plate-fin validation uses
  this instead of a "heater" device.
- `heatsink.back: {wall: footprint}` and `{wall: {y_mm: [a, b], z_mm: [c, d]}}`: an adiabatic wall
  only behind the sink (or over that rectangle), open air on the rest of the back boundary (patch
  `back_wall`, split off `back` with topoSet + createPatch). For a heater, vessel or housing no
  larger than the sink; `wall` (whole back boundary) stays for a mounting plate or enclosure wall.
  `free` and `wall` cases are unchanged byte for byte.
- Report figures like those of CFD papers (Kirinčić et al. 2025, Figs. 10-13): air temperature
  sections at mid fin height and vertically through a fin channel, with flow arrows
  (`cfd-air-sections.png`); velocity vectors coloured by speed at mid fin height
  (`cfd-velocity.png`); the heat sink alone on its own colour scale (`cfd-sink-local.png`).
- Measured vs simulated: optional `measurements:` in the YAML (points or a part's max/mean, with
  uncertainty and one optional reference point); the report plots and tabulates them, absolute
  and relative to the reference (`measured-vs-cfd.png`). `make_report.py --measurements <yaml>`
  takes them from another file for a case run before they were added.
- Report structure (`references/report-structure.md`): 1 Result (page 1: verdict table and one
  key figure), 2 Inputs and assumptions, 3 Results, 4 Comparison with measurement, 5 Time
  behaviour, 6 Checks, each figure only when its condition holds. New: `report.camera_image`
  (thermal camera image in section 4), `report.warmup: false` (steady answer only) and
  `make_report.py --mesh-compare <case>` (mesh comparison under Checks).
- GSD planning in `.planning/` (project, requirements, roadmap for 0.2.0, the v0.2 PRD). It is
  not part of the skill package and is left out of the package hash.

### Changed

- Plate-fin validation (`assets/validation-plate-fin.yaml`): wall only behind the sink, 25 mm
  vessel foam, open back boundary 30 mm behind the base (as in the paper's domain); acceptance
  is the measurement's ±2u (±6.6 %). CFD coarse 2.31 K/W (+1.2 %), normal 2.31 K/W (+1.5 %; 2.41 /
  2.42 K/W with the old odd ray default, see Fixed). The
  earlier whole-wall result (−2 … −3 %) was flattered by 12–14 % of the heat leaking through the
  vessel wall's back face into an air gap that is insulated in reality.
- CFD figures and the video use Turbo by default (`report.style: cfd`; `3d` is accepted as the
  old name): smooth point-interpolated fields in 256 levels, legend on the left, still figures
  rendered at 2.5x and saved at 200 dpi. The thermal-camera palette is now `report.style: ir`,
  for comparisons with a camera image (its figures unchanged). In the cfd style the air
  sections replace `cfd-plume.png`.
- Report sections reordered to the structure above: setup and limits sit next to the inputs,
  the comparison with measurement has its own section, and the checks come last.
- `hand_calc.py` without devices no longer prints the base temperature and R_sink-air twice.
- The package hash also leaves out `.planning/` (README, SKILL.md, `.github/package-hash.sh`).
- SKILL.md intake: emissivity is set per part (`heatsink`, `board`, `devices[]`, `solids[]`);
  metal or foil-covered heat sources need 0.03-0.1 instead of the 0.9 default.
- SKILL.md checks: a low-power free-convection run that just misses "Heat flow settled" is rerun
  with `solver.iterations: 3000` before the result is judged.

### Fixed

- Default radiation rays had an odd polar count (`solver.radiation_rays: [3, 3]`): fvDOM's middle
  polar band straddled the horizontal plane, so faces facing straight up or down saw 3/4 of the
  hemisphere and low-emissivity horizontal faces absorbed radiation that does not exist (about
  80 W/m2; every balance still closed). Default now [3, 4] (48 rays); an odd nTheta in a YAML is
  rounded up with a warning. Plate-fin R +5.8 / +6.2 % -> +1.2 / +1.5 % (coarse / normal). Every case with radiation gets a
  new `radiationProperties`; the comment in it now states the real ray count (4 nPhi nTheta;
  it said 72 for the 36 rays of [3, 3]). `[2, 2]` (fast radiation) was already even.
- An adiabatic wall on the domain boundary (`heatsink.back: wall`, and the `back_wall` patch of
  a partial wall) radiated as a black body at the temperature of the air next to it: in the
  plate-fin case with the whole back wall it put 2.8 W (coarse) / 3.1 W (normal) into a case
  with 9.22 W heat input. It is now a perfect reflector (emissivity 0, zero net flux); R of that
  case 2.214 -> 2.206 K/W. The current plate-fin asset (wall behind the sink only, 0.03 W) is
  unchanged (2.413 K/W). Cases with `back: free` are unchanged byte for byte.
- `report.py`: for cases with a boundary wall, a domain energy balance (heat in = convection +
  radiation out through the open boundaries; the wall must carry nothing), from new
  `radFlow_<patch>` function objects. The old whole-wall run fails it (+31 %), the fixed run
  passes (+0.1 %).

## [0.1.0] - 2026-10-28

First release.

Package SHA-256: `9eff3e2fa99f50819d11e9b57a82c7854805a9d609cefd282b2e44b106a1ad24`

### Added

- Workflow in `SKILL.md`: intake with every assumption marked `# CHECK:`, hand calculation first
  as the yardstick, then CFD only when it is needed, checks, report.
- One YAML file per design (`assets/example-case.yaml`): heat sink, board stack, devices, extra
  solids (terminals, lugs, cables), airflow, mesh and solver settings.
- Losses: I² · Rds(on) at the junction temperature, back-to-back MOSFETs, optional switching loss.
- Board stack `board:` written as the board is built: layers under the parts, a meshed spreader
  (Al of an IMS, Cu core of a QIT board, ...), layers and dry contacts down to the sink. Optional
  `islands:` for a structured copper core, with their own I²R losses.
- Hand calculation (`hand_calc.py`, `cooling_model.py`): thermal network with free convection and
  radiation, or forced air through the fin channels with a measured bypass ratio.
- OpenFOAM v2412 case generator (`make_case.py`): one structured mesh whose grid lines fall on
  every solid edge, one region per part, conjugate heat transfer (`chtMultiRegionSimpleFoam`, or
  `chtMultiRegionFoam` for transients), fvDOM surface radiation.
- Fan cooling: inlet along the fins, onto the component side or onto the fin tips
  (`airflow.direction: fins | components | sink`).
- Optional k-ω SST air with a turbulent fan inlet (`airflow.turbulence`).
- Cables leaving the model as long fins with their own I²R heating (`far_end`).
- Checks in `report.py`: energy balance of the solids and of the air, mass balance, settled
  temperatures and heat flow, hand calc against CFD, cell counts per region.
- Report (`make_report.py`): Word and PDF with junction temperatures and margins, layout,
  stack-up, 3D assembly, CFD figures in an IR-camera palette and a warm-up video.
- Warm-up from cold (`warmup.py`): lumped model calibrated to the CFD, with the heat capacity of
  the sink, the board, each part, the lugs and the cables leaving the model.
- Fin-channel velocity from a CFD run (`channel_flow.py`) for the hand calc's bypass ratio.
- `of.sh`: runs OpenFOAM in Docker; falls back to the system engine when Docker Desktop is down or
  cannot mount the case directory.
- `setup_env.sh`: Python environment for reports and renders.
- Evals for the hand calc, a fan-cooled case, a vague request and a build-and-smoke-test run.
- `VERSION` file and installation check (package SHA-256) in `SKILL.md` and the README.

### Known issues

- The warm-up of the Infineon 48 V battery switch reaches 90 % of its rise after about 5 min;
  the measurement takes about 9 min.
- The lumped warm-up model ends about 1.5 K below the CFD it is calibrated to.
- The "temperatures settled" check fails on some fan cases (impinging flow, normal mesh) after
  1500 iterations; raise `solver.iterations`.

[Unreleased]: https://github.com/AWolf81/openfoam-electronics-cooling-skill/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AWolf81/openfoam-electronics-cooling-skill/releases/tag/v0.1.0
