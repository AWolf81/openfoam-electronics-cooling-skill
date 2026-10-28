# OpenFOAM case notes (v2412, ESI / openfoam.com)

How the generated case is put together, why each choice was made, and what to do when it
misbehaves. Every dictionary in `make_case.py` was checked against the v2412 tutorials
(`heatTransfer/chtMultiRegionSimpleFoam/multiRegionHeaterRadiation`, `cpuCabinet`,
`chtMultiRegionFoam/externalSolarLoad`, `buoyantSimpleFoam/hotRadiationRoomFvDOM`) and run.

## Contents

1. Case layout and patch names
2. Boundary conditions and why
3. Defects this setup has had (read before changing BCs or solver settings)
4. Troubleshooting by symptom
5. Transient fallback
6. Editing a generated case by hand
7. Viewing results
8. Foundation OpenFOAM (openfoam.org) differences

## 1. Case layout and patch names

```
case.yaml               copy of the input
case-meta.json          hand calc, powers, expected cells per region, grid breakpoints
CACHEDIR.TAG            marks the case as re-runnable: backups with --exclude-caches skip it;
                        make_report.py puts the report and config copies in ../<case>-report/
Allrun / Allclean       run inside the container: scripts/of.sh <case> ./Allrun
system/blockMeshDict    one block, multi-graded so grid lines fall on every solid edge
system/topoSetDict      one cellZone per region (boxToCell), air = the rest
system/<region>/        fvSchemes, fvSolution, decomposeParDict, fvOptions (devices)
system/air/setExprFieldsDict   hydrostatic initial p (see section 3)
constant/<region>/      thermophysicalProperties, radiationProperties, (air) turbulenceProperties
0/<region>/             T, p (+ U, p_rgh, IDefault in air)
postProcessing/<region>/<function>/<startTime>/*.dat
```

Regions: `air` (fluid), `heatsink`, `ims`, one per device. `splitMeshRegions` names the
interfaces `<region>_to_<neighbour>`: `air_to_heatsink`, `heatsink_to_air`, `heatsink_to_ims`,
`ims_to_q1`, `q1_to_ims`, ... Outer patches (`back front left right bottom top`) stay with the air.
With `heatsink.back: {wall: footprint}` (or a `{wall: {y_mm, z_mm}}` rectangle) the faces of
`back` inside the rectangle become a wall patch `back_wall` (topoSet faceSet `backWallFaces` +
`createPatch -overwrite`, before `splitMeshRegions`); the rectangle edges are grid lines, so the
split is exact. `back: wall` keeps the whole `back` patch as a wall, as before.

Coordinates: z up (gravity -z), fins along z, y across the fins, x out of the fins; IMS and
devices at x < 0 on the back of the base.

## 2. Boundary conditions and why

| Where | Field | Condition | Why |
|---|---|---|---|
| whole air region | hRef | top boundary height (`constant/hRef`, `constant/air/hRef`) | p_rgh equals the static pressure at the top, so warm air can leave there (defect 4) |
| open boundaries | p_rgh | `totalPressure`, p0 1e5 | p_rgh is uniform in still isothermal air, so a uniform p0 is the undisturbed room |
| open boundaries | U | `pressureInletOutletVelocity` | lets air enter and leave wherever the plume wants |
| open boundaries | T | `inletOutlet`, inletValue = ambient | entering air is at ambient, leaving air carries its own temperature |
| open boundaries | IDefault | `greyDiffusiveRadiation`, emissivity 1 | the room radiates as a black body at the boundary temperature |
| wall on the domain boundary (`back` with `back: wall`, `back_wall`) | IDefault | `greyDiffusiveRadiation`, own `boundaryRadiationProperties` entry with emissivity 0 (perfect reflector) | an adiabatic wall has zero net radiative flux; under the black `".*"` default it emitted at its own temperature (defect 7) |
| air side of solids | T | `compressible::turbulentTemperatureRadCoupledMixed`, `kappaMethod fluidThermo`, `qr qr` | conjugate coupling; the fluid side adds the radiative flux |
| solid side | T | same type, `kappaMethod solidThermo`, `qrNbr qr` on `*_to_air` | picks up the air side's radiative flux |
| solid-solid | T | same type with `thicknessLayers` / `kappaLayers` | `board.layers_under_parts` on device-board, `board.layers_to_sink` on board-sink, without meshing 10-100 um layers |
| air side of solids | U, p_rgh | `noSlip`, `fixedFluxPressure` | standard buoyant wall |

Radiation: `fvDOM` in the air with `absorptionEmissionModel none` (transparent air), solved
every 10 iterations. In 3D fvDOM makes 4 nPhi x nTheta rays, nPhi over each 90 degrees of
azimuth and nTheta over the whole 0-180 degrees of polar angle, so the default [3, 3] is 36 rays
(the comment written into `radiationProperties` says 72; it is wrong, left so existing cases stay
byte-identical). Surface emissivities in `constant/air/boundaryRadiationProperties`: `".*"` black
(emissivity 1) for the open boundaries, `lookup` per `air_to_<solid>` patch, emissivity 0 for a
wall on the domain boundary. Solids have `radiation off`; they only exchange through the coupled
patches. Cases with a wall on the domain boundary also write `radFlow_<patch>` (integral of qr,
positive = leaving the air) for every domain boundary patch; `report.py` uses them for the domain
energy balance.

