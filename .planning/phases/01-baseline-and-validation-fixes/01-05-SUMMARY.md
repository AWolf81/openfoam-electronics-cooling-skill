---
phase: 01-baseline-and-validation-fixes
plan: 05
subsystem: report
tags: [make_report, figures, turbo, pyvista, matplotlib, REP-01]

requires:
  - phase: 01-04
    provides: "full Word/PDF/video report for zero-device cases (plate-fin validation case)"
provides:
  - "report.style cfd (default): Turbo, point-interpolated, 256 levels, paper-style legend, global/local scales"
  - "sharp still figures: 2.5x render, 200 dpi, fonts sized for print width"
  - "vertical section laid out like Kirincic et al. 2025 Fig. 11, with vector flow arrows"
  - "report.style ir unchanged (byte-identical) for thermal-camera comparisons"
affects: [01-06, 01-07 report rework and docs]

tech-stack:
  added: []
  patterns:
    - "CFD_RENDER_SCALE / CFD_DPI / CFD_LINE_PX: render scale applied to window size and line widths together; fonts scaled per figure for its print width"
    - "Flow arrows drawn by matplotlib quiver over the rendered image (axes in mm), velocity sampled from the 3D air volume"
    - "ir code paths untouched; shared helpers take new parameters with defaults equal to the old behaviour"

key-files:
  created: []
  modified:
    - scripts/make_report.py
    - assets/example-case.yaml
    - SKILL.md

key-decisions:
  - "Colour map Turbo (not the Fluent rainbow, not inferno): same blue-to-red order as the paper, smooth lightness, no false edges"
  - "256 levels (continuous) by default; report.cfd_levels: 64 for visible bands"
  - "Legend left, vertical, 'Temperature [°C]', ~11 round ticks plus labelled ends, 2 decimals under 2 K"
  - "Scales: air section and video ambient to hottest (global); 3D solids coldest to hottest solid, labelled 'local scale' (like paper Fig. 12)"
  - "Still cfd figures: render 2.5x, save at 200 dpi, outlines scaled with the render; video stays at scale 1"
  - "Vertical section window: centred on the sink, one sink length of air below and above, ~60 mm beside; white where the domain has no air"
  - "Arrows: white with a thin dark outline, equal length (direction only), grid every window height / 36 (~8 mm for a 100 mm sink)"

duration: ~1h (continuation after the checkpoint)
completed: 2026-10-28
---

# Phase 01 Plan 05: Figure Style Summary

**The CFD figures now use Turbo with smooth 256-level fields and a paper-style legend on the left. They are rendered at 2.5x and saved at 200 dpi: cfd-solids grew from 2080x910 to 3200x1400 px, and the legend ticks print at about 9.5 pt. The vertical section is laid out like the paper's Fig. 11, with sharp vector arrows. The IR style is byte-identical to before.**

## Performance

- **Tasks:** 3/3 (Task 1 before the checkpoint, Task 2 human-verify with feedback, Task 3)
- **Files modified:** 3

## Accomplishments

- Task 1 (42ad72e): shared CFD style.
  - `report.style: cfd | ir`, with cfd as the default and `3d` accepted as its old name.
  - Turbo with point data and `interpolate_before_map`, unlit, black feature edges.
  - Legend as in the paper.
  - Local scale for the 3D solids and the global scale for the section and the video.
