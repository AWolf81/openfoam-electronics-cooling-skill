# PRD: openfoam-electronics-cooling v0.2 – closing the gaps from the Cadence cooling guide

Status: draft for a GSD session · Owner: Alexander · Base: v0.1.0 (2026-10-28)

## 1. Context

The Cadence ebook "Engineer's Guide to Simulating Electronics Cooling" (02/2026) was reviewed
against the skill. The skill already exceeds the guide on result credibility (hand calc as
yardstick, energy-balance gates, mesh independence, IR comparison, `--calibrate`). The guide does
name six inputs or analyses the skill does not cover. This PRD turns them into scoped work.

None of these are correctness bugs in v0.1.0 for its stated scope (sea level, indoor, steady,
open sink). They widen the scope and tighten one consistency loop.

## 2. Goals

- G1 Correct results away from sea level.
- G2 CFD losses consistent with CFD temperatures (closed Rds(on)–Tj loop).
- G3 Judge a design against all its limits and its worst-case corner, not only Tj(max) at one point.
- G4 Outdoor equipment: solar load.
- G5 Duty cycles: Tj over time and ΔTj per cycle.
- G6 (with Gerber phase 2) FR-4 boards with anisotropic effective conductivity.

## 3. Non-goals

- Fan curves / `fanPressure` boundaries (only matter with a duct or shroud; revisit with enclosures).
- Lifetime prediction (solder fatigue, power-cycling models) as a verdict. At most an optional,
  clearly labelled estimate later.
- Arrhenius "failure rate doubles per 10 K" in reports. Rule of thumb, not to be stated as fact.
- Full-detail CAD import "without simplification". The skill keeps simplify-then-check.

## 4. Requirements

Priority: P0 = this session, P1 = next, P2 = later / tied to phase 2.

### R1 Altitude / ambient pressure (P0)

- YAML: `ambient.altitude_m` or `ambient.pressure_Pa` (mutually exclusive; default 101325 Pa).
  Altitude → pressure via ISA: `p = 101325 · (1 − 2.25577e-5 · h)^5.25588`.
- `cooling_model.air_props(T, p)`: density from p; everything derived (ν, α, Ra) follows.
- CFD: `p0` of the `totalPressure` boundaries, the initial `p`/`p_rgh` and `constant/air`
  thermophysical reference use the same pressure.
- Report states the pressure used in the inputs table.
- Expected effect for orientation: free-convection h ∝ ρ^0.5 (Ra ∝ ρ², Nu ∝ Ra^¼), so 3000 m
  (≈ 0.69 · p0) gives ≈ −17 % h. Radiation unchanged.

Acceptance
- Default case: hand-calc and generated case byte-identical to v0.1.0 (regression).
- 3000 m case: hand-calc convective h within ±2 % of the ρ^0.5 scaling; CFD energy and
  hand-calc gates still pass.
- New eval `altitude-hand-calc`: grader checks that the agent asks for or uses site altitude when
  the prompt says "installed at 2500 m" and that Tj rises vs sea level.

### R2 Loss–temperature consistency after CFD (P0)

Today `make_case.py` uses the hand-calc fixed-point power; if CFD Tj differs, the loss is off.

- `report.py`: per device, recompute `P(Tj_cfd)` with the same Rds(on)(T) model; show
  `P used`, `P at CFD Tj`, `ΔP %` in the device table.
- New gate **Loss consistency**: |ΔP| ≤ 2 % for every device. Fail → message with the rerun command.
- `make_case.py --power-from cases/<prev>`: takes powers at the previous run's Tj (optionally
  `--init-from` the same case so the rerun is short).
- Devices with fixed `power_W` and solids/islands are skipped (no Tj dependence).

Acceptance
- Example case passes the gate or converges in ≤ 2 reruns.
- Synthetic case where hand calc under-predicts Tj by ≥ 10 K: gate fails, rerun passes.
- SKILL.md step 5 lists the new gate.

### R3 Additional limits and worst-case corners (P0)

- YAML `limits:` list, each `{name, region | part, quantity: T_max | T_surface_max, value_C, note}`,
  e.g. a touch-temperature limit on the heat sink's outer surfaces (user supplies the value and
  the standard it comes from; skill marks it `# CHECK:` if assumed).
