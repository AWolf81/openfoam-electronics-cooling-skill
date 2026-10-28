---
phase: 01-baseline-and-validation-fixes
plan: 09
subsystem: case-generation
tags: [make_case, report, fvDOM, boundaryRadiationProperties, energy-balance, plate-fin, FIX-05]

requires:
  - phase: 01-08
    provides: "back_wall patch (partial wall), plate-fin full-wall and sink-only runs, the 2.8-3.1 W wall-radiation finding"
provides:
  - "Adiabatic boundary walls (back with back: wall, back_wall) are perfect reflectors: net radiation 0 W"
  - "radFlow_<patch> function objects (only in cases with a boundary wall) and a domain energy balance gate in report.py"
  - "Measured: odd nTheta (default [3, 3]) loses radiation into horizontal low-emissivity faces; plate-fin R 2.413 -> 2.308 K/W with [3, 4]"
affects: [phase 1 validation numbers (if the ray default changes), SKILL.md checks list]

tech-stack:
  added: []
  patterns:
    - "Function objects and dictionary entries emitted only for the mode that needs them, so back: free cases stay byte-identical"

key-files:
  created: []
  modified:
    - scripts/make_case.py
    - scripts/report.py
    - references/openfoam-case-notes.md
    - CHANGELOG.md

key-decisions:
  - "Wall radiation BC: lookup with emissivity 0 / absorptivity 0 (perfect reflector), not a re-radiating BC: zero net flux is what an adiabatic wall has in steady state, and it needs no new field"
  - "Domain gate leaves the wall out of the balance (heat in = convection + radiation out through the open boundaries); counting the wall's net flux as a term would make the balance close whatever the wall does"
  - "Domain gate only where radFlow_* data exist (boundary-wall cases), so device-case reports keep their numbers and controlDicts stay byte-identical"
  - "Open boundaries keep radiating at their local (inletOutlet) T: the warm outflow adds ~0.13-0.15 W of emission, nearly all leaving through the other open boundaries; separating it needs an extra field and changes every case"
  - "Default radiation_rays left at [3, 3] despite the odd-nTheta finding: changing it changes every case and the validation numbers; left for a decision"

duration: ~1.5h (incl. three coarse runs)
completed: 2026-10-29
---

# Phase 01 Plan 09: Radiation-Neutral Walls Summary

**Boundary walls are now perfect reflectors (emissivity 0): net radiation through the plate-fin full back wall went from −2.81 W to −0.000 W. report.py has a domain energy gate that fails the old run (+30.8 %) and passes the fixed one (+0.1 %). R of the full-wall case changed 2.214 → 2.206 K/W; the current sink-only asset is unchanged at 2.413 K/W. Side finding: with the default odd nTheta = 3, horizontal low-emissivity faces absorb radiation that does not exist. With nTheta = 4 the current asset gives 2.308 K/W (measured 2.28).**

## Task 1: measure, then fix (767d9d6)

Per-patch net qr was measured on the existing runs. The data are copies in `.../validation/rijeka-plate-fin/qr-measure/<case>/`, made with `postProcess -region air -dict system/qrPatches`, so the original cases were not touched. qr is positive out of the air. A negative value means the patch puts radiation into the domain.

| Patch | full wall coarse (old) | full wall normal (old) | full wall coarse **radfix** | sink-only coarse (old) | sink-only coarse **radfix** | sink-only coarse radfix **rays [3,4]** |
|---|---|---|---|---|---|---|
| back (wall / open) | **−2.815** (wall) | **−3.094** (wall) | **−0.000** (wall) | −0.228 (open) | −0.236 (open) | +0.110 (open) |
| back_wall | – | – | – | −0.031 | +0.000 | −0.000 |
| front | +1.547 | +1.673 | +0.206 | +0.197 | +0.196 | +0.263 |
| left / right | +0.606 each | +0.665 each | +0.073 each | +0.032 each | +0.029 each | +0.132 each |
| bottom | +0.002 | −0.002 | −0.019 | −0.135 | −0.137 | +0.059 |
| top | +0.238 | +0.278 | −0.121 | −0.158 | −0.159 | −0.144 |
| sum open | +3.000 | +3.280 | +0.214 | −0.260 | −0.276 | +0.552 |
| solids (report "of which radiation") | +0.16 | +0.16 | +0.20 | −0.29 | −0.27 | +0.55 |

- The old full-wall wall T was 35.2 °C mean (zeroGradient, the warm air next to it) in a 29.02 °C room. As a black body it emitted 2.8–3.1 W net.
- Fix in `make_case.py`: the wall patch (`back` for `back: wall`, `back_wall` for a partial wall) gets its own `boundaryRadiationProperties` entry: `lookup`, emissivity 0, absorptivity 0, transmissivity 0. It is a perfect reflector, with zero net flux, the same as a re-radiating adiabatic wall in steady state. Open boundaries keep the black `".*"` default.
- New `radFlow_<patch>` function objects (areaIntegrate of qr) for every domain boundary patch. They are emitted only when the case has a boundary wall.
- `references/openfoam-case-notes.md`:
  - BC table row for the wall.
  - Radiation paragraph: fvDOM has 4·nPhi·nTheta rays, so the default is 36 rays, not 72. The comment written into `radiationProperties` still says 72; it is left so cases stay byte-identical.
  - Defect 7 with the numbers above.

## Task 2: domain energy gate and effect on results (c09983d)

