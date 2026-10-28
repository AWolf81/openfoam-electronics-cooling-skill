# Requirements: openfoam-electronics-cooling

**Defined:** 2026-10-28
**Core Value:** Junction temperatures you can trust: every CFD result is checked against a hand
calculation and energy balances, and the report says what was assumed.
**Source:** `prd-v0.2-guide-gaps.md` (R1–R6) and the plate-fin validation (FIX).

## v1 Requirements (milestone v0.2.0)

### Baseline

- [ ] **BASE-01**: A regression script builds every eval case and `assets/*.yaml` with v0.1.0 and with the working tree and reports any change in hand-calc output or generated case files
- [ ] **BASE-02**: All existing evals still pass after each phase

### Validation fixes

- [ ] **FIX-01**: A case can heat the sink without devices (`board.power_W`, or a `heat_source: base` option); the plate-fin validation uses it instead of a flat "heater" device
- [ ] **FIX-02**: SKILL.md and the example YAML say that `emissivity` is set per device and that the 0.9 default suits mould compound, not metal or foil
- [ ] **FIX-04**: `heatsink.back` can put the adiabatic wall only behind the sink (`{wall: footprint}` or a rectangle), open air elsewhere; the plate-fin validation uses it and shows per-channel plumes like Kirinčić Fig. 10
- [ ] **FIX-03**: SKILL.md advises more iterations (about 3000) for low-power free convection when "heat flow settled" just fails

### Report and figures

- [ ] **REP-01**: CFD figures use the Turbo colour map with smooth point-interpolated fields and a "Temperature [°C]" legend, aligned with Kirinčić et al. 2025 Figs. 10–12 but smoother; `report.style: cfd` (default) or `ir` (thermal-camera comparisons)
- [ ] **REP-02**: The report shows air section planes (mid fin height, mid width), velocity vectors, a local-scale 3D heat-sink view, and simulated vs measured values when the YAML has `measurements:`
- [ ] **REP-03**: Reports follow `references/report-structure.md`: 1 Result, 2 Inputs, 3 Results, 4 Comparison with measurement, 5 Time behaviour, 6 Checks, each figure shown only when its condition holds

### Altitude (PRD R1)

- [ ] **ENV-01**: YAML `ambient.altitude_m` or `ambient.pressure_Pa` (mutually exclusive, default 101325 Pa; ISA conversion)
- [ ] **ENV-02**: `cooling_model.air_props(T, p)` takes pressure; density, ν, α and Ra follow
- [ ] **ENV-03**: The CFD uses the same pressure (`totalPressure` p0, initial p / p_rgh, thermophysical reference)
- [ ] **ENV-04**: The report's inputs table states the pressure used
- [ ] **ENV-05**: Eval `altitude-hand-calc`: the agent asks for or uses the site altitude ("installed at 2500 m") and Tj rises against sea level

### Loss consistency (PRD R2)

- [ ] **LOSS-01**: `report.py` shows per device `P used`, `P at CFD Tj` and `ΔP %` with the same Rds(on)(T) model
- [ ] **LOSS-02**: New gate "Loss consistency": |ΔP| ≤ 2 % for every device; on failure it prints the rerun command
- [ ] **LOSS-03**: `make_case.py --power-from cases/<prev>` takes powers at the previous run's Tj (with `--init-from` for a short rerun)
- [ ] **LOSS-04**: Devices with fixed `power_W`, solids and islands are skipped; SKILL.md step 5 lists the gate

### Limits and worst case (PRD R3)

- [ ] **LIM-01**: YAML `limits:` list `{name, region | part, quantity: T_max | T_surface_max, value_C, note}`, assumed values marked `# CHECK:`
- [ ] **LIM-02**: `hand_calc.py` and `report.py` report every limit with margin and pass/fail; a failing limit fails the overall verdict even if Tj passes
- [ ] **LIM-03**: `hand_calc.py --sweep key=v1,v2,...` over `ambient`, `current`, `rds_factor`, `velocity` prints the corners and marks the worst; a 3 × 3 sweep runs in < 5 s
- [ ] **LIM-04**: `--worst` writes the worst corner to `case.worst.yaml` for the CFD
- [ ] **LIM-05**: SKILL.md intake asks for typical and worst-case ambient and current; eval `worst-case-corner` checks the sweep runs before CFD

### Release

- [ ] **REL-01**: SKILL.md, `references/physics.md` and CHANGELOG updated; version 0.2.0 released from `main` with the package hash

## v2 Requirements (v0.3 and later)

### Solar load (PRD R4)

- **SOL-01**: YAML `ambient.solar` (irradiance, direction, absorptivity per part); hand calc adds α · G · A_projected
- **SOL-02**: Spike: how v2412 `solarLoad` / fvDOM with a solar calculator combine; documented in `references/openfoam-case-notes.md`
- **SOL-03**: Energy balance gate includes absorbed solar; SKILL.md warns that black anodising absorbs sunlight

### Load profiles (PRD R5)

- **PROF-01**: YAML `load_profile` (piecewise constant, `repeat`); `warmup.py` gives Tj(t), peak, ΔTj per cycle, mean
- **PROF-02**: Optional `zth_jc_foster` per device for short pulses; report says the model is lumped, calibrated to steady CFD

### Anisotropic FR-4 (PRD R6, with Gerber phase 2)

- **BRD-01**: Effective in-plane and through-plane k per zone from Gerber copper coverage and via density
- **BRD-02**: Spike: anisotropic solid conductivity in v2412 on a two-region test case

### Warm-up accuracy

- **WARM-01**: Find why the Infineon warm-up runs about 2× faster than measured (5 vs 9 min)
- **WARM-02**: Remove the 1.5 K end offset of the lumped warm-up model against the CFD

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fan curves / `fanPressure` boundaries | Only matter with a duct or shroud; revisit with enclosures |
| Lifetime prediction as a verdict | Solder fatigue / power-cycling models are not validated here; at most a labelled estimate |
| "Failure rate doubles per 10 K" in reports | Rule of thumb, not a fact |
| Full-detail CAD import | The skill keeps simplify-then-check |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BASE-01 | Phase 1 | Pending |
| BASE-02 | Phase 5 | Pending |
| FIX-01, FIX-02, FIX-03, FIX-04 | Phase 1 | Pending |
| REP-01, REP-02, REP-03 | Phase 1 | Pending |
| ENV-01 – ENV-05 | Phase 2 | Pending |
| LOSS-01 – LOSS-04 | Phase 3 | Pending |
| LIM-01 – LIM-05 | Phase 4 | Pending |
| REL-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-10-28*
*Last updated: 2026-10-28 after Phase 1 planning (figure style and report structure added)*
