# Changelog

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each release lists its **package SHA-256** (see "Verify your installation" in the README).

## [Unreleased]

## [0.1.0] - 2026-10-28

First release.

Package SHA-256: `<!-- package-sha256 -->`

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