`report.py` has a new gate, "Domain energy balance within 2 % (walls adiabatic)". It checks heat in = convection + conduction out (enthalpyFlow + condFlow) + radiation out through the open boundaries (+ cable ends). The wall is not a term in the balance; its net radiation is shown in the detail and should be 0. The gate is added only when `radFlow_*` data exist, so reports of device cases with `back: free` keep their numbers. The solids gate is unchanged.

| Run | Domain gate | Base °C | R K/W |
|---|---|---|---|
| plate-fin-coarse (old full wall; radFlow from postProcess on the copy) | **FAIL +30.8 %** (12.056 of 9.220 W) | 49.4 | 2.214 |
| plate-fin-normal (old full wall) | **FAIL +33.8 %** | 49.7 | 2.242 |
| plate-fin-coarse-radfix (full wall, fix) | pass +0.1 %, wall −0.000 W, all checks pass | 49.36 | 2.206 |
| plate-fin-backfoot-coarse (old, current asset) | pass +0.4 % (back_wall −0.031 W) | 51.3 | 2.413 |
| plate-fin-backfoot-coarse-radfix | pass +0.0 %, back_wall +0.000 W, all checks pass | 51.26 | 2.413 |
| plate-fin-backfoot-coarse-radfix-rays34 (test only) | pass +0.1 %, all checks pass | 50.30 | 2.308 |

New runs are in `.../validation/rijeka-plate-fin/cases/`: `plate-fin-coarse-radfix`, `plate-fin-backfoot-coarse-radfix`, `plate-fin-backfoot-coarse-radfix-rays34`. Their YAMLs are saved next to the cases and not committed:
- `validation-plate-fin-fullwall.yaml`: `back: wall`, 5 mm back clearance, a copy of the old case's case.yaml.
- `validation-plate-fin-backfoot.yaml`.
- `validation-plate-fin-backfoot-rays34.yaml`.

The fix changes R by −0.008 K/W (−0.07 K) on the full-wall case and by nothing on the sink-only asset. The full-wall wall's emission mostly left through the open boundaries; the low-emissivity parts absorbed little of it.

CHANGELOG [Unreleased] has a new "Fixed" section with both entries.

## Open-boundary radiation (the −0.29 W)

- **Warm outflow:** the open boundaries do radiate at their local inletOutlet T. The top boundary has 25 % of its area warmer than ambient, up to 42 °C. It emits about 0.13–0.15 W net into the domain: estimated 0.13 W from the face temperatures, measured −0.14 to −0.16 W in every run. Nearly all of it leaves through the other open boundaries. The parts (emissivity 0.05, small view factor) absorb well under 0.01 W of it, so it has no measurable effect on R.
- Separating the radiation temperature in v2412 is possible: `greyDiffusiveRadiation` takes `T <fieldName>`, so a fixed-ambient field could be loaded with readFields. It would change every case, so it was documented and left as is.
- **The real cause of the −0.29 W is the ray set.** fvDOM's nTheta spans 0–180°. With nTheta = 3 the middle band straddles the horizontal plane, so faces with a vertical normal see only 3/4 of the hemisphere: incident 354 W/m² vs 470–500 W/m² on vertical faces, measured from the VTK patch data.
- On a low-emissivity face, the reflected intensity is built from that 3/4 share, so about a quarter of the incident flux disappears into the face. That is about +80 W/m² of spurious absorption: the foam's top and bottom absorb +0.25 W each, the sink's ends +0.14 W each. The open boundaries feed it: the bottom boundary, all at ambient, emits −0.14 W net.
- Every balance still closes, so no gate sees it.
- With `radiation_rays: [3, 4]` the solids radiate +0.55 W out (hand calc +0.15 W; the paper says ≤ 5 %), the bottom boundary absorbs +0.06 W, and **R = 2.308 K/W (+1.2 % vs the measured 2.28) instead of 2.413 K/W (+5.8 %)**.
- The default was not changed: [3, 4] costs 1.33× the rays and changes every case and the published validation numbers. This is recorded as defect 8 in the notes (8edc4c1), as an open item for a decision.

## Regression

- `.github/regression.sh` (vs v0.1.0): every device case is "same", the plate-fin asset is "new"; exit 0.
- vs HEAD before 01-09: only `assets/validation-plate-fin.yaml` differs, in `constant/air/boundaryRadiationProperties` and `system/controlDict` (the radFlow function objects), as expected.
- vs 375bc98 after 01-06's commits: `case-meta.json` and `case.yaml` differ too, from 01-06's edit of the asset, not from this plan.

## Deviations from Plan

1. **[Rule 1 - Bug, documented, not fixed] Odd nTheta radiation loss** (see above). Fixing it means changing the default rays, which changes every case and the validation numbers. That conflicts with the byte-identity constraint, so it was measured (one extra coarse run), documented as defect 8, and left for a decision.
2. **[Rule 1 - Bug, docs] "72 rays" in the notes corrected to 36.** The generated comment in `radiationProperties` keeps the wrong number for byte-identity.
3. **Gate definition:** the plan's wording "out = convection + radiation through open boundaries + net through walls" would always close. The wall is instead treated as adiabatic (not a term), with its net flux shown, so the old run fails as required.
4. **Old runs checked via copies:** the old cases have no radFlow output. The gate was run on copies in `qr-measure/` with radFlow produced by postProcess at the final time, so the case directories stay read-only.

## Next Phase Readiness

- FIX-05 done; boundary walls cannot inject energy unnoticed.
- Decision needed: switch the default `radiation_rays` to an even nTheta ([3, 4]). Plate-fin R would go to about 2.31 K/W (coarse). Device cases with low-emissivity horizontal faces would change too, and every case would show a regression DIFF.
- SKILL.md step 5 does not list the new domain gate yet (not in this plan's files).