With nTheta odd (the default 3) the middle polar band straddles the horizontal plane, so faces
with a vertical normal (tops and bottoms of parts, the top and bottom boundaries) see only 3/4 of
the hemisphere: their incident radiation is 0.75 of the true value (measured: 354 vs 470-500 W/m2
on vertical faces in a room at 29 C). For black faces this only scales the exchange by 0.75. For
low-emissivity faces it is worse: the reflected intensity is built from the 0.75 share, so a
quarter of the incident flux vanishes into the face as spurious absorption, about +80 W/m2 into
a horizontal face with emissivity 0.05 (plate-fin, see defect 8). An even nTheta (e.g.
`radiation_rays: [3, 4]`) puts a band boundary in the horizontal plane.

Heat sources: `scalarSemiImplicitSource` on `h`, `selectionMode all`, `volumeMode absolute`,
in `system/<device>/fvOptions`. The value is W for the whole region.

Air: `heRhoThermo`, perfect gas, constant mu and Pr = 0.71 at the hand-calc film temperature,
laminar. Solids: `heSolidThermo`, `constIso`.

## 3. Defects this setup has had

Each of these produced a plausible-looking number before it was caught. They are why the
report has the sanity gates.

1. **`prghTotalPressure` on open boundaries drove a downdraft.** It takes p0 as *static*
   pressure, which removes the hydrostatic head at the boundaries; air fell through the domain
   at 3.5 m/s and the sink came out 70 % too cool. Use `totalPressure` on p_rgh.
2. **Uniform initial p diverged in 4 iterations.** chtMultiRegionSimpleFoam recomputes
   `p_rgh = p - rho*gh` at start-up, so a uniform p puts the air several Pa out of hydrostatic
   balance; the steady solver blows up (continuity errors of order 10, rho clamped). Fix:
   `setExprFields -region air` sets `p = 1e5 - rho_amb*g*z` before the solver starts.
3. **Solids starting at ambient took > 10 000 iterations to warm up.** A solid touching only
   coupled patches has a free mean temperature that partial solves (relTol 0.1) converge very
   slowly. Fix: start solids at their hand-calc temperatures and solve h fully each iteration
   (`relTol 0`, relaxation 1). With both, the example's solids settle in about 500-900 iterations.
4. **Pressure reference at z = 0 blocked the plume (hRef).** p_rgh = p - rho*g*(z - hRef). With
   hRef = 0, the fixed p_rgh on the top boundary 0.5 m up misstates the static pressure of warm
   air by (rho_amb - rho)*g*z_top, about 0.1 Pa, while the plume's whole buoyancy head is about
   0.04 Pa. The plume could not leave through the top, came out of the sides, air entered at
   the top, the p_rgh residual stalled near 1e-1 and the air carried only ~1.5 W of the ~5.6 W
   convected heat out. The solid temperatures were still within 2 % of the hand calc and every
   solid-side gate passed, so only the air energy gate showed it. Running transient did not
   help (same imbalance). Fix: `constant/hRef` and `constant/air/hRef` at the top boundary
   height, and the hydrostatic start written relative to it. After the fix the plume leaves at
   the top (2.3 g/s), the residual falls below 1e-4 and the air balance closes (5.67 vs 5.64 W).
5. **Write interval must divide the iteration count.** OpenFOAM writes only on multiples of
   `writeInterval`, never automatically at `endTime`; a 1200-iteration run with interval 500
   had no final fields, so reconstruction and the VTK export silently used old or empty data.
   The generator picks an interval that divides the count. Function objects that write fields
   (gradT, wallHeatFlux) create time directories of their own; gradT therefore writes only at
   regular write times.
6. **Plumbing:** the top-level `system/fvSchemes` must contain the (empty) sub-dictionaries or
   `splitMeshRegions` fails; `decomposePar -allRegions` needs `system/<region>/decomposeParDict`;
   OpenFOAM does not write the final time unless it falls on `writeInterval` (so the generator
   caps the interval at the iteration count); the image's entrypoint changes directory, so
   `of.sh` does `cd /case` itself.
