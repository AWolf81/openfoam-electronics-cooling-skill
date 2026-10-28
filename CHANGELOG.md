# Changelog

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each release lists its **package SHA-256** (see "Verify your installation" in the README).

## [Unreleased]

### Added

- Validation case `assets/validation-plate-fin.yaml`: a plate-fin heat sink in free convection
  against the measurement in Kirinčić et al., Thermo 2025 (CC BY 4.0). Hand calc +3 %, CFD on the
  normal mesh 0 % on the thermal resistance; results table in the README.
- Cases without devices: `board.power_W` (or island power) can be the only heat source, for bare
  heat-sink benchmarks and datasheet R_sa checks. The hand calc and `report.py` then give the
  base and board temperature instead of junction temperatures. The plate-fin validation uses
  this instead of a "heater" device (coarse CFD: base 49.4 °C, 2.21 K/W, −3 % vs measured).
- `heatsink.back: {wall: footprint}` and `{wall: {y_mm: [a, b], z_mm: [c, d]}}`: an adiabatic wall
  only behind the sink (or over that rectangle), open air on the rest of the back boundary (patch
  `back_wall`, split off `back` with topoSet + createPatch). For a heater, vessel or housing no
  larger than the sink; `wall` (whole back boundary) stays for a mounting plate or enclosure wall.
  `free` and `wall` cases are unchanged byte for byte.
- GSD planning in `.planning/` (project, requirements, roadmap for 0.2.0, the v0.2 PRD). It is
  not part of the skill package and is left out of the package hash.

### Changed

- The package hash also leaves out `.planning/` (README, SKILL.md, `.github/package-hash.sh`).
- SKILL.md intake: emissivity is set per part (`heatsink`, `board`, `devices[]`, `solids[]`);
  metal or foil-covered heat sources need 0.03-0.1 instead of the 0.9 default.
- SKILL.md checks: a low-power free-convection run that just misses "Heat flow settled" is rerun
  with `solver.iterations: 3000` before the result is judged.

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
