---
phase: 01-baseline-and-validation-fixes
plan: 03
subsystem: model
tags: [cooling_model, hand_calc, make_case, report, openfoam, validation, FIX-01]

requires:
  - phase: 01-01
    provides: ".github/regression.sh (proof that device cases are unchanged against v0.1.0)"
provides:
  - "Cases without devices: board.power_W (or island power) as the only heat source"
  - "Tbase_heatsink function object (area mean of the sink's contact face with the board), written only for zero-device cases"
  - "report.py section 'Board and base temperature' and gate 'Base temperature settled' for zero-device cases"
  - "Plate-fin validation without the heater workaround: coarse base 49.4 C, R 2.21 K/W (-3 %)"
affects: [report rework in phase 1 (make_report.py still assumes devices), warm-up model]

tech-stack:
  added: []
  patterns:
    - "Zero-device paths are added beside the device paths, so device-case output stays byte-identical"

key-files:
  created: []
  modified:
    - scripts/cooling_model.py
    - scripts/hand_calc.py
    - scripts/make_case.py
    - scripts/report.py
    - assets/validation-plate-fin.yaml
    - README.md
    - CHANGELOG.md
    - .github/regression.sh

key-decisions:
  - "Zero devices allowed when board.power_W > 0 or an island has power; a missing 'devices' key counts as empty. Otherwise: 'no heat source: add devices or board.power_W'"
  - "The zero-device result is the base temperature = area mean of heatsink_to_<board> (where a base thermocouple sits); board maximum (Tmax_ims) reported next to it"
  - "The Tbase_heatsink probe is only written for zero-device cases, so device cases stay identical to v0.1.0"
  - "Hand calc board temperature computed in hand_calc.py from T_base_under_ims_C + P_tot*R_tim; no new key in network(), since its dict goes into case-meta.json"
  - "validation-plate-fin.yaml: the unused electrical block was removed (the loader does not need it)"

duration: 35min
completed: 2026-10-28
---

# Phase 01 Plan 03: Heat Sinks Without Devices Summary

**A case can now have no devices and put its heat into the board through `board.power_W`. The plate-fin validation is converted to this and reaches base 49.4 °C on the coarse mesh (R 2.21 K/W, −2.9 % against the measured 2.28 K/W). All checks pass, and every device case is unchanged against v0.1.0.**

## Performance

- **Duration:** about 35 min (including a 10 min coarse CFD run)
- **Completed:** 2026-10-28
- **Tasks:** 3 (+1 harness fix)
- **Files modified:** 8

## Accomplishments

- `load_config` accepts zero devices when the board or an island carries power. `network()` takes a single pass in that case. With neither devices nor board power, it raises `ValueError: no heat source: add devices or board.power_W` (checked).
- Hand calc on the zero-device plate-fin: sink 50.6 °C (R_sink-air 2.342 K/W), base under board 50.6 °C (2.345 K/W), heated board face 50.7 °C. These match the old heater variant (sink 50.6 °C).
- make_case.py needed no changes for zero devices (power, T0, emissivity, Allrun region list already worked). The only addition is the `Tbase_heatsink` probe.
- report.py with no devices prints "No devices: result is the board/base temperature" and a table (base mean, board max, sink mean, R to ambient, hand calc). It adds the gate "Base temperature settled", and the Tj lines are skipped. On a device case its output is byte-identical to v0.1.0's report.py. I checked this with a synthetic heater case built from the new run's postProcessing data.

## CFD result (coarse, 112,200 cells, 3000 iterations, 8 cores, zero devices)

| Quantity | CFD | R to ambient | Hand calc |
|---|---|---|---|
| Base under the board (mean of contact face) | 49.4 °C | 2.214 K/W (−2.9 %) | 50.6 °C |
| Board maximum | 49.6 °C | 2.232 K/W | 50.7 °C |
| Heat sink mean | 49.3 °C | 2.202 K/W | 50.6 °C |

Gates: all pass. Air speed 0.48 m/s, no air hotter than the solids, mass balance 7e-10 of 1.0e-3 kg/s, air energy balance 9.06/9.06 W, energy balance +0.0 %, heat flow settled (0.00 %), base settled (0.00 K drift), sink rise −6 % vs hand calc. Verdict: all checks pass.

Comparison with the heater-device run (v0.1.0, same mesh settings): the heater's case temperature was 49.8 °C, sink mean 49.5 °C, and the energy balance was +1.5 %. Without the heater, the sink mean is 0.2 K lower and the energy balance closes exactly. The base result sits inside the ±3 % acceptance band (49.3–50.6 °C) but near its lower edge. It is below the 49.8–50.2 °C that the plan's Task 2 verify line expected. Inputs were not tuned.

## Task Commits

1. **Harness fix (deviation)** - `5349e72` (fix)
2. **Task 1: Model and hand calc without devices** - `79aae94` (feat)
3. **Task 2: Case generator and report without devices** - `ad67755` (feat)
4. **Task 3: Convert the plate-fin validation and record it** - `555fc86` (feat)

**Plan metadata:** `docs(01-03): complete heat sinks without devices plan`

## Regression

`.github/regression.sh` exits 0 after every task. Every device case is `same`, the eval specs are `same (not a case file: both sides reject it identically)`, and `assets/validation-plate-fin.yaml` is `new`. The converted asset generates case files identical to the YAML that was run (only the `case.yaml` comments differ).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regression harness flagged traceback line numbers as DIFF**
- **Found during:** Task 1
- **Issue:** The four eval YAMLs that both trees reject showed `DIFF (hand calc)`. Adding lines to hand_calc.py moved the line numbers in the traceback.
- **Fix:** Traceback frames are replaced by `Traceback (frames omitted)`. The exception line and the exit status are still compared.
- **Files modified:** .github/regression.sh
- **Commit:** 5349e72

**2. [Rule 2 - Missing] Base temperature probe for zero-device cases**
- **Found during:** Task 2
- **Issue:** Without devices there is no `case_<device>` probe, so the CFD had no base temperature to report or gate on.
- **Fix:** A `Tbase_heatsink` surfaceFieldValue (areaAverage of `heatsink_to_(ims|islands)`) is written only when there are no devices.
- **Files modified:** scripts/make_case.py
- **Commit:** ad67755

**3. README.md updated** (allowed by the orchestrator): the coarse row changed (49.4 °C, 112 k cells, −3 %). The normal row is now labelled as the v0.1.0 heater run, because it was not rerun.

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2).

## Issues Encountered

- `scripts/make_report.py` (the full PDF/HTML report) still fails with zero devices: `IndexError` at `cfg.devices[0]` in `fig_layout`. Other device assumptions are at lines 651 and 477 and in the figures. It was not in this plan's files and should be handled in the phase-1 report plan. `warmup.py` has not been checked with zero devices.
- SKILL.md does not yet say that `devices` may be empty when `board.power_W` is set. A one-line note in the intake/"More devices" section would make the feature discoverable. It was left out because SKILL.md is not in this plan's files and changes the package hash.

## Next Phase Readiness

- The STATE.md blocker "heater workaround in the plate-fin validation" can be removed.
- The normal-mesh plate-fin result has not been rerun without devices.

---
*Phase: 01-baseline-and-validation-fixes*
*Completed: 2026-10-28*
