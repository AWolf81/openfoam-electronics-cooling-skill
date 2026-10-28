---
phase: 01-baseline-and-validation-fixes
plan: 06
subsystem: report
tags: [make_report, cooling_model, figures, validation, measurements, pyvista, REP-02]

requires:
  - phase: 01-05
    provides: "cfd figure style helpers (cfd_cmap, cfd_add, cfd_colorbar, _cfd_arrows), 2.5x render, 200 dpi"
  - phase: 01-08
    provides: "plate-fin model with the wall behind the sink + foam; normal-mesh case plate-fin-backfoot-normal"
provides:
  - "fig_air_sections: (a) mid fin height (normal x), (b) vertical through a channel centre, global scale, arrows in (b)"
  - "fig_velocity: equal-length arrows coloured by speed at mid fin height (like Kirincic Fig. 13)"
  - "fig_sink_local: isometric heat sink on its own scale (like Fig. 12)"
  - "optional measurements: list in the YAML; fig_measured_vs_cfd + table (absolute and relative to a reference point)"
  - "make_report.py --measurements YAML (measured points for a case that was run before they were added)"
affects: [01-07 docs (SKILL.md: measurements:, new figures, --measurements), README validation section]

tech-stack:
  added: []
  patterns:
    - "_render_section: parallel camera framed exactly on a window in mm, so matplotlib overlays (arrows) use the same mm axes"
    - "docx figures numbered automatically in the order present"

key-files:
  created: []
  modified:
    - scripts/make_report.py
    - scripts/cooling_model.py
    - assets/validation-plate-fin.yaml

key-decisions:
  - "cfd style: cfd-plume.png removed; section (b) of cfd-air-sections.png replaces it (ir style still renders cfd-plume, unchanged)"
  - "Section (b) goes through the channel centre nearest the heat sources (devices, or board centre), +0.37 mm off grid faces"
  - "Velocity figure: white air, grey solids, equal-length arrows coloured by |U| (Turbo, 0 to the fastest arrow), one column per channel centre"
  - "measurements: one entry may be reference: true; the report then also compares T - T_ref (tests the distribution apart from R)"
  - "Plate-fin thermocouples on fin 1 (second from the side, Fig. 2a), at mid-thickness; TCb 0.5 mm into the base at y 61.5, z 90"

duration: ~1.5h
completed: 2026-10-29
---

# Phase 01 Plan 06: New Figures Summary

**The report now shows the air and the flow, and checks against measured points. It has two air sections like the paper's Figs. 10/11, velocity vectors at mid fin height like Fig. 13, and the heat sink on a local scale like Fig. 12. With `measurements:` in the YAML it also plots measured vs CFD with error bars and adds a table. Plate-fin: the CFD runs +1.45 to +1.55 K above all five thermocouples, which is the known +6 % in R. Relative to the base thermocouple TCb, the CFD matches the measured temperature distribution within -0.02 to +0.08 K (4 of 4 points inside the ±0.28 K combined uncertainty).**

## Tasks

| Task | Commit | Files |
|---|---|---|
| 1 Air sections, velocity vectors, local-scale sink | eec5f0d | scripts/make_report.py |
| 2 Measured vs simulated | fb382b9 | scripts/cooling_model.py, scripts/make_report.py, assets/validation-plate-fin.yaml |

## New figures

Plate-fin (free convection, normal mesh, `.../validation/rijeka-plate-fin/cases/plate-fin-backfoot-normal`), report in `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/0106-plate-fin/` (thermal-report.docx/.pdf, heatup.mp4):
- `figures/cfd-air-sections.png`: (a) x = 21 mm. Boundary layers on all 11 fins, uniform warm channels, short streaks above each channel that merge ~15-20 mm above the sink into one plume (as documented in 01-08; rendered as computed). (b) y = 56 mm, channel centre: plume straight up, entrainment from both sides, the foam block behind the base.
- `figures/cfd-velocity.png`: up to 0.24 m/s. Fastest flow in the outer channels and above the sink; inflow from the sides below the sink.
- `figures/cfd-sink-local.png`: 50.84-51.47 °C. Hot at the top of the base, coolest at the bottom fin tips, outer fins cooler (as in Fig. 12).
- `figures/measured-vs-cfd.png`: absolute and relative to TCb.

