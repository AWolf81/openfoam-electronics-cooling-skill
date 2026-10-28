---
phase: 01-baseline-and-validation-fixes
plan: 08
subsystem: case-generation
tags: [make_case, cooling_model, boundary-conditions, createPatch, plate-fin, FIX-04]

requires:
  - phase: 01-05
    provides: "cfd figure style, plate-fin full-wall coarse/normal reference runs"
provides:
  - "heatsink.back: {wall: footprint} | {wall: {y_mm, z_mm}}: wall patch back_wall over a rectangle of the back boundary, open 'back' elsewhere"
  - "Measured evidence that the full back wall leaked 1.1-1.3 W (12-14 %) through the board's back face and that the footprint+foam model gives R 2.41 K/W (coarse)"
affects: [plate-fin validation decision, README validation table, 01-07 docs]

tech-stack:
  added: []
  patterns:
    - "Patch split along grid lines: rectangle edges added to the y/z breakpoints, topoSet faceSet (boxToFace) + createPatch -overwrite before splitMeshRegions; only emitted for the new mode, so old cases stay byte-identical"

key-files:
  created: []
  modified:
    - scripts/cooling_model.py
    - scripts/make_case.py
    - scripts/make_report.py
    - references/openfoam-case-notes.md
    - SKILL.md
    - CHANGELOG.md

key-decisions:
  - "Split by topoSet + createPatch (not multi-block blockMesh): the blockMesh stays one block, so free/wall cases are byte-identical"
  - "Hand calc: exposed base back area outside the board minus the part the wall rectangle covers"
  - "Plate-fin asset NOT switched: the footprint variant left the 2.28 K/W +- 3 % band on the coarse mesh; per the plan the normal run, README and asset header were not done (stop and report)"

duration: ~1.5h
completed: 2026-10-29
---

# Phase 01 Plan 08: Footprint Back Wall Summary

**`heatsink.back: {wall: footprint}` (and an explicit rectangle) works and leaves free/wall cases byte-identical. But the plate-fin validation with it, modelled the way the paper describes (insulated vessel behind the base, open air 30 mm behind the base elsewhere), gives R 2.41 K/W on the coarse mesh (+5.8 %, outside the band). So the plan stopped before the normal run and before the asset/README switch.**

## Paper: what is behind the base (Kirinčić et al. 2025, Sec. 5.1 and 5.3)

- Domain: 100 mm below and above the sink, 30 mm beside it (half model, symmetry at mid-width), 90 mm in front of the fin tips, and **30 mm behind the base, "not including the region behind the heat sink base, since that surface is in contact with the electronic component"**. So the volume behind the base is cut out of the air.
- Boundaries: (1) bottom pressure inlet; (2) lateral, (3) front, (4) top, **(5) upper rear, (6) bottom rear: pressure outlets** (open); **(7) upper and (8) lower horizontal boundaries and (9) the rear vertical boundary behind the heat sink: adiabatic no-slip walls**. These are the faces of the cut-out block behind the base. (10) base isothermal at Tb; (11) symmetry.
- Experiment (Sec. 3): the vessel was insulated on every other face with 25 mm expanded rubber foam, covered in aluminium foil.
- So in the paper only the block behind the base is walled. Above and below it the back of the domain is open, 30 mm behind the base.

## Task 1: footprint-only back wall (c5bfd85)

- `cooling_model.load_back`: `free` | `wall` | `{wall: footprint}` | `{wall: {y_mm: [a, b], z_mm: [c, d]}}`. The last two give mode `partial` and store the rectangle in `sink["back_wall"]`. Invalid forms raise a clear error.
- `make_case`:
  - adds the rectangle edges (clipped to the domain) to the y/z grid breakpoints;
  - adds a `backWallFaces` faceSet to topoSetDict and writes `system/createPatchDict` (back_wall, type wall);
  - Allrun gets `run createPatch -overwrite` before splitMeshRegions;
  - `back_patches()` drives open_names, the T/U/p_rgh/k/omega/nut/alphat wall BCs, the massFlow/condFlow/enthalpyFlow function objects and far_end patch names.
  - The full-wall case keeps patch name `back`. The partial case has `back` (open) plus `back_wall`. Radiation uses the default black entry for both, as before.
- Hand calc: `A_back` = base back area outside the board minus the part the wall covers (0 for the plate-fin).
- make_report inputs table: "wall behind the sink only, open air around it" or the rectangle.
- Verified:
  - `.github/regression.sh` exits 0 against v0.1.0 and against HEAD, which also covers the plate-fin `back: wall` asset.
  - 20-iteration smoke run: checkMesh OK on all regions; `back_wall` 123.0 cm² over y 0–123, z 0–100 mm, `back` 790.5 cm²; the sum is the whole 203 × 450 mm boundary.
  - The explicit-rectangle variant generates the expected boxToFace.

## Task 2: plate-fin rerun (stopped at the acceptance gate)

### Model used

The variant is saved, not committed, at `.../validation/rijeka-plate-fin/validation-plate-fin-backfoot.yaml`. It follows the paper's domain:
- `back: {wall: footprint}`;
- `solids: vessel_insulation`, 25 mm foam with k 0.036 and emissivity 0.05 behind the 2 mm vessel wall;
- `clearance_mm.back: 3`, so the back boundary is 30 mm behind the base.

