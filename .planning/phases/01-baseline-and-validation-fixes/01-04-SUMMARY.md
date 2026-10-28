---
phase: 01-baseline-and-validation-fixes
plan: 04
subsystem: report
tags: [warmup, make_report, docx, pdf, FIX-01]

requires:
  - phase: 01-03
    provides: "zero-device cases (board.power_W), Tbase_heatsink probe, finished plate-fin coarse CFD"
provides:
  - "warmup.py: zero-device lumped model (board node + sink); summary hottest = \"board\", t63/t90/t99 on T_ims_C"
  - "make_report.py: full Word/PDF/video report for cases without devices"
affects: [01-05..01-07 report rework (structure 1 Result ... 6 Checks), docs plan 01-07]

tech-stack:
  added: []
  patterns:
    - "Zero-device branches beside the device branches; device output byte-identical (figures, warmup.csv, docx text)"

key-files:
  created: []
  modified:
    - scripts/warmup.py
    - scripts/make_report.py

key-decisions:
  - "Warm-up without devices follows the board node (T_ims_C = board maximum calibrated to Tmax_ims); summary key 'hottest' is 'board', Tj_end_C keeps its name and holds the board end temperature"
  - "warmup.csv P_W carries the board power when there are no devices (device cases unchanged: device losses only)"
  - "Report result for zero devices: base (Tbase_heatsink tail mean, same as report.py), board max, sink mean, each with hand calc and R to ambient"
  - "Temperature path for zero devices: ambient -> sink mean -> base under board -> board spreader"

duration: 25min
completed: 2026-10-28
---

# Phase 01 Plan 04: Warm-up and Report Without Devices Summary

**make_report.py now produces the full Word/PDF report, six figures, warm-up and heat-up video for a bare heat sink heated through the board. On the plate-fin case it shows base 49.4 °C (R 2.214 K/W), board 49.6 °C and sink 49.3 °C next to the hand calc, and the board warms up with t63 14.8 min and t90 32.7 min. The Infineon device report is byte-identical before and after the change.**

## Performance

- **Duration:** about 25 min (including three full report renders of the Infineon case)
- **Completed:** 2026-10-28
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- warmup.py with zero devices: the board node and the sink only. The curve, `Tj_end_C` and t63/t90/t99 are keyed on `T_ims_C` and labelled "board". The stability limit no longer divides by `len(cfg.devices)`.
  - Plate-fin CFD-calibrated: board ends at 49.6 °C, t63 14.8 min, t90 32.7 min, t99 63.2 min (sink 420 J/K, vessel wall 59.8 J/K).
  - Hand-calc-only: 50.7 °C, t63 16.0 min, t90 35.0 min.
- make_report.py fixes:
  - Stack-up: "Heat put into the board" replaces the package layer.
  - Temperature path starts at the board.
  - Plume slice cuts through the board centre (y = 62 mm).
  - Video curve follows the board.
  - Result table shows base, board and sink with hand calc, CFD and R to ambient.
  - Inputs row shows the heat input.
  - Setup row shows the base temperature.
  - Captions and limits are adjusted.
- Plate-fin report at `/tmp/oec-0103/cases/plate-fin-coarse-report/`:
  - thermal-report.docx and .pdf, heatup.mp4, warmup.csv
  - figures: assembly-3d, cfd-plume, cfd-solids, layout, temperature-path, warmup
- A hand-calc-only report from `assets/validation-plate-fin.yaml` also renders (4 figures plus the PDF).

## Before/after on device cases

- **warmup.py:** CSV and JSON are identical (`cmp`) for `assets/example-case.yaml` (hand calc) and for the Infineon case `noisl-cu50-sink-2p4ms-sst` (CFD-calibrated).
- **make_report.py on the Infineon case** (`/tmp/oec-0104/before-infineon` vs `/tmp/oec-0104/after2-infineon`):
  - same file list
  - all 6 PNGs byte-identical
  - warmup.csv, report.md, case.yaml and case-meta.json identical
  - docx text (paragraphs and tables) identical
- The project's own report folder was not touched.

## Task Commits

1. **Task 1: Warm-up without devices** - `864e6c4` (feat)
2. **Task 2: Word/PDF report without devices** - `67e510a` (feat)

**Plan metadata:** `docs(01-04): complete warm-up and report without devices plan`

## Regression

`.github/regression.sh` exits 0 after both tasks:
- every device case is `same`
- the evals are `same (both sides reject it identically)`
- the plate-fin asset is `new`

## Deviations from Plan

**1. [Rule 2 - Missing] P_W column in warmup.csv was 0 without devices**
- **Found during:** Task 1
- **Issue:** P_W sums only device losses, so the zero-device warm-up figure title would read "0.0 W total".
- **Fix:** P_W carries the board power when there are no devices. Device cases are unchanged.
- **Commit:** 864e6c4

Beyond the plan's list, inputs and captions were also adjusted for zero devices: electrical rows are replaced by "Heat input", and the Figure 1/3/5 captions, the warm-up paragraph and the first limits bullet are reworded. All of these changes are conditional, and the device text is verified identical.

**Total deviations:** 1 auto-fixed (Rule 2).

## Issues Encountered

- The layout figure's panel (a) dimension labels ("123 mm", "100 mm") overlap the axis tick labels when the board covers the whole sink. This is pre-existing label placement and cosmetic. It was left for the report-rework plans.
- The case.yaml copy inside `/tmp/oec-0103/cases/plate-fin-coarse` still carries the old heater-era header comments (from the 01-03 run). It has no effect.

## Next Phase Readiness

- FIX-01 is complete across hand_calc, make_case, report, warmup and make_report.

---
*Phase: 01-baseline-and-validation-fixes*
*Completed: 2026-10-28*
