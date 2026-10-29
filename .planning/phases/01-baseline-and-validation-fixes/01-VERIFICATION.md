---
phase: 01-baseline-and-validation-fixes
verified: 2026-10-29T23:45:00Z
status: passed
score: 29/29 must-have truths verified (1 partial, accepted by the user: per-channel plumes, 01-08)
re_verification: false
accepted_deviations:
  - "01-03/01-08: acceptance band ±2u = ±6.6 % (R 2.13-2.43 K/W) instead of ±3 % (user decision); results 2.308 / 2.314 K/W vs 2.28 measured are also inside ±3 %"
  - "01-08: per-channel plumes only as short streaks merging 10-20 mm above the sink (user accepted)"
  - "01-10: regression.sh vs v0.1.0 exits 1 by design (radiationProperties only); vs 97c24e7 only the zero-device hand-calc wording differs"
  - "01-06: cfd style uses cfd-air-sections.png (section b) instead of cfd-plume.png"
  - "01-07: Time behaviour is on by default (report.warmup: false removes it), not 'only when asked' as the plan truth says; documented in references/report-structure.md and 01-07-SUMMARY"
non_blocking_findings:
  - "references/report-structure.md:70 cites 'Kirinčić, M., Trp, A., Lenić, K. (2025)'; the paper's authors are Mateo Kirinčić, Tin Fadiga and Boris Delač (as README.md and the asset YAML say)"
  - "assets/validation-plate-fin.yaml measurements comment still says 'its temperatures run ~1.4 K high (R +6 %)' from the odd-ray era; now about +0.3-0.4 K (R +1.2/+1.5 %)"
---

# Phase 1: Baseline, validation fixes and report - Verification Report

**Phase Goal:** A regression check that proves later phases leave v0.1.0 results unchanged, the fixes from the plate-fin validation, and reports whose figures and structure match good validation practice (Kirinčić et al. 2025 figure types, Turbo colour map, answer first).
**Verified:** 2026-10-29
**Status:** passed
**Re-verification:** No - initial verification

Checked against code and generated output, not SUMMARY claims. Commands run: `.github/regression.sh 97c24e7`, `.github/regression.sh` (v0.1.0), `hand_calc.py` on the plate-fin asset, `make_case.py --resolution coarse` into /tmp/verify-01 (asset, an odd-nTheta variant, a rectangle back wall and `back: wall`). Rendered evidence read under `validation/rijeka-plate-fin/` (cases/plate-fin-rays-*.report.md, figure-style-check/0107-* docx headings and figures).

## Goal Achievement

### Observable Truths

