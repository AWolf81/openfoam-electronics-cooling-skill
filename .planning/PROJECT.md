# openfoam-electronics-cooling

## What This Is

A Claude Code skill that turns a plain-language description of a power stage on a heat sink
(MOSFETs, IGBTs, diodes or regulators on an IMS, Cu-core or PCB board, finned aluminium sink,
free convection or a fan) into junction temperatures an engineer can trust. It does the losses, a
hand calculation as the yardstick, a checked OpenFOAM conjugate-heat-transfer run and a report.
For power-electronics and hardware engineers who need a thermal answer without a CFD specialist.

## Core Value

Junction temperatures you can trust: every CFD result is checked against a hand calculation and
energy balances, and the report says what was assumed.

## Requirements

### Validated

- ✓ YAML case, losses with Rds(on) at temperature, back-to-back MOSFETs — v0.1.0
- ✓ Hand calculation: free convection + radiation, forced air with bypass ratio — v0.1.0
- ✓ OpenFOAM v2412 CHT case generator, steady and transient, fvDOM radiation — v0.1.0
- ✓ Board stack as built (layers, meshed spreader, Cu-core islands with losses) — v0.1.0
- ✓ Fan directions fins / components / sink, optional k-ω SST — v0.1.0
- ✓ Checks: solid and air energy balance, mass balance, settled, hand calc vs CFD — v0.1.0
- ✓ Word/PDF report, IR-style figures and warm-up video, lumped warm-up incl. lugs and cables — v0.1.0
- ✓ Release with package SHA-256, security scan, release automation — v0.1.0
- ✓ Validation against a published measurement (plate-fin heat sink, Kirinčić et al. 2025):
  hand calc +3 %, CFD normal mesh 0 % on R — develop (2026-10-28)

### Active

Milestone v0.2.0, from `prd-v0.2-guide-gaps.md` (P0 items) plus fixes found in the validation:

- [ ] Correct results away from sea level (altitude / ambient pressure) — PRD R1
- [ ] CFD losses consistent with CFD temperatures (closed Rds(on)–Tj loop) — PRD R2
- [ ] Additional limits (e.g. touch temperature) and worst-case corner sweep — PRD R3
- [ ] Heat sinks without devices, per-device emissivity guidance, iteration advice — validation findings
- [ ] Regression harness: default cases unchanged against v0.1.0, all evals pass

### Out of Scope

- Fan curves / `fanPressure` boundaries — only matter with a duct or shroud; revisit with enclosures
- Lifetime prediction (solder fatigue, power cycling) as a verdict — at most a labelled estimate later
- "Failure rate doubles per 10 K" statements — rule of thumb, not to be stated as fact
- Full-detail CAD import without simplification — the skill keeps simplify-then-check

## Context

- v0.1.0 released 2026-10-28 (package SHA-256 `9eff3e2f…`), tested end to end from a fresh clone.
- Main validation so far: Infineon R 48V BATT SWITCH10 at 300 A (6 K hot at an assumed 2.4 m/s
  fan; the guide gives no fan speed) and the Kirinčić plate-fin experiment (exact on the normal mesh).
- The v0.2 PRD comes from reviewing the Cadence ebook "Engineer's Guide to Simulating Electronics
  Cooling" (02/2026) against the skill.
- Known issues: warm-up about 2× faster than the Infineon measurement (5 vs 9 min); the lumped
  warm-up model ends about 1.5 K below the CFD it is calibrated to.
- Work happens on `develop`; `main` carries releases only.

## Constraints

- **Tech stack**: OpenFOAM v2412 in Docker (`opencfd/openfoam-default:2412`), Python 3 with uv —
  the skill must run on a desktop without a local OpenFOAM install.
- **Compatibility**: every new YAML key has a default that keeps v0.1.0 results unchanged.
- **Packaging**: `.planning/`, `.github/`, README and CHANGELOG stay out of the package hash.
- **Performance**: hand calc and sweeps in seconds; coarse CFD in about 10 minutes on 8 cores.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hand calc before CFD, always | It is the yardstick that tells whether the CFD is right | ✓ Good |
| Checks gate every report | A CFD number without energy balance is not trustworthy | ✓ Good |
| k-ω SST opt-in, laminar default | SST fixed fan cases; free convection stays laminar | ✓ Good |
| Package hash excludes docs, CI and planning | Hash must describe only what the skill runs | ✓ Good |
| Develop branch; release from main | Try changes locally before a release | — Pending |

---
*Last updated: 2026-10-28 after GSD planning set up from the v0.2 PRD*
