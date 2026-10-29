# Report structure

What goes where in the Word/PDF report (`scripts/make_report.py`), and when. The order is:
the answer first, then enough to reproduce it, then the evidence. Someone who reads only page 1
knows whether the design is safe and whether the CFD can be trusted. Someone who reads to the
end can rebuild the case and check every number.

## The six sections

| Section | Content and figures | Shown |
|---|---|---|
| 1 Result (page 1) | Verdict table (Tj and margin per device; without devices the base, board and sink temperature), one paragraph with the margin, the check verdict and the warm-up time, and one key figure: the CFD temperature of the solids (`cfd-solids.png`), or without CFD the temperature path from the hand calc | always |
| 2 Inputs and assumptions | Inputs table, the `# CHECK:` values from the YAML, layout and stack-up (`layout.png`), 3D assembly (`assembly-3d.png`), simulation setup table, limits | always |
| 3 Results | Temperature path (`temperature-path.png`), heat sink on its own scale (`cfd-sink-local.png`), air sections (`cfd-air-sections.png`), velocity vectors (`cfd-velocity.png`), heat balance table; style `ir`: the air section `cfd-plume.png` in place of the sink, section and vector figures | always; CFD figures only after a CFD run |
| 4 Comparison with measurement | Measured vs CFD plot (`measured-vs-cfd.png`) and table, absolute and relative to the reference point; thermal camera: the camera-palette view (page 1) with its scale stated, and the camera image itself | only with `measurements:` (or `--measurements`), `report.camera_image`, or `report.style: ir` after a CFD run |
| 5 Time behaviour | Warm-up curve (`warmup.png`), the lumped model's heat capacities, the heat-up video (`heatup.mp4`) | unless `report.warmup: false` |
| 6 Checks | Gates table from `report.py`; mesh comparison with `--mesh-compare <case>` (other runs of the same design on other meshes) | always; without CFD one line saying nothing checked the hand calc |

Sections are numbered in the order present: a report without measurements has five, and
"Time behaviour" is then section 4. The headings keep their names, so a reader finds the same
content under the same name in every report. Figure numbers follow the figures present, so a
figure left out leaves no gap.

## Why each rule

- **Answer first (section 1).** A design review reads page 1 and stops. It must carry the
  temperatures, the margin, whether the checks passed and one picture that shows where the heat
  is. The key figure is sized to the space left under the table, so it stays on page 1 even
  with 16 devices; section 2 always starts on a new page.
- **Inputs before results (section 2).** A result without its inputs cannot be reproduced or
  questioned. The assumptions the user has not confirmed (`# CHECK:`) and the model's limits
  belong next to the inputs, not at the end where they read like small print.
- **Air figures in the results (section 3).** The cooling happens in the air: boundary layers
  on the fins, warm channels, the plume, the bypass around the sink. A report that shows only
  the solids hides why they have that temperature. The figures follow the types in Kirinčić et
  al. 2025 (Thermo 5, 57): air temperature sections (Figs. 10/11), the sink on a local scale
  (Fig. 12), velocity vectors at mid fin height (Fig. 13). One velocity plane is enough for
  free convection, where the flow is one plume. For a fan the vectors are always shown, since
  the bypass decides how much air the channels get. Section (b) of the air sections carries flow
  arrows in both cases.
- **Comparison only with real measurements (section 4).** A comparison needs something
  measured. Without it the section is left out, rather than filled with a comparison against
  the hand calc (that one is a check and sits in section 6). With a thermal camera, the CFD
  view must use the camera's palette and scale (`report.style: ir`, `ir_range`), otherwise
  equal temperatures look different. Measured points are compared absolutely and relative to a
  reference point: the relative comparison tests the shape of the temperature field apart from
  the overall thermal resistance (Kirinčić et al. 2025, Figs. 8-9).
- **Time behaviour by default (section 5).** The warm-up costs seconds (a lumped model
  calibrated to the steady result), and "how long until it is hot" is the next question after
  "how hot". It is left out only for a pure steady answer (`report.warmup: false`), which also
  skips the video. This keeps the behaviour of earlier versions, which always included it.
- **Checks always (section 6).** A CFD temperature is only as good as its energy balances, its
  settling and its agreement with the hand calc. The gates table is in every CFD report, and a
  hand-calc-only report says that nothing checked it. A number that goes into a decision needs a
  second mesh (SKILL.md step 6); `--mesh-compare` puts that comparison next to the gates.

## Colour

CFD figures use Turbo, the blue-to-red order of the Fluent rainbow in CFD papers but with
smoothly changing lightness. A rainbow without that property puts false edges into a smooth
field (Kovesi 2015). The thermal-camera palette is used only where a camera image is the
comparison (`report.style: ir`).

## Sources

- Report practice in CFD courses and validation write-ups: the CFD report guide of Wrocław
  University of Science and Technology (problem, model, mesh and boundary conditions, results,
  validation, conclusions) and SimScale's validation cases (setup, result plots, comparison with
  the reference, mesh study).
- Kirinčić, M., Trp, A., Lenić, K. (2025). Thermo 5, 57. Plate-fin heat sink in free
  convection; figure types for the air, the sink and the comparison with thermocouples.
- Kovesi, P. (2015). Good colour maps: how to design them. arXiv:1509.03700.

## Where it is in the code

`build_docx()` in `scripts/make_report.py` writes the sections in this order. `main()` decides
which figures exist (style, CFD run, measurements, `report.warmup`, `report.camera_image`,
`--mesh-compare`). A change to the order or a condition goes into both places and into this
file.
