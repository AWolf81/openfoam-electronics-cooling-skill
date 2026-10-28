# Roadmap: openfoam-electronics-cooling

## Overview

v0.1.0 is released and validated (Infineon 48 V switch, Kirinčić plate-fin experiment). Milestone
v0.2.0 closes the P0 gaps from the Cadence cooling-guide review: sea-level-only air, losses that
do not follow the CFD temperatures, and verdicts on one limit at one operating point. It starts
with a regression baseline and the small fixes the validation exposed, so every later phase can
prove it left v0.1.0 results unchanged. Work happens on `develop`; v0.2.0 is released from `main`
once the user has tried the skill locally.

## Milestones

- ✓ **v0.1.0** — released 2026-10-28
- 🚧 **v0.2.0** — Phases 1–5 (in progress)
- 📋 **v0.3.0** — solar load, load profiles, warm-up accuracy (planned, see REQUIREMENTS.md v2)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Baseline, validation fixes and report** - Regression harness; heat sinks without devices; emissivity/iteration guidance; paper-style figures and report structure
- [ ] **Phase 2: Altitude** - Ambient pressure in the hand calc and the CFD (PRD R1)
- [ ] **Phase 3: Loss consistency** - Loss at the CFD's Tj, a gate, and `--power-from` reruns (PRD R2)
- [ ] **Phase 4: Limits and worst-case corners** - `limits:`, corner sweep, worst corner to CFD (PRD R3)
- [ ] **Phase 5: Release 0.2.0** - Docs, evals, changelog, release from `main`

## Phase Details

### Phase 1: Baseline, validation fixes and report
**Goal**: A regression check that proves later phases leave v0.1.0 results unchanged, the three fixes from the plate-fin validation, and reports whose figures and structure match good validation practice (Kirinčić et al. 2025 figure types, Turbo colour map, answer first)
**Depends on**: Nothing (first phase)
**Requirements**: BASE-01, FIX-01, FIX-02, FIX-03, REP-01, REP-02, REP-03
**Success Criteria** (what must be TRUE):
  1. One command compares hand-calc output and generated case files of every eval and asset against v0.1.0 and lists differences
  2. The plate-fin validation runs with the heat put into the base directly, no "heater" device, and still gives 2.28 K/W ± 3 %
  3. SKILL.md tells the agent about per-device emissivity and extra iterations for low-power free convection
  4. CFD figures use Turbo, smooth fields and a paper-style legend; the user approved them against the paper's Figs. 10–12
  5. Reports show air sections, velocity vectors, a local-scale sink view and measured vs simulated, in the documented six-section structure
**Research**: Done during planning (paper figures, report practice, colour maps)
**Plans**: 7 plans in 6 waves

Plans:
- [ ] 01-01: Regression script (`.github/regression.sh`) and clean first run — wave 1
- [ ] 01-02: Emissivity and iteration guidance (FIX-02, FIX-03) — wave 1
- [ ] 01-03: Heat sinks without devices: model, hand calc, case, report; plate-fin re-validated (FIX-01) — wave 2
- [ ] 01-04: Warm-up and Word report without devices — wave 3
- [ ] 01-05: Turbo figure style, `report.style: cfd | ir`, user check against the paper (REP-01) — wave 4
- [ ] 01-06: Air sections, velocity vectors, local-scale sink, measured vs simulated (REP-02) — wave 5
- [ ] 01-07: Report structure and figure rules (REP-03) — wave 6

### Phase 2: Altitude
**Goal**: Correct results away from sea level
**Depends on**: Phase 1
**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04, ENV-05
**Success Criteria** (what must be TRUE):
  1. The default case is byte-identical to v0.1.0 (regression script)
  2. At 3000 m the hand calc's convective h is within ± 2 % of the ρ^0.5 scaling (about −17 %)
  3. A 3000 m CFD run passes the energy and hand-calc gates; the report states the pressure
  4. Eval `altitude-hand-calc` passes
**Research**: Unlikely (ISA formula given in the PRD)
**Plans**: 2 plans

Plans:
- [ ] 02-01: `air_props(T, p)`, YAML keys, hand calc and report inputs table
- [ ] 02-02: CFD pressure (boundaries, initial fields, thermophysics), 3000 m run, eval

### Phase 3: Loss consistency
**Goal**: CFD losses consistent with CFD temperatures
**Depends on**: Phase 1
**Requirements**: LOSS-01, LOSS-02, LOSS-03, LOSS-04
**Success Criteria** (what must be TRUE):
  1. The device table shows P used, P at CFD Tj and ΔP %
  2. The example case passes the loss gate or converges in ≤ 2 reruns
  3. A synthetic case where the hand calc under-predicts Tj by ≥ 10 K fails the gate; the printed rerun passes
**Research**: Unlikely
**Plans**: 2 plans

Plans:
- [ ] 03-01: Loss at CFD Tj in `report.py` and the new gate
- [ ] 03-02: `make_case.py --power-from` with `--init-from`; SKILL.md step 5

### Phase 4: Limits and worst-case corners
**Goal**: Judge a design against all its limits and its worst corner
**Depends on**: Phase 2 (sweep includes ambient and pressure-dependent air)
**Requirements**: LIM-01, LIM-02, LIM-03, LIM-04, LIM-05
**Success Criteria** (what must be TRUE):
  1. A 3 × 3 corner sweep runs in < 5 s and marks the worst row
  2. `--worst` writes `case.worst.yaml`, and the CFD of it runs unchanged
  3. A failing touch-temperature limit makes the overall verdict FAIL even when Tj passes
  4. Eval `worst-case-corner` passes
**Research**: Unlikely
**Plans**: 3 plans

Plans:
- [ ] 04-01: `limits:` in YAML, hand calc and report
- [ ] 04-02: `--sweep` and `--worst`
- [ ] 04-03: SKILL.md intake, eval `worst-case-corner`

### Phase 5: Release 0.2.0
**Goal**: v0.2.0 on `main` after the user has tried `develop` locally
**Depends on**: Phases 2, 3, 4
**Requirements**: REL-01, BASE-02
**Success Criteria** (what must be TRUE):
  1. All evals and the regression script pass; plate-fin and Infineon validations rerun
  2. SKILL.md, `references/physics.md`, CHANGELOG updated; `.github/release.sh 0.2.0` run on `main`
  3. The release workflow publishes the notes, hash and SHA256SUMS
**Research**: Unlikely
**Plans**: 1 plan

Plans:
- [ ] 05-01: Docs, full eval run, merge `develop` to `main`, release

## Progress

**Execution Order:** 1 → 2 → 3 → 4 → 5 (Phase 3 can run in parallel with Phase 2)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Baseline, validation fixes and report | v0.2.0 | 0/7 | Planned | - |
| 2. Altitude | v0.2.0 | 0/2 | Not started | - |
| 3. Loss consistency | v0.2.0 | 0/2 | Not started | - |
| 4. Limits and worst-case corners | v0.2.0 | 0/3 | Not started | - |
| 5. Release 0.2.0 | v0.2.0 | 0/1 | Not started | - |
