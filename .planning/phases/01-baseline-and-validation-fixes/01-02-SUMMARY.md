---
phase: 01-baseline-and-validation-fixes
plan: 02
subsystem: docs
tags: [skill-md, emissivity, radiation, convergence, free-convection]

requires: []
provides:
  - Per-part emissivity guidance in SKILL.md intake (FIX-02)
  - Iteration advice for low-power free convection at the "Settled" gate (FIX-03)
  - Commented device emissivity line in assets/example-case.yaml
affects: [regression baseline, report, later validation plans]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: [SKILL.md, assets/example-case.yaml, CHANGELOG.md]

key-decisions:
  - "Emissivity guidance names the defaults the code really uses: heatsink 0.85, board/devices/solids 0.9"
  - "Iteration advice sits in the Settled gate bullet of step 5; --init-from mentioned because it copies the latest fields for any mode when the mesh matches"

patterns-established: []

duration: 6min
completed: 2026-10-28
---

# Phase 1 Plan 02: Emissivity and iteration guidance Summary

**SKILL.md now tells the agent to set 0.03-0.1 emissivity on metal or foil-covered heat sources and to rerun a ~10 W free-convection case at 3000 iterations when "Heat flow settled" misses by < 1 %, both with the plate-fin numbers.**

## Performance

- **Duration:** about 6 min
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Intake item 4 (Emissivity) lists `heatsink.emissivity` (default 0.85), `board.emissivity`,
  `devices[].emissivity`, `solids[].emissivity` (default 0.9); 0.03-0.1 for bare metal, lugs and
  foil/insulation-covered sources; plate-fin: 0.6 W of 9.2 W radiated out of an insulated back,
  balance +5-7 % at 0.9, +1-1.5 % at 0.03.
- Step 5 "Settled" gate: rerun with `solver.iterations: 3000` when the miss is below 1 % and the
  energy balance passes (1500: 0.65 % / 0.53 %; 3000: 0.28 % / 0.21 %); `--init-from` the first
  case shortens the rerun.
- `assets/example-case.yaml` q1: `# emissivity: 0.9` comment with a one-line explanation.
- CHANGELOG [Unreleased] / Changed: two lines.

## Task Commits

1. **Task 1: Emissivity per part (FIX-02)** - `5b83ec6` (docs)
2. **Task 2: Iteration advice and changelog (FIX-03)** - `489e79c` (docs)

## Verification

- `hand_calc.py` output for `assets/example-case.yaml` and `assets/validation-plate-fin.yaml`
  identical before and after (diff of /tmp/hc0102/before-*.txt vs after-*.txt).
- `grep "devices\[\].emissivity" SKILL.md` and `grep 3000 SKILL.md` find the new text.

## Deviations from Plan

None - plan executed as written. STATE.md not updated (orchestrator does it after the wave).
