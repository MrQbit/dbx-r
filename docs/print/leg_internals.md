# ROCKY-5 leg INTERNALS — print package (D-042 chassis, D-043 long slender legs)

The printable mechanism of one leg (×5). **STLs regenerate from the parametric code**
(`scripts/cadpy scripts/gen_cad.py rocky` → `rocky/cad/parts/<name>.stl`) — the code is
the source of truth; STLs are gitignored (regenerable, and to keep the copyrighted
sculpture meshes out). Final STLs are exported + committed once the Phase-2 shell fit
confirms no chassis changes are needed.

> Status: chassis LOCKED (D-042); legs lengthened to long/slender movie proportions
> (D-043: femur 73→98, tibia 105→170 mm, hip→tip 328 mm, footprint 489 mm); cosmetic
> shell derived + craggy-preserving + tibia thin-axis fatten to enclose the mechanism
> (D-044/D-045). gate-1/2/3 green. Regenerate STLs (below) before printing — the
> lengths differ from the original D-042 set.

## Printed parts (PETG unless noted) — per leg, ×5 legs
| Part | Qty/leg | Mass @100% (~30% infill) | Notes / print |
|---|---|---|---|
| `leg_hip_yoke` | 1 | 34 g (~12 g) | coxa_yaw QDD flange → body; min-wall 4.9 |
| `coxa_bracket` | 1 | 240 g (~72 g) | hip-cluster frame, holds 3 QDD; body mass, not leg |
| `femur_link` | 1 | ~55 g (~19 g) | 98 mm Ø12 driveshaft wrap + CV ring + knee bevel box |
| `tibia_bracket` | 1 | ~80 g (~26 g) | knee-bevel driven; hosts the inline roll STS |
| `tibia_link` | 1 | ~40 g (~14 g) | 170 mm shank (D-043 lengthened) |
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

## Cosmetic shell (separate cosmetic layer, D-044/D-045)
The craggy stone leg skins derive from the official action-figure limbs (N-A femur +
N-B tibia, leg1 = manipulator/1-C hand) — uniform-scaled (s=4.40) + thin-hollowed to
preserve the craggy relief, tibia thin-axis fattened to enclose the mechanism. Split into
sagittal clamshells that bolt on the 6× M2.5 anchors (removable). Derived under
`rocky/cad/stl_derived/af_shells/` (gitignored — source meshes are copyrighted, see
docs/LICENSES.md; regenerate via `scripts/blender_actionfig_shells.py`). Legs 2/3/4 have
minor chassis show-through at natural stone hollows — back/paint on the real print.

## To regenerate the STLs
```
scripts/cadpy scripts/gen_cad.py rocky      # writes rocky/cad/parts/*.stl
make gate-2                                 # QA (watertight / envelope / min-wall)
```