7. **A black adiabatic wall on the domain boundary made energy (FIX-05).** The default
   `boundaryRadiationProperties` entry `".*"` (emissivity 1) also covered the wall patch `back`
   (`heatsink.back: wall`). Its T is zeroGradient, so it took the temperature of the warm air
   next to it (35 C mean in a 29 C room) and emitted as a black body: net qr through it
   -2.81 W (coarse) / -3.09 W (normal) in the plate-fin case with 9.22 W heat input; the open
   boundaries took 3.00 / 3.28 W out by radiation. The solids' balance cannot see this (the
   solids lost 9.22 W either way). Fix: the wall patch (`back` or `back_wall`) has its own
   entry with emissivity 0, absorptivity 0 (a perfect reflector: zero net flux, the same as a
   re-radiating adiabatic wall in steady state). Measured after the fix (plate-fin full wall,
   coarse): wall -0.000 W, open boundaries +0.21 W = the 0.20 W the solids radiate; base
   49.4 C, R 2.206 K/W (2.214 before). The sink-only wall (`back_wall`, 123 cm2) had given only
   -0.03 W. `report.py` now balances the whole domain (heat in = convection + radiation out of
   the open boundaries; walls adiabatic) from `radFlow_<patch>`: the old run fails it at
   +30.8 % (12.06 W out of 9.22 W), the fixed run passes at +0.1 %. Open boundaries stay black
   at their T: where warm plume air leaves (top, 25 % of its area warmer than ambient, up to
   42 C) they emit about 0.15 W more than a room at ambient would; it nearly all leaves again
   through the other open boundaries, and the parts (emissivity 0.05, small view factor) absorb
   well under 0.01 W of it, so it is left as is (separating the radiation temperature would
   need an extra field read through `T Tname` on `greyDiffusiveRadiation` and would change
   every case).

## 4. Troubleshooting by symptom

| Symptom | Look at | Usual cause and fix |
|---|---|---|
| `Allrun: step failed: ...` | the matching `log.<step>` | read the first `FOAM FATAL` block |
| cells per region differ from `make_case.py`'s print | `log.splitMeshRegions` | a box face missed a grid line; check `grid_breakpoints_mm` in case-meta.json |
| `Min/max rho: 0.5 2` and huge continuity errors | `log.chtMultiRegionSimpleFoam` | divergence; check the hydrostatic start ran (`log.setExprFields`), lower `U`/`h` relaxation to 0.2 |
| air speed > 1 m/s, mass in at the top | report gates, `postProcessing/air/massFlow_*` | open-boundary pressure condition (defect 1) |
| air hotter than any solid | report gates | unbounded convection scheme on a coarse mesh: use `bounded Gauss upwind` for `div(phi,h)`, or refine |
| energy balance off by > 2 % and still moving | `airWallHeatFlux` series | not converged: rerun the same Allrun (startFrom latestTime) or raise `endTime` |
| balance off but flat | `fvOptions` power vs case-meta.json | a source not applied (wrong region name) or heat leaving through a patch you did not expect |
| heat flow oscillates and never settles | `airWallHeatFlux` series | unsteady plume; report the mean and band, or go transient (section 5) |
| `of.sh: no Docker daemon reachable` | `docker info` | start Docker Desktop or the docker service |

## 5. Transient mode

`--mode transient` (or `solver.mode: transient`) writes a `chtMultiRegionFoam` case: Euler time
stepping, PIMPLE (1 outer, 2 pressure correctors, momentum predictor), `adjustTimeStep` with
`maxCo 0.8`. Two deliberate choices:

- **Solid heat capacity scaled by `solid_inertia_scale` (default 0.01).** A 150 x 200 mm sink
  has a thermal time constant of about 15 minutes; scaled, it settles in seconds. Density only
  enters a solid's heat capacity, so the steady answer is unchanged.
- **`maxDi 10000`.** Solids are solved implicitly; the diffusion number only limits how
  accurately their warm-up is followed, which the scaling already gave up. With `maxDi 10` and
  scaled solids the step fell to 0.2 ms; with the relaxed limit it is Courant-bound at ~8 ms.

Start from a converged steady case with `--init-from` (same YAML and resolution, checked through
the expected cell counts); the run then only has to settle, and 20 s of simulated time is
enough for the example (plume transit ~3 s, scaled sink time constant ~8 s). The report's gates
read the end of the run. For a real warm-up curve or a load profile, use scale 1 and a run
several time constants long.

## 6. Editing a generated case by hand

Change the YAML and regenerate whenever you can; hand edits are lost on regeneration. If you
must: powers in `system/<device>/fvOptions`; emissivities in
`constant/air/boundaryRadiationProperties`; layers in `0/<region>/T` on the interface patch,
on *both* sides; mesh density through `mesh.resolution` in the YAML (the far-field growth and
cell counts per span are in `RES` in make_case.py).

## 7. Viewing results

`case.foam` opens all regions in ParaView (choose "Decomposed" or "Reconstructed" case type);
`VTK/` holds the latest time per region from `foamToVTK`. Useful views: T on a y-normal slice
through the devices, U on the same slice (the plume), T on the IMS and sink surfaces.

## 8. Foundation OpenFOAM (openfoam.org) differences

This skill targets ESI v2412. The Foundation line (v11+) replaced `chtMultiRegionSimpleFoam`
with `foamMultiRun` plus solver modules (`fluid`, `solid`), moved `fvOptions` to
`fvModels`/`fvConstraints`, and renamed several keywords. Do not mix dictionaries from the two
lines; if a user has Foundation OpenFOAM installed, run this skill's Docker image instead.