| # | Plan | Truth | Status | Evidence |
|---|---|---|---|---|
| 1 | 01-01 | One command compares working tree vs v0.1.0 for every case YAML | VERIFIED | `.github/regression.sh` (111 lines) iterates `find assets evals -name '*.yaml'`, runs hand_calc.py and make_case.py in a baseline worktree and the working tree, diffs output and case trees |
| 2 | 01-01 | Zero differences with no simulation-code change | VERIFIED (by accepted deviation) | vs 97c24e7: example-case and all evals `same`; only the zero-device hand-calc wording of validation-plate-fin differs (01-07 cosmetic fix). vs v0.1.0 hand calc unchanged; only radiationProperties differ (FIX-06 by design) |
| 3 | 01-01 | Deliberate change -> non-zero exit naming case and file | VERIFIED | Live: exit 1 with `DIFF (case: constant/air/radiationProperties)` and `DIFF (hand calc)` with unified diff |
| 4 | 01-02 | Agent sets low emissivity for metal/foil sources | VERIFIED | SKILL.md:45-52 names heatsink/board/devices[]/solids[].emissivity, 0.9 default for mould compound, 0.03-0.1 for metal/foil, plate-fin example; example-case.yaml:49 commented device line |
| 5 | 01-02 | Agent raises iterations (~3000) when "heat flow settled" just fails | VERIFIED | SKILL.md:180-184 |
| 6 | 01-03 | Zero-device YAML with board.power_W runs through the tools | VERIFIED | cooling_model.py:213-216 allows it; hand_calc exit 0 with board/base output; make_case puts 9.22 W in `ims` (make_case.py:481); report.py has a no-device result table; plate-fin CFD reports exist |
| 7 | 01-03 | Plate-fin via board.power_W within band, all checks pass | VERIFIED | Asset has `power_W: 9.22`, no devices. plate-fin-rays-coarse 2.308, -normal 2.314 K/W, all 9 gates pass on both |
| 8 | 01-03 | Device cases unchanged vs v0.1.0 | VERIFIED | Hand calc identical vs v0.1.0; case files differ only in radiationProperties (FIX-06, intended) |
| 9 | 01-04 | make_report.py works without devices | VERIFIED | 0107-plate-fin report (docx/pdf, figures, warmup.csv, heatup.mp4) for the zero-device case; warmup.simulate called at make_report.py:1547 |
| 10 | 01-04 | Device-case reports unchanged in content | VERIFIED | 0107-infineon-cfd/-ir reports built with device tables and warm-up |
| 11 | 01-05 | Turbo, smooth fields, "Temperature [°C]" legend | VERIFIED | `cfd_cmap()` uses `turbo` resampled to cfd_levels (256 default); `cfd_colorbar` label "Temperature [°C]"; figures confirm |
| 12 | 01-05 | style cfd default, ir still available | VERIFIED | 0107-infineon-ir uses IR palette and cfd-plume.png; cfd reports use Turbo |
| 13 | 01-05 | Read like Kirinčić Figs. 10-12, smoother | VERIFIED (human, done) | User checkpoint in 01-05 (Task 2 human-verify, feedback applied in 340f104); figures inspected: smooth Turbo fields |
| 14 | 01-06 | Two air section planes | VERIFIED | fig_air_sections; cfd-air-sections.png: (a) mid fin height, (b) vertical through a channel with plume |
| 15 | 01-06 | Velocity vectors at mid fin height | VERIFIED | fig_velocity, cfd-velocity.png in reports |
| 16 | 01-06 | Local-scale 3D sink view | VERIFIED | fig_sink_local; cfd-sink-local.png "local scale 49.86 to 50.45 °C" |
| 17 | 01-06 | Measured vs simulated with error bars and deviations | VERIFIED | load_measurements, sample_measurements (pyvista sample), fig_measured_vs_cfd; asset has TCb, TC1-TC4; figure shows absolute and relative-to-TCb panels plus table |
| 18 | 01-07 | Six-section structure | VERIFIED | build_docx order Result / Inputs and assumptions / Results / Comparison with measurement / Time behaviour / Checks; docx headings of 0107-plate-fin match exactly |
| 19 | 01-07 | Figures only when condition holds | VERIFIED (deviation noted) | No comparison section without measurements/camera (0107-infineon-cfd); hand-calc report with camera_image and warmup:false omits Time behaviour; Time behaviour default-on is documented |
| 20 | 01-07 | Page 1 answers: verdict table + one key figure | VERIFIED | Section 1 has verdict table and cfd-solids (or temperature path without CFD), sized to fit |
| 21 | 01-08 | Wall only behind the sink or a rectangle | VERIFIED | load_back accepts free/wall/{wall: footprint}/{wall: {y_mm, z_mm}}; generated topoSetDict backWallFaces box 0-123 x 0-100 mm (footprint) and 20-100 x 10-90 mm (rectangle); createPatch back_wall; U noSlip, T zeroGradient on back_wall |
| 22 | 01-08 | back: wall / free cases unchanged vs v0.1.0 | VERIFIED | example-case (free) differs only in radiationProperties (FIX-06) |
| 23 | 01-08 | Plate-fin with footprint wall: channel plumes, R in band | PARTIAL (accepted) | R in band, all checks pass; plumes only as short streaks (user accepted) |
| 24 | 01-09 | Adiabatic wall carries ~0 net radiation | VERIFIED | boundaryRadiationProperties: explicit back_wall (and back for `back: wall`) emissivity 0, absorptivity 0 |
| 25 | 01-09 | Energy check counts boundary radiation | VERIFIED | report.py:217-239 domain energy balance gate with radFlow_* (7 radFlow objects in controlDict); passes at +0.0/+0.1 % in plate-fin reports |
| 26 | 01-09 | free byte-identical; wall changes only radiation settings | VERIFIED | Regression output as above |
| 27 | 01-10 | Even default polar count | VERIFIED | make_case.py:802 default [3, 4]; generated file `nTheta 4; ... 48 rays` |
| 28 | 01-10 | Odd nTheta rounded up with a warning | VERIFIED | Live: `[3, 3]` -> stderr warning, file written with nTheta 4 (make_case and hand_calc) |
| 29 | 01-10 | Plate-fin near measurement on both meshes, README/asset updated | VERIFIED | 2.308/2.314 K/W, all checks pass; README.md:142-143 and asset header give the new numbers |

