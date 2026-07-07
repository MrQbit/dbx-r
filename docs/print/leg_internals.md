# ROCKY-5 leg INTERNALS — print package (D-042 locked chassis)

The printable mechanism of one leg (×5). **STLs regenerate from the parametric code**
(`scripts/cadpy scripts/gen_cad.py rocky` → `rocky/cad/parts/<name>.stl`) — the code is
the source of truth; STLs are gitignored (regenerable, and to keep the copyrighted
sculpture meshes out). Final STLs are exported + committed once the Phase-2 shell fit
confirms no chassis changes are needed.

> Status: chassis LOCKED (D-042), gate-1/2/3 green. Shell-fit trial in progress — if it
> forces a chassis change, regenerate this set before printing.

## Printed parts (PETG unless noted) — per leg, ×5 legs
| Part | Qty/leg | Mass @100% (~30% infill) | Notes / print |
|---|---|---|---|
| `leg_hip_yoke` | 1 | 34 g (~12 g) | coxa_yaw QDD flange → body; min-wall 4.9 |
| `coxa_bracket` | 1 | 240 g (~72 g) | hip-cluster frame, holds 3 QDD; body mass, not leg |
| `femur_link` | 1 | 46 g (~16 g) | SLIM Ø12 driveshaft wrap + CV ring + knee bevel box |
| `tibia_bracket` | 1 | 73 g (~24 g) | knee-bevel driven; hosts the inline roll STS |
| `tibia_link` | 1 | 28 g (~10 g) | shank |
| `grip_palm` | 1 | 67 g | slim 2+1 hand palm (hides grip micro); Y-split clamshell |
| `grip_crown` | 1 | 2 g | hidden thumb drive crank |
| `grip_finger` | 1 | 8 g | the moving THUMB (2 primaries fused to the palm) |
| `foot` | 1 | 14 g (TPU sole option) | — |

All parts watertight, ≤250 mm (print whole, no split), min-wall ≥2.4 mm. Gyroid 30–40%
infill on the struts (D-040). Split-shell clamshells bolt over the 6× M2.5 anchors.

## Sourced hardware (NOT printed) — per leg / ×5
| Item | Qty/leg | ×5 | Spec |
|---|---|---|---|
| Robstride EduLite-05 QDD | 3 | **15** | coxa_yaw + femur_pitch + knee motor; Ø46×44, 6 N·m, CAN, 48 V |
| Feetech STS3215 servo | 1 | **5** | tibia_roll (inline); 45×24.7×35, TTL, 12 V |
| MG90S micro-servo | 1 | **5** | grip thumb drive; PWM |
| RC 1/8 CVD / double-cardan | 1 | 5 | knee driveshaft through the femur_pitch axis (constant-velocity, ~80°) |
| M1 16T miter bevel pair | 1 | 5 | knee — turns shaft → knee axis, 1:1 |
| Ø6 steel shaft (in Ø12 tube) | 1 | 5 | femur driveshaft |
| 625ZZ bearing (5×16×5) | ~4 | ~20 | pitch pivots + shaft supports |
| Ø5×20 steel stub axle | 1–2 | ~7 | far-side pitch support |
| M3 heat-set + bolt | ~6 | ~30 | QDD flanges (M3+M4) |
| M2.5 heat-set + bolt | 6 | **30** | SHELL anchors (2 each coxa/femur/tibia) — hidden, serviceable |
| Ø5 pivot pin (finger) | 1 | 5 | grip thumb hinge |

## Transmission (D-042)
Knee = double-cardan CVD on the femur_pitch axis → Ø6 shaft down the femur → M1 miter
bevel at the knee. Ratio 1.0, backlash ~0.044 rad (2.5°), efficiency ~0.9. Motor lives
in the body hip cluster (light distal leg).

## Buses / power
QDD (15) on **CAN** @ 48 V (6S pack); STS roll (5) on **TTL serial** @ 12 V (buck rail);
grip micro (5) on **PWM**. E-stop on the QDD rail.

## To regenerate the STLs
```
scripts/cadpy scripts/gen_cad.py rocky      # writes rocky/cad/parts/*.stl
make gate-2                                 # QA (watertight / envelope / min-wall)
```