Infineon fan case (`cases/noisl-cu50-sink-2p4ms-sst`, `--style cfd`), report in `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/0106-infineon/`:
- `figures/cfd-air-sections.png`: (a) x = 9 mm, the wakes behind the fin ends. (b) y = 50 mm, the jet onto the fin tips splits above and below the sink. The bypass around the sink and the warm wake are visible. White at the bottom of the window is outside the domain (50 mm below clearance).
- `figures/cfd-velocity.png`: up to 2.9 m/s. Inside the channels the flow splits up and down from the stagnation line at about mid-length. Around the sink, fast bypass at ~2.5-2.9 m/s.
- `figures/cfd-sink-local.png`: 71.9-79.2 °C, hot spot under the FET rows.

## Measured vs CFD (plate-fin, normal mesh)

| Point | Model point (x, y, z mm) | Measured °C (±0.2) | CFD °C | Δ K | Meas. − TCb | CFD − TCb | Δ K |
|---|---|---|---|---|---|---|---|
| TCb | (0.5, 61.5, 90) | 50.00 | 51.46 | +1.46 | ref | ref | - |
| TC1 | (7, 13.5, 50) | 49.80 | 51.29 | +1.49 | −0.20 | −0.17 | +0.03 |
| TC2 | (21, 13.5, 50) | 49.70 | 51.15 | +1.45 | −0.30 | −0.32 | −0.02 |
| TC3 | (35, 13.5, 1) | 49.40 | 50.86 | +1.46 | −0.60 | −0.60 | +0.00 |
| TC4 | (35, 13.5, 99) | 49.60 | 51.15 | +1.55 | −0.40 | −0.32 | +0.08 |

- Absolute: +1.45 to +1.55 K, 0 of 5 within ±0.2 K. This is expected. The experiment held the base at 50.0 °C, while our model puts in the measured 9.22 W, so the whole field sits higher by the R excess (+6.2 %, 22.4 vs 21.0 K rise).
- Relative to TCb: −0.02 to +0.08 K, all 4 within ±0.28 K (the two readings' ±0.2 K combined).
- TCb position sensitivity: the paper does not give its depth. In the CFD, the base 0.5 mm from the contact face at y 61.5 reads 51.27 °C at z 10, 51.39 at z 50 and 51.46 at z 90. With TCb at z = 50 instead of 90, all relative CFD values shift by +0.07 K, and TC4 would be +0.15 K, still inside ±0.28 K.

## Verification

- make_report.py on both cases exits 0; every new PNG was viewed. Fins, plumes, boundary layers and the bypass are visible and not clipped.
- `.github/regression.sh` (vs v0.1.0) exit 0. All cases "same", and the plate-fin asset is "new". At the time of the run, 01-09's working-tree changes to make_case.py were present; no DIFF appeared.
- The plate-fin hand calc is byte-identical before and after adding `measurements:`.
- Bad `measurements:` forms raise clear errors: point and part both missing, a point_mm of the wrong length, an unknown stat, a non-list.

## Deviations from Plan

1. **[Rule 1 - Bug] Colour bar mislabelled steps of 0.025.** It printed 0.03, 0.05, 0.08. `cfd_colorbar` now adds decimals until the inner ticks print exactly. Existing ranges keep their decimals. (eec5f0d)
2. **[Rule 1 - Bug] LibreOffice hung with a relative `--out`.** The private profile path went into a `file://` URL relative to the working directory, and soffice timed out after 300 s. The path is now absolute. (eec5f0d)
3. **[Rule 3 - Blocking] `--measurements YAML` option.** The finished plate-fin case's `case.yaml` predates the thermocouples, and cases are read-only. The option reads only the `measurements:` list from another YAML.
4. **Schema addition `reference: true`.** At most one entry; it gives the T − T_ref comparison requested by the orchestrator. It is not in the plan's field list.
5. **docx figure numbers are now automatic.** They were hard-coded "Figure N"; the new figures would have broken the numbering.
6. The velocity window is tighter than the temperature sections: half a sink length below and 0.7 above. This keeps the arrows readable at print size.

## Next Phase Readiness

- 01-07 docs: SKILL.md should describe `measurements:` (incl. `reference`, `part`/`stat`), `--measurements`, the new figure files (cfd-air-sections, cfd-velocity, cfd-sink-local, measured-vs-cfd) and say that the cfd style no longer writes cfd-plume.png. The README validation section could add the TC table.
- In a device case, section (b) passes through a channel centre near the devices and does not necessarily cut a device. For the Infineon case it cuts two packages at y = 50.