The foam fills the region the paper cuts out. Without it, a 30 mm deep air pocket would sit behind the heated board.

### Results

| Run | Base °C | R K/W | vs 2.28 | Checks | Heat into air: sink / board / foam / back-wall radiation |
|---|---|---|---|---|---|
| Full wall, coarse (existing) | 49.4 | 2.214 | −2.9 % | all pass | 7.96 / 1.26 / – / 2.81 W |
| Full wall, normal (existing) | 49.7 | 2.242 | −1.7 % | all pass | 8.08 / 1.14 / – / 3.09 W |
| **Footprint + foam, coarse** | **51.3** | **2.413** | **+5.8 %** | **all pass** (energy −0.0 %, settled, rise +2 % vs hand calc) | 8.75 / 0.10 / 0.37 / 0.03 W |
| Footprint, normal | not run (stop rule) | | | | |

### Why R went up

The full-wall model did not send all the heat through the sink. **1.1–1.3 W (12–14 %) left through the board's back face into the 5 mm air gap.** That gap is an open-ended vertical channel in front of the adiabatic back wall.

The real vessel was insulated there. With the foam that leak drops to 0.47 W. Through the sink alone, R is about the same in both models: 2.53 K/W with the footprint wall vs 2.58 (coarse) / 2.55 (normal) with the full wall. So the open back helps the sink slightly, and the earlier −2 % agreement depended partly on the leak.

### Radiation artifact (side finding)

The full back wall is zeroGradient in T but black for radiation. It emitted 2.8–3.1 W net, which is not energy-conserving. The solids' reported radiation was −0.16 W in those runs (hand calc +0.15). With the footprint wall it is 0.03 W, but the reported radiation is −0.29 W (open boundaries at outflow temperature radiate as black). Small next to 9.22 W, but worth a separate fix: a radiatively adiabatic wall.

### Plumes

Image: `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/mid-height-backwall-vs-footprint.png`. It has three panels: full wall coarse, full wall normal, footprint coarse. The fourth (footprint normal) is empty because that run was not made. Script: `mid_height_backwall.py` in the same folder.

- Full wall: only the two edge "flames"; the centre plume clings to the back wall.
  - Coarse: T max at x = 3 mm, 47.8 °C; at x = 21 mm only 32.7 °C.
  - Normal: T max at x = −1 mm.
- Footprint: the plume now rises through the fin region.
  - Centre channel at z = 130 mm: T max at x = 11 mm; at x = 21 mm 40.6 °C instead of 31–33 °C.
  - All 10 channels are equally hot at mid fin height (45.0–45.4 °C at z = 110 mm), like Fig. 10's "fairly uniform across all channels".
  - Short streaks over each channel are visible just above the sink top. They merge within ~10–15 mm into one wide plume, so there are no long separate per-channel plumes. On the coarse mesh (4 cells per gap) the hot lines sit on the fins, not over the channel centres (channel minus fin-line −1.4 K).
- Verdict: the plume no longer clings to the back wall, and the channels are uniform. Distinct per-channel plumes above the sink appear only weakly (coarse mesh).

### cfd-plume

Rendered with `make_report.py --style cfd` for the coarse footprint case (the normal case was not run), in `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/plate-fin-footprint-cfd/figures/cfd-plume.png`.

- The plume rises straight up above the sink and is centred over it, with air on both sides above and below the sink (30 mm on the back side), and the panel is centred.
- Behind the base the section shows the foam block, since the domain ends 3 mm behind it.

## Deviations from Plan

1. **[Rule 2 - Missing Critical] Insulation block behind the vessel wall.** With a footprint wall alone and 30 mm back clearance, the heated board would face a 30 mm open air pocket. The paper cuts that region out, and the real vessel had 25 mm foam. Modelled as `solids: vessel_insulation` in the variant YAML (not committed).
2. **Stop rule applied.** Coarse R 2.413 K/W is outside 2.28 ± 3 % (2.21–2.35). Per the plan ("stop and report, do not tune"), these were not done: the normal footprint run, the asset switch, the asset header numbers and the README table rows. The asset is still `back: wall` (restored, unchanged). CHANGELOG and SKILL.md document only the new option, in commit 3de500b.
3. Smoke-test files are left in `.../validation/rijeka-plate-fin/smoke/` (rm -rf outside /tmp is blocked).

## Decision needed (for the orchestrator / user)

Pick one of these for the plate-fin validation asset:

- (a) Keep `back: wall` and document the 12–14 % board back-face leak as a known reason for the good agreement.
- (b) Switch to footprint + foam and accept +6 % (coarse; normal is likely similar or slightly higher). Here all the heat goes through the sink as in the experiment, and the remaining gap is a sink-side under-prediction of heat transfer.
- (c) Footprint without foam, closer to "open behind": run it once to see where it lands. Physically it is less faithful.

The radiation artifact of the zeroGradient black wall is a separate small fix candidate.

## Next Phase Readiness

- Feature ready and regression-safe.
- The plate-fin validation decision is open; STATE todos "back wall" and "cfd-plume left" are partly answered: the plume separates from the back, and cfd-plume is centred with the footprint model.