- Task 2 (checkpoint) feedback, applied in 340f104:
  - **Sharper figures.**
    - cfd-solids: views rendered at 2500x2050 instead of 1000x820, outlines 3 px instead of 1.2 px, fonts x2.3, 200 dpi.
    - cfd-plume: 2.5x render, fonts x1.5, 200 dpi.
    - Word inserts the images at the same widths as before (16.5 cm and 13 cm), so the pixel density is higher and the print size unchanged.
  - **Section laid out like Fig. 11.**
    - The window is centred on the heat sink, with one sink length of air below and above and about 60 mm beside it.
    - The plate-fin case has only 5 mm of back clearance. That side stays white, not stretched and not filled with fake air.
    - The panel is centred in the figure, with the legend on the left and a clear gap to the plot.
  - **Arrows kept and made sharp.**
    - They are now matplotlib quiver arrows (shaft and head) drawn as vectors over the render.
    - Velocity is sampled from the 3D air volume on a regular grid. Points in solids or still air are skipped.
    - Colour: white with a thin dark outline (#1a1a1a, 0.3 pt). It reads on the dark ambient air, on the hot plume and next to the red solids.
- Task 3 (e71bcc9): SKILL.md report section.
  - cfd is the default; ir is only for camera comparisons.
  - `ir_range: [lo, hi]` in °C gives a fixed scale; leaving it out gives the automatic range from ambient plus `ir_floor_K` to the hottest point. The code does not accept `camera` as a value.
  - `3d` is described as the old name for cfd.

## User feedback at the checkpoint

1. "I think color scale is OK, but can we increase resolution?" Agreed reading: keep Turbo and the scale rules, and make the figures sharper (blurry text and edges, tiny legend text). Done as above.
2. Lay out the vertical section like Fig. 11: sink centred, air around it, legend on the left with a gap, white padding instead of fake air, colour scale unchanged. Done.
3. Keep the arrows but make them sharp: proper glyphs that scale, visible on dark and red, a regular grid, none inside solids. Done.

## Figure pixel sizes (cfd style)

| Figure | Before (42ad72e) | After |
|---|---|---|
| cfd-solids.png | 2080x910 (130 dpi, 1000x820 renders) | 3200x1400 (200 dpi, 2500x2050 renders) |
| cfd-plume.png | 832x1235 (130 dpi, 1500x2000 render) | plate-fin 1648x1620, Infineon 1760x1620 (200 dpi, render 2.5x the old window height, width to fit the window) |
| heatup.mp4 | unchanged | unchanged (scale 1) |

layout, assembly-3d, temperature-path and warmup are shared with the IR style and were left unchanged (160 dpi).

## Report size

| Report | docx before / after | pdf before / after |
|---|---|---|
| plate-fin cfd | 1.01 MB / 1.75 MB | 0.64 MB / 0.80 MB |
| Infineon cfd | 1.1 MB / 2.0 MB | 0.76 MB / 0.98 MB |
| Infineon ir | 0.62 MB (unchanged) | 0.74 MB (unchanged) |

## IR byte identity

The IR figures rendered by 42ad72e were copied to `figure-style-check/infineon-ir-before/`. After the change, the report was re-rendered with `--style ir`. All six PNGs and heatup.mp4 are byte-identical (`cmp`). This was checked twice: after the resolution change and again after the section and arrow changes.

## Verification

- Renders, all exit 0:
  - plate-fin-coarse with `--style cfd`
  - Infineon noisl-cu50-sink-2p4ms-sst with `--style cfd`
  - Infineon with `--style ir`
- Output folder: `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/` (plate-fin-cfd, infineon-cfd, infineon-ir).
- compare.py: savefig dpi 90 -> 150; mid-height section window 900x1200 -> 2250x3000. compare-plate-fin.png is now 1890x2737.
- `.github/regression.sh` exit 0.

## Deviations from Plan

1. **[Rule 1 - Bug] The air section could not sample velocity.** Probing the 2D slice gave no valid points (vtkValidPointMask all 0). The arrows sample the 3D air volume at the section's y instead. Commit 340f104.
2. **Arrow spacing about 8 mm, not 3-4 mm.** A 4 mm grid over the 3-sink-length window gave about 75 rows of specks that could not be read at print size. The default is window height / 36 (at least 3 mm), and `_cfd_arrows` takes `spacing=` for a denser grid in a zoomed view.
3. Task 2 follow-up and the user's two later requests went into one commit (340f104). They change the same functions.

## Next Phase Readiness

- The arrow grid density may need a user decision (8 mm now; 3-4 mm was mentioned).
- The new SKILL.md paragraph says still figures render at 2.5x and 200 dpi. Keep it in step if CFD_RENDER_SCALE or CFD_DPI change.