- `hand_calc.py` and `report.py` report every limit with margin and pass/fail.
- `hand_calc.py --sweep key=v1,v2,... [key=...]` (keys: `ambient`, `current`, `rds_factor`,
  `velocity`): prints a table of corners and the worst one; `--worst` writes that corner to
  `case.worst.yaml` for the CFD.
- SKILL.md intake: ask for typical and worst-case ambient and current; CFD the worst corner.

Acceptance
- Sweep over 3 × 3 corners runs in < 5 s and marks the worst row.
- Report shows a limits table; a failing touch limit gives an overall FAIL even if Tj passes.
- Eval `worst-case-corner`: grader checks the agent runs the corner sweep before CFD.

### R4 Solar load (P1)

- YAML `ambient.solar: {G_W_m2, direction: [x,y,z], absorptivity: {heatsink: 0.9, ...}}`.
- Hand calc: `Q_solar = α · G · A_projected` added to the sink balance (projected area of the
  envelope normal to the sun direction).
- CFD: OpenFOAM v2412 solar load. **Spike first:** confirm how `solarLoad` / fvDOM with a solar
  calculator combine in v2412 (start from the `externalSolarLoad` tutorial already referenced);
  pick one, document it in `references/openfoam-case-notes.md`.
- SKILL.md: note that black anodising absorbs sunlight strongly (α ≈ ε); outdoors the
  "anodise for radiation" advice can turn into a net heat gain. Ask for finish and shading.

Acceptance
- Energy balance gate includes absorbed solar (loss + solar in = out, within 2 %).
- Hand calc vs CFD sink rise within the existing 25 % gate on a sunlit example.

### R5 Load profiles and ΔTj per cycle (P1)

- YAML `load_profile: [[t_s, I_A], ...]` (piecewise constant, optionally `repeat: n`).
- `warmup.py`: drive the existing lumped model with the profile; output Tj(t) per device,
  Tj peak, ΔTj per cycle, and the mean Tj; plot in the report.
- Optional `zth_jc_foster: [[R_K_W, tau_s], ...]` per device for pulses shorter than the
  package's time constant (steady Rth(j-c) overstates short pulses); fall back to Rth(j-c).
- Report states: lumped model calibrated to the steady CFD; not a field-resolved transient.

Acceptance
- Constant profile reproduces today's warm-up curve exactly.
- Square-wave profile: ΔTj per cycle reported; with Foster data, single short pulse peak lower than
  with steady Rth(j-c).
- Runs in seconds on the example.

### R6 Anisotropic FR-4 board (P2, with Gerber phase 2)

- From Gerber copper coverage per layer and via density per area, compute effective
  `k_in_plane` (parallel) and `k_through` (series + via columns) per zone.
- Hand calc uses them for spreading; CFD meshes the board as a solid with anisotropic κ.
- **Spike first:** verify anisotropic solid conductivity in v2412 (`constAnIso`-type transport
  with a coordinate system) on a two-region test case.

Acceptance
- Analytic check: uniform board with known layer stack matches the parallel/series formula ±1 %.
- Via array under a part: CFD vs 1D via-column estimate within 10 %.

## 5. Cross-cutting

- Every new YAML key has a default that keeps v0.1.0 results unchanged; regression run on all
  existing evals.
- Every new requirement gets an eval folder in the existing format (`case.yaml`, `prompt.md`,
  `graders/*.md`).
- Update SKILL.md (intake, gates, limits section), `references/physics.md`, CHANGELOG
  `[Unreleased]`, bump to 0.2.0.
- Packaging: this PRD lives outside the hashed package (keep it in `.planning/` and exclude that
  path in `.github/package-hash.sh`, or remove it before tagging), so the release hash stays a
  hash of the skill only.

## 6. Suggested session plan

1. R1 altitude (smallest, touches `cooling_model.py` + `make_case.py` boundaries).
2. R2 loss consistency gate + `--power-from`.
3. R3 limits + sweep.
4. Spike for R4 solar in v2412; write findings into case notes; implement if straightforward.
5. Release 0.2.0 when R1–R3 pass all evals. R4–R6 can follow in 0.3.
