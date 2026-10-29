---
phase: 01-baseline-and-validation-fixes
plan: 07
subsystem: report
tags: [make_report, docx, report-structure, measurements, SKILL.md, REP-03]

requires:
  - phase: 01-06
    provides: "air sections, velocity vectors, local-scale sink, measured vs CFD, --measurements"
  - phase: 01-09
    provides: "domain energy balance gate (documented in SKILL.md step 5 here)"
  - phase: 01-10
    provides: "plate-fin runs with the even ray default (plate-fin-rays-coarse/normal)"
provides:
  - "references/report-structure.md: six sections, figure-to-section table with conditions, reasons, sources"
  - "build_docx in that order: page 1 = verdict table + key figure sized to fit; sections numbered in the order present"
  - "report.camera_image, report.warmup: false, make_report.py --mesh-compare"
  - "SKILL.md: report structure, figure files, measurements:, --measurements, empty devices, domain gate"
affects: [every later report change (keep build_docx, main() and report-structure.md in step)]

tech-stack:
  added: []
  patterns:
    - "Page-1 key figure width computed from the height left under the table (estimate in cm), picture kept with its caption"

key-files:
  created:
    - references/report-structure.md
  modified:
    - scripts/make_report.py
    - scripts/hand_calc.py
    - SKILL.md
    - CHANGELOG.md
    - README.md

key-decisions:
  - "Sections numbered in the order present (no gap when section 4 is absent); headings keep their names"
  - "Key figure on page 1 = cfd-solids (cfd or ir style); without CFD the hand-calc temperature path. In ir style section 4 refers to Figure 1 and states its scale instead of repeating it"
  - "Section 4 appears with measurements, report.camera_image, or style ir after a CFD run; never as a hand-calc comparison (that is a check)"
  - "Time behaviour stays on by default (as before); report.warmup: false leaves out section 5, the warm-up sentence and the video"
  - "Simulation setup and limits moved into section 2 (Inputs and assumptions); Checks always present, with a no-CFD line for hand-calc-only reports"
  - "docs/cfd-result.png not regenerated: it is the IR comparison image and the ir style is unchanged"

duration: ~1.5h
completed: 2026-10-29
---

# Phase 01 Plan 07: Report Structure Summary

**Every report now reads answer first: page 1 has the verdict table and one key figure (sized to fit even with 16 devices), then Inputs and assumptions, Results, Comparison with measurement (only when something was measured or a camera comparison is asked for), Time behaviour, Checks. The rules and their reasons are in `references/report-structure.md`; SKILL.md points to it and documents `measurements:`, the figure files, empty `devices` and the domain energy gate.**

## Task Commits

| Task | Commit | Files |
|---|---|---|
| 1 Report structure and figure rules | 1be4056 (feat) | scripts/make_report.py, references/report-structure.md |
| Cosmetic hand-calc fix (from STATE todos) | 71fac1d (fix) | scripts/hand_calc.py |
| 2 Skill docs, changelog, README | a5b3047 (docs) | SKILL.md, CHANGELOG.md, README.md |

## Section order in the rendered PDFs (pdftotext)

Outputs under `/media/alexander/code/learning/48V_battery_switch_design/validation/rijeka-plate-fin/figure-style-check/`.

| Report | Sections | Figures by section |
|---|---|---|
| `0107-plate-fin` (plate-fin-rays-normal, cfd, `--measurements`, `--mesh-compare` coarse), 10 pages | 1 Result, 2 Inputs and assumptions (Simulation setup, Limits), 3 Results, 4 Comparison with measurement, 5 Time behaviour, 6 Checks (Mesh comparison) | 1: cfd-solids; 2: layout, assembly-3d; 3: temperature-path, cfd-sink-local, cfd-air-sections, cfd-velocity; 4: measured-vs-cfd + table; 5: warmup; 6: gates + mesh table (coarse base 50.30, normal 50.35 C, -0.05 K) |
| `0107-infineon-cfd` (fan, cfd), 10 pages | 1 Result, 2 Inputs and assumptions, 3 Results, 4 Time behaviour, 5 Checks | 1: cfd-solids; 2: layout, assembly-3d; 3: path, sink-local, air-sections, velocity; 4: warmup; no comparison section (no measurements, cfd style) |
| `0107-infineon-ir` (fan, ir), 8 pages | 1 Result, 2 Inputs and assumptions, 3 Results, 4 Comparison with measurement, 5 Time behaviour, 6 Checks | 1: cfd-solids in IR palette; 3: path, cfd-plume; 4: text naming Figure 1 and its scale (32.9-89.0 C, ambient + ir_floor_K to the hottest point); no measured-vs-cfd (no measurements) |
| `0107-example/report` (example-case coarse, 300 iterations, no measurements), 9 pages | 1 Result, 2 Inputs and assumptions, 3 Results, 4 Time behaviour, 5 Checks | as Infineon cfd; Checks has the "mesh comparison: not run" line |
| `0107-handcalc/report` (example YAML, no CFD, `report: {camera_image, warmup: false}`) | 1 Result, 2 Inputs and assumptions, 3 Results, 4 Comparison with measurement, 5 Checks | 1: temperature path (hand calc); 4: the camera image; no Time behaviour; Checks: "No CFD run" line |

