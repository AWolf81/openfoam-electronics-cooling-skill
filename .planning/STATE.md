# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-28)

**Core value:** Junction temperatures you can trust: every CFD result is checked against a hand calculation and energy balances, and the report says what was assumed.
**Current focus:** Phase 1 — Baseline, validation fixes and report

## Current Position

Phase: 1 of 5 (Baseline, validation fixes and report)
Plan: 9 of 10 in current phase
Status: In progress (wave 8: 01-07)
Last activity: 2026-10-29 — Wave 7 done: 01-10 even ray default [3, 4]; plate-fin R coarse 2.308, normal 2.314 K/W (+1.5 %), TC deviations +0.45…+0.55 K absolute, +0.01…+0.10 K relative to TCb

Progress: [█████████░] 90% (9 of 10 plans in phase 1)

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:
- Setup: work on `develop`, release from `main` only after the user has tried the skill locally.
- Setup: `.planning/` is excluded from the package hash (README, SKILL.md, package-hash.sh, release workflow).
- Phase 1: CFD figures use Turbo (smooth rainbow look like the Fluent figures in Kirinčić et al. 2025, without false edges); IR palette only for thermal-camera comparisons.
- 01-01: regression.sh pins PYTHONHASHSEED=0: make_case.py writes interface patches in set order (order-only differences between runs).
- 01-05: cfd style = Turbo, 256 levels, point data, 2.5x render, 200 dpi; arrows as vector glyphs every ~8 mm; IR byte-identical. Outputs go to the project folder, never /tmp (/tmp was cleared once).
- 01-08 (user, 2026-10-29): plate-fin validation uses the wall behind the sink + 25 mm foam (as in the experiment); acceptance = measurement uncertainty ±2u = ±6.6 % (paper: u = 3.28 %), not ±3 %. The earlier whole-wall agreement was flattered by 12-14 % heat leaking out the back.
- Phase 1: report structure 1 Result, 2 Inputs, 3 Results, 4 Comparison with measurement, 5 Time behaviour, 6 Checks.

### Pending Todos

- SKILL.md: say that `devices` may be empty when `board.power_W` is set (fold into 01-07 docs).
- Layout figure: dimension labels overlap axis numbers when the board covers the whole sink (cosmetic; 01-07 may fix).
- (done in 01-08: plume no longer clings to the wall; per-channel plumes still merge 15-20 mm above the sink, Fig. 10 not fully reproduced) `heatsink.back: wall` makes the WHOLE back boundary an adiabatic wall (full domain height). In the plate-fin case the plume then clings to it (normal mesh: centre-channel plume max at x = −2…3 mm, i.e. on the wall; fresh air enters through the fin tips at ~1 cm/s), so per-channel plumes as in Kirinčić Fig. 10 do not appear at mid fin height. Real setup: insulated vessel only behind the base, open air above. Candidate fix: wall only over the sink/vessel footprint (`back: {wall: footprint}`), rerun plate-fin and compare R and Fig. 10. Normal mesh R 2.242 K/W (−1.7 %), all checks pass.
- hand_calc.py zero-device output prints "Base under board" and "R_sink-air" twice (cosmetic).

### Blockers/Concerns

- RESOLVED in 01-10: default radiation_rays [3, 4] (even nTheta), odd values rounded up with a warning. Regression vs v0.1.0 now shows DIFF in constant/air/radiationProperties for every case with radiation (expected, documented).

- Known issues carried from v0.1.0: warm-up 2× faster than the Infineon measurement; 1.5 K end offset of the lumped warm-up (v2: WARM-01, WARM-02).

## Session Continuity

Last session: 2026-10-28
Stopped at: Phase 1 planned; next is `/gsd:execute-phase 1`
Resume file: None