**Score:** 29/29 (one partial, accepted by the user)

### Required Artifacts

| Artifact | Status | Details |
|---|---|---|
| `.github/regression.sh` | VERIFIED | 111 lines, runs both scripts, hash seed fixed, worktree cleaned up |
| `SKILL.md` | VERIFIED | Emissivity, iterations, back wall, radiation rays, report structure, measurements, style |
| `assets/example-case.yaml` | VERIFIED | Commented per-device emissivity |
| `assets/validation-plate-fin.yaml` | VERIFIED | power_W 9.22, no devices, `back: {wall: footprint}`, foam solid, measurements, 3000 iterations |
| `scripts/cooling_model.py` | VERIFIED | Zero devices, load_back, load_measurements, load_radiation_rays |
| `scripts/hand_calc.py` | VERIFIED | Zero-device output |
| `scripts/make_case.py` | VERIFIED | Back wall patch split, radiation BC for walls, ray default [3, 4], radFlow function objects |
| `scripts/report.py` | VERIFIED | No-device result, domain energy gate |
| `scripts/warmup.py`, `scripts/make_report.py` | VERIFIED | Zero-device warm-up; Turbo style; new figures; six-section build_docx |
| `references/report-structure.md` | VERIFIED | 79 lines; section table, conditions, reasons (citation author error, see below) |

### Key Link Verification

| From | To | Status |
|---|---|---|
| regression.sh | hand_calc.py, make_case.py | WIRED |
| SKILL.md emissivity item | devices/solids/board emissivity keys | WIRED |
| board.power_W | make_case power["ims"] | WIRED (generated case: ims 9.22 W) |
| make_report main | warmup.simulate | WIRED |
| STYLE cfd | Turbo in all CFD figures | WIRED |
| measurements[].point_mm | CFD sample | WIRED (sample_measurements) |
| build_docx | report-structure.md order | WIRED |
| heatsink.back footprint | topoSet/createPatch | WIRED |
| boundaryRadiationProperties | back / back_wall | WIRED |
| solver.radiation_rays | radiationProperties nTheta | WIRED |

### Requirements Coverage

| Requirement | Status |
|---|---|
| BASE-01 | SATISFIED |
| FIX-01 | SATISFIED |
| FIX-02 | SATISFIED |
| FIX-03 | SATISFIED |
| FIX-04 | SATISFIED (plumes partial, accepted) |
| FIX-05 | SATISFIED |
| FIX-06 | SATISFIED |
| REP-01 | SATISFIED (user approved at the 01-05 checkpoint) |
| REP-02 | SATISFIED |
| REP-03 | SATISFIED |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| references/report-structure.md | 70 | Wrong co-authors in the Kirinčić citation (Trp, Lenić instead of Fadiga, Delač) | Warning | Wrong reference in a user-facing doc |
| assets/validation-plate-fin.yaml | measurements comment | "~1.4 K high (R +6 %)" is from the odd-ray model | Info | Stale comment; header and README are correct |

No TODO/FIXME in scripts, regression.sh or report-structure.md.

### Human Verification Required

None outstanding. The figure check against the paper (REP-01) was done at the 01-05 checkpoint; the plume shape (FIX-04) was accepted by the user.

### Gaps Summary

No blocking gaps. Two small text fixes are worth doing: correct the citation in references/report-structure.md and update the stale +6 % comment in the plate-fin asset.

---

_Verified: 2026-10-29_
_Verifier: Claude (gsd-verifier)_