Page 1 (viewed for all four CFD reports): title, date line, "1. Result", the verdict table (3 rows for the plate-fin, 2 for the example, 16 compact rows for Infineon), one paragraph (margin, check verdict, warm-up time), and Figure 1 with its caption. Section 2 starts on page 2 in every report.

## Regression and hash

- `.github/regression.sh 97c24e7` before any change: exit 0.
- After: exit 1, only `assets/validation-plate-fin.yaml` "DIFF (hand calc)", exactly the zero-device block (the repeated "Base under board ... R base-air" line becomes "R base-air ... (base under board 50.6 C, above)", the repeated "R_sink-air" line is dropped). All device cases and case files are "same".
- Package hash (`.github/package-hash.sh`): `7680275dc9d52dbed2bf49cd4405a5d4ef256362bd3fc3d4d12af09db0b74ba0`.

## Deviations from Plan

1. **[Rule 1 - Bug] Captions orphaned and page 1 overflow.** With the key figure at full width, its caption (plate-fin) or the whole figure (Infineon, 16 devices) fell onto page 2. Fix: top/bottom margins 2 cm, title 20 pt, the verdict, check and warm-up lines in one paragraph, a compact table above 6 rows, the figure width computed from the height left, and every picture kept with its caption.
2. **[Rule 1 - Bug] Limits bullet said "Air is laminar" for k-omega SST fan cases.** Now names SST when `airflow.turbulence` is set.
3. **[Rule 1 - Bug] Layout figure (a):** the dimension labels overlapped the tick labels, and the "air" arrow was clipped outside the axes. The data limits now include them (STATE todo).
4. **Additions to make the plan's conditions real:** `report.camera_image` (the plan names "a camera image path"; no such input existed), `report.warmup: false` (the documented way to leave out time behaviour) and `--mesh-compare` (the table lists "mesh comparison" under Checks; there was nothing to show it from).
5. **hand_calc.py cosmetic fix** (optional STATE todo): zero-device output only, see Regression.
6. **Third case:** the plate-fin coarse run's case.yaml already contains the thermocouples, so it cannot show a report without section 4. Used the Infineon cfd report and a new coarse example-case run (300 iterations, `0107-example/case`; its checks do not all pass at 300 iterations, which does not matter for the structure).
7. A scratch render folder `figure-style-check/0107-iter-infineon-cfd` is left behind (recursive delete outside /tmp is blocked).

## Phase 1 success criteria (ROADMAP)

1. Regression command: true (01-01).
2. Plate-fin with heat into the base, no heater: true; the ±3 % was replaced by the user's ±2u decision (01-08), result +1.2/+1.5 % (01-10).
3. SKILL.md emissivity and iteration guidance: true (01-02).
4. Turbo figures approved against Figs. 10-12: true (01-05 checkpoint).
5. Air sections, vectors, local-scale sink, measured vs simulated in the six-section structure: true (01-06 + this plan).
6. Back wall only behind the base: true; per-channel plumes only as short streaks that merge 15-20 mm above the sink (01-08, documented).

## Next Phase Readiness

- Phase 1 complete once the orchestrator updates STATE/ROADMAP. STATE todos closed here: empty `devices` in SKILL.md, layout label overlap, hand-calc repeated lines.
- The mesh table's column widths are not applied by LibreOffice (names wrap); the same holds for the other tables, so it was left.

---
*Phase: 01-baseline-and-validation-fixes*
*Completed: 2026-10-29*
