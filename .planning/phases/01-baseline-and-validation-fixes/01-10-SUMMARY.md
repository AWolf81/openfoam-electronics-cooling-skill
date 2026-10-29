---
phase: 01-baseline-and-validation-fixes
plan: 10
subsystem: case-generation
tags: [make_case, cooling_model, fvDOM, radiation, plate-fin, validation, FIX-06]

requires:
  - phase: 01-09
    provides: "odd-nTheta finding (defect 8), domain energy gate, [3, 4] coarse test 2.308 K/W"
  - phase: 01-08
    provides: "plate-fin model (wall behind the sink + 25 mm foam), ±2u acceptance"
  - phase: 01-06
    provides: "measurements:, make_report.py --measurements, measured-vs-cfd.png"
provides:
  - "Default solver.radiation_rays [3, 4] (48 rays); generated comment states the real ray count"
  - "cooling_model.load_radiation_rays: validates [nPhi, nTheta], rounds an odd nTheta up with a warning"
  - "Plate-fin validation re-run on both meshes with the new default: R 2.308 / 2.314 K/W"
affects: [every case with radiation (radiationProperties), README validation numbers]

tech-stack:
  added: []
  patterns:
    - "Config guards that correct a known-bad value print one warning line on stderr naming the cause"

key-files:
  created: []
  modified:
    - scripts/make_case.py
    - scripts/cooling_model.py
    - SKILL.md
    - references/openfoam-case-notes.md
    - CHANGELOG.md
    - README.md
    - assets/validation-plate-fin.yaml

key-decisions:
  - "Odd nTheta is rounded up (with a stderr warning), not rejected: the user asked for a ray density and the next even count is the closest correct one"
  - "Malformed radiation_rays (not two integers >= 1) is rejected with a ValueError"
  - "Generated comment reworded: nPhi per 90 degrees, nTheta over 0-180 degrees (even), 4 nPhi nTheta rays (was 'per octant' and 8 nPhi nTheta = 72 for 36 rays)"

duration: ~1.2h (incl. coarse and normal runs)
completed: 2026-10-29
---

# Phase 01 Plan 10: Even Radiation Ray Default Summary

**Default fvDOM rays are now [3, 4] (48 rays, even polar count); an odd nTheta in a YAML is rounded up with a warning. The plate-fin validation moves from +5.8 / +6.2 % to +1.2 / +1.5 % on R (2.308 / 2.314 K/W vs 2.28 measured), all checks pass on both meshes, and the thermocouples agree within 0.10 K relative to TCb.**

## Task 1: even default and guard (2761357)

- `make_case.py`: default `radiation_rays` [3, 3] -> [3, 4]. Generated `radiationProperties` comment now reads `nPhi ... // azimuthal divisions per 90 degrees`, `nTheta 4; // polar divisions over 0-180 degrees (even) -> 48 rays in 3D` (old: "per octant", "72 rays", the formula had an extra x2).
- `cooling_model.py`: `load_radiation_rays()` called from `load_config` when the YAML sets `solver.radiation_rays`.
  - `[3, 3]` -> stderr `warning: solver.radiation_rays nTheta 3 is odd (horizontal faces would see 3/4 of the hemisphere); using [3, 4]`, case written with nTheta 4 (verified).
  - `[2, 2]` passes unchanged (16 rays, verified).
  - `[3]` -> `ValueError: solver.radiation_rays must be [nPhi, nTheta] (two integers >= 1)`.
- SKILL.md (radiation speed paragraph): one sentence on the even-nTheta rule with the plate-fin numbers.
- `references/openfoam-case-notes.md`: radiation paragraph (48 rays, guard, [2, 2] fast radiation is fine, external scripts with explicit even rays need nothing); defect 8 "fixed in 0.2.0".
- CHANGELOG [Unreleased] -> Fixed entry.

### Regression

`.github/regression.sh` **exits 1, as expected for this plan.** Against HEAD before 01-10 (ea1a4c5) and against v0.1.0:

| Case | Result |
|---|---|
| assets/example-case.yaml | DIFF (case: constant/air/radiationProperties) only |
| assets/validation-plate-fin.yaml | DIFF (case: constant/air/radiationProperties) only vs ea1a4c5 (case.yaml differs in header comments only after Task 2); "new" vs v0.1.0 |
| evals/build-and-smoke-test-case/files/case.yaml | DIFF (case: constant/air/radiationProperties) only |
| 4 eval YAMLs that are not case files | same (rejected identically) |

