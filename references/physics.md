# Physics behind the hand calculation

What `scripts/cooling_model.py` computes, why, and where it stops being right. Read this when
the CFD and the hand calc disagree, or when a user asks how a number was obtained.

## Contents

1. Losses
2. Thermal network
3. Free convection in the fin channels
4. Outside surfaces
5. Radiation
6. Spreading resistance
7. Layers above and below the spreader
8. Typical values
9. When the hand calc is not enough

## 1. Losses

Conduction loss per conducting device: `P = I^2 * Rds(on)(Tj)`, with Rds(on) linear in Tj
through the 25 C value and the datasheet's normalised factor at 125 C. The model iterates
P <-> Tj to a fixed point, so a hot device is charged its hot resistance. Use the datasheet
*maximum* Rds(on); typical values understate loss by 15-30 %.

Back-to-back (common-source) MOSFETs used as a bidirectional switch: both carry the full
current, so the pair dissipates `2 * I^2 * Rds(on)`. Paralleled devices share current:
model each with its share of the current (or give `power_W` per device). Switching loss is
added per device as a constant if given.

## 2. Thermal network

```
Tj = T_case + P_i * Rth(j-c)
T_case = T_ims_back + P_i * (R_layers_i + R_spread_ims_i)
T_ims_back = T_base_under_ims + P_tot * R_tim
T_base_under_ims = T_sink + P_tot * R_spread_base
T_sink = solve  P_tot = Q_conv(T_sink) + Q_rad(T_sink)
```

The sink is treated as isothermal at `T_sink` for convection and radiation; the spreading
resistance adds the hot spot under the IMS. That split is standard and good to ~10 % for
bases thicker than ~5 mm.

## 3. Free convection in the fin channels

Bar-Cohen & Rohsenow (1984), symmetric isothermal vertical parallel plates:

```
Ra_s = g * beta * (Ts - Ta) * s^3 / (nu * alpha)      s = fin gap
El   = Ra_s * s / L                                   Elenbaas number, L = fin length (vertical)
Nu_s = (576 / El^2 + 2.873 / El^0.5)^-0.5,  h = Nu_s * k / s
```

Air properties at the film temperature (Ts + Ta)/2. Fin efficiency `tanh(mH)/(mH)` with
`m = sqrt(2h / (k t))`; for aluminium fins in free convection it is almost always > 0.95.

Optimum gap for a given length and temperature rise: `s_opt = 2.714 * L * Ra_L^-0.25`,
typically 6-12 mm for 100-300 mm sinks. Too tight chokes the flow (the channel boundary layers
merge); too wide wastes area. The script flags gaps more than 40 % off the optimum.

The correlation assumes channels open at the bottom and the top and a sink far from walls. A
wall close behind or a shroud changes this; let the CFD decide.

## 4. Outside surfaces

The outer faces of the two end fins and an exposed back face use Churchill-Chu for an
isothermal vertical plate:

```
Nu_L = (0.825 + 0.387 Ra_L^(1/6) / (1 + (0.492/Pr)^(9/16))^(8/27))^2
```

Top and bottom edge faces are neglected (small area).

## 5. Radiation

The fin array radiates through its outer envelope: front plane of the fin tips (W x L), two
sides, and the exposed back face. Each radiates as grey at the surface emissivity to black
surroundings at ambient:

```
Q_rad = eps * sigma * A_envelope * (Ts^4 - Ta^4)
```

Fin-to-fin radiation inside a channel cancels out (they are at almost the same temperature),
which is why the envelope rather than the full wetted area counts. A channel actually emits a
little more than a flat plate of the same emissivity (cavity effect), so this errs low on heat
rejected and high on temperature, the safe side. For bare aluminium (eps ~ 0.05) radiation
is negligible; for black anodised it is 25-45 % of the total at small temperature rises.

## 6. Spreading resistance

Song, Lee & Au (1994), centred circular source on a circular plate with convective cooling on
the far side (sources and plates mapped to equal-area circles):

```
eps = a/b, tau = t/b, Bi = h_eff * b / k
lambda = pi + 1/(sqrt(pi) * eps)
Phi = (tanh(lambda tau) + lambda/Bi) / (1 + lambda/Bi * tanh(lambda tau))
psi_max = eps tau / sqrt(pi) + (1 - eps) Phi / sqrt(pi)
R_sp = psi_max / (k a sqrt(pi))
```

Used twice: IMS footprint into the sink base (h_eff from the sink's overall resistance) and
device pad into the IMS substrate (h_eff from the TIM conductance). Off-centre and edge
devices spread worse than this; the CFD captures that.

## 7. Layers above and below the spreader

One-dimensional, `R = sum(t / k) / A`: `board.layers_under_parts` over the device pad, and
`board.layers_to_sink` over the board footprint. Where the insulation sits matters. In an IMS
it is under the parts (above the Al spreader): 100 um at 2.2 W/mK under a 150 mm^2 pad is
0.30 K/W, as much as the whole sink at a few watts. In a Cu-core (QIT) board it is below the
Cu core, so the heat spreads first and crosses the insulation over a large area: 75 um at
1.8 W/mK over 40 cm^2 is ~0.01 K/W. Copper above the spreader is taken as not spreading
(conservative). A dry metal-to-metal contact without TIM is roughly R'' = 2-5e-4 m^2K/W
(h_c 2000-5000 W/m^2K, flat, screw-clamped); give it as a layer `{name, R_m2K_W}`. It then
often dominates the board-to-sink path.

## 8. Typical values

| Quantity | Typical |
|---|---|
| h in fin channels, free convection | 2-6 W/m2K |
| h on an outside vertical face | 3-6 W/m2K |
| Radiation h at 50 C, eps 0.9 | ~6.5 W/m2K on the envelope |
| IMS dielectric conductivity | 1-3 W/mK standard, up to ~10 for premium |
| Gap pad TIM | 1-6 W/mK, 0.1-1 mm |
| Thermal paste | 1-8 W/mK, 25-100 um |
| Rth(j-c) of D2PAK / TOLL power MOSFETs | 0.3-0.8 K/W |

## 9. When the hand calc is not enough

- Devices close to an edge of the base or of the IMS, or several sources far apart.
- Horizontal fins, a shroud, an enclosure, a wall close by.
- A sink much taller than ~0.3 m (the channel flow develops, the top runs hot).
- Anything where the answer sits within ~15 K of the limit.