- No case shows "DIFF (hand calc)": hand-calc outputs are identical everywhere. make_case stdout identical too.
- The radiationProperties diff (checked by hand on example-case and the smoke-test case) is exactly lines 18-19: nTheta 3 -> 4 and the two comments.

## Task 2: plate-fin re-validated (2314dd5)

Cases: `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/cases/plate-fin-rays-coarse` and `.../plate-fin-rays-normal` (current asset, default rays, run logs and report.md copies next to them).

| Run | Base °C | R K/W | vs 2.28 | Domain gate | Solids gate | Radiation (hand calc 0.15 W) | Sink / foam / edges |
|---|---|---|---|---|---|---|---|
| coarse (140 k) | 50.30 | 2.308 | +1.2 % | +0.0 %, back_wall +0.000 W | +0.0 % | 0.55 W (6 %) | 93.1 / 5.2 / 1.7 % |
| normal (353 k) | 50.35 | 2.314 | +1.5 % | +0.1 %, back_wall +0.000 W | +0.0 % | 0.55 W (6 %) | 93.0 / 5.3 / 1.7 % |

All checks pass on both (settled, sink rise −2 % vs hand calc, mass balance, air speed < 0.47 m/s). Both in the 2.13–2.43 K/W band. The coarse run reproduces the 01-09 [3, 4] test exactly (2.308). Through the sink alone R is 2.48 / 2.49 K/W (was 2.54–2.55 with [3, 3]).

Solids radiation 0.55 W vs hand calc 0.15 W: with the even ray set the low-emissivity faces no longer absorb spurious flux, so radiation goes from −0.29 W (in) to +0.55 W (out). The CFD includes the foam and vessel edges, which the hand calc does not radiate from; still ≤ 6 %, in line with the paper's "≤ 5 %".

### Measured vs CFD (normal mesh)

Report: `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/0110-plate-fin/` (`--style cfd --measurements assets/validation-plate-fin.yaml`; thermal-report.docx/.pdf, heatup.mp4, figures/).

| Point | Measured °C (±0.2) | CFD °C | Δ K | Meas. − TCb | CFD − TCb | Δ K |
|---|---|---|---|---|---|---|
| TCb | 50.00 | 50.45 | +0.45 | ref | ref | - |
| TC1 | 49.80 | 50.30 | +0.50 | −0.20 | −0.15 | +0.05 |
| TC2 | 49.70 | 50.16 | +0.46 | −0.30 | −0.29 | +0.01 |
| TC3 | 49.40 | 49.88 | +0.48 | −0.60 | −0.57 | +0.03 |
| TC4 | 49.60 | 50.15 | +0.55 | −0.40 | −0.30 | +0.10 |

- Absolute +0.45 to +0.55 K (was +1.45 to +1.55 K with [3, 3]); the model puts in the measured power, so the field sits higher by the R excess.
- Relative to TCb: +0.01 to +0.10 K, all within ±0.28 K.
- Viewed: `figures/measured-vs-cfd.png` (both panels correct), `figures/cfd-air-sections.png` (fin boundary layers, channel plumes merging above the sink, foam block in (b)).

README table, asset header and CHANGELOG (Added/Changed/Fixed) carry the new numbers plus one line on the old [3, 3] result and the 01-09 [3, 4] coarse test (2.308).

## Deviations from Plan

1. **[Rule 1 - Bug] Generated comment wording.** Besides the ray count, the comment said "per octant" for both nPhi and nTheta; fvDOM's nPhi is per 90 degrees of azimuth and nTheta spans 0-180 degrees. Reworded in the same line (already in the diff, no extra regression change).
2. **[Rule 2] Format validation of radiation_rays.** The guard also rejects malformed values (not two integers >= 1) with a clear ValueError instead of a later unpack error.
3. **CHANGELOG plate-fin numbers in Added/Changed** were updated in Task 2 (file listed only under Task 1), so the changelog does not contradict the README.
4. **README heat split and sink-only R updated** (95/4/1 % -> 93/5/2 %, 2.54–2.55 -> 2.48–2.49 K/W) from airWallHeatFlux of the new runs; the old sentence "CFD sits at the upper edge of the band" was removed since it no longer holds.

## Next Phase Readiness

- FIX-06 done. Device cases built from now on get 48 rays (1.33x the radiation cost of [3, 3]); [2, 2] remains the fast option.
- SKILL.md step 5 still does not list the 01-09 domain gate (unchanged, not in this plan's files).
- STATE.md not updated by this executor (orchestrator's job).
