# ROCKY-5 — Print Manifest (G8 print package)

Generated from the parametric CAD after the **tightened** params (D-014):
carapace circumscribed dia **165 mm**, legs ~×0.75, EduLite-05 servos, mass target ~5 kg.

- Source of truth: `rocky/design/params.yaml` → `scripts/gen_cad.py` (via `scripts/cadpy`, micromamba `duet-cad`: build123d 0.8.0 + trimesh).
- Print envelope: **Bambu Lab P2S 250 × 250 × 250 mm** (QA hard limit).
- Mesh QA (`common/export/qa.py::check_mesh`): watertight + ≤250 mm envelope + min-wall (2.4 mm structural / 1.6 mm cosmetic). **All parts below PASS.**
- STL files live in `rocky/cad/parts/*.stl` (gitignored — regenerate with `make _cad ROBOT=rocky`).
- Preview render: `docs/media/rocky_print_set.png`.

## Registered printable parts (the robot)

| Part | Filament | Qty | Bbox L×W×H (mm) | Fits 250? | Supports | Print orientation | Inserts | QA |
|---|---|---:|---|:--:|---|---|---|:--:|
| `core_plate` | PETG | 1 | 149.2 × 156.9 × 4.0 | ✅ | none | flat on bed, as modeled (pentagon face down) | M3 heat-set ×5 (coxa mounts) | PASS (min-wall 4.00) |
| `core_tub` | PETG | 1 | 123.9 × 124.0 × 31.4 | ✅ | tree | floor down on bed, open top up (walls/standoffs self-support; tree under the fan bolt bosses) | M3 heat-set ×4 (Jetson standoffs), M2 self-tap ×2 (IMU) | PASS (min-wall 2.90) |
| `leg_bracket` | PETG | 5 | 239.4 × 76.4 × 44.0 | ✅ | tree | flat bottom on bed, servo pockets up; tree under the side pivot-knuckle bores | M3 heat-set ×3 (coxa-root + tie), 625ZZ ×4 (pitch pivots) | PASS (min-wall 3.90) |
| `limb_marked` | PETG | 1 | 22.0 × 16.0 × 72.0 | ✅ | none | upright along Z; engraved +X face vertical (no support on the ternary/marriage relief) | M2 self-tap ×1 (foot boss) | PASS (min-wall 2.60) |
| `foot` | PETG* | 5 | 40.7 × 47.0 × 26.6 | ✅ | tree | hub axis vertical, prongs up; tree supports under the 35° splayed prongs | M3 heat-set ×1 (tibia bolt) | PASS (min-wall 3.00) |
| `carapace` | PLA | 1 | 153.1 × 158.4 × 93.5 | ✅ | tree | rim-down (open mouth on the plate), apex up; tree supports for the crown overhang | — | PASS (min-wall 3.68) |
| `belly_rx_plate` | PETG | 1 | 76.0 × 76.0 × 9.0 | ✅ | none | flip pocket-side **up** on the bed → self-supporting Qi pocket | M3 heat-set ×3 (under core plate) | PASS (min-wall 3.00) |
| `charging_base` | PETG | 1 | 129.9 × 130.0 × 22.0 | ✅ | none | pad flat on bed, TX pocket opens up (self-supporting) | M3 heat-set ×4 (TX + feet) | PASS (min-wall 4.00) |

Total registered printed mass (unit×qty, solid-volume × density = 100 % infill upper bound): core_plate 78.3 g + **core_tub 130.3 g** + **5×leg_bracket 2279 g** + 5×foot 70.5 g + tibia 32.0 g + carapace 140.9 g + belly 34.2 g + dock 135.6 g ≈ **3.0 kg of plastic** (was ~491 g for the seed set). With the 17 EduLite servos (~4.1 kg) that trends the built robot toward ~7 kg at 100 % infill — **above the 5 kg design target (D-014)**. The solid `leg_bracket` beam (456 g each) dominates the growth: real prints use 15–30 % infill (far lighter), but the bracket should still be lightened (side windows / lower infill) before the G1 torque re-check — see "Still needs a decision". Numbers per `docs/reports/mass_rocky.md`.

\* **Foot filament note:** the generator currently tags the 3-prong claw `foot` as **PETG** (it is the structural end-effector). The movie-accurate **TPU hemispherical sole** (`foot_dia_mm: 19`, params §dimensions) is a separate soft cap that is **not yet modeled** as its own part — see "Still needs a decision" below. Print the claw in PETG; the TPU sole prints on the external TPU spool once authored.

## Carapace split (validated alternate — currently UNREGISTERED)

The single-piece `carapace` (153 × 158 × 93 mm) fits the envelope with wide margin, so it stays the default one-print shell (registry keeps the split out). The 2-piece split is **validated at the tightened params** and swaps in unchanged if a future scale pushes the dome past 250 mm:

| Part | Filament | Qty | Bbox L×W×H (mm) | Fits 250? | Supports | Orientation | QA |
|---|---|---:|---|:--:|---|---|:--:|
| `carapace_cap` | PLA | 1 | 108.8 × 113.8 × 42.3 | ✅ | tree | seam-face down on bed, apex up | PASS (min-wall 3.14) |
| `carapace_skirt` | PLA | 1 | 153.1 × 158.4 × 61.1 | ✅ | none | seam-face up (rim on bed) | PASS (min-wall 2.15) |

**Dovetail / registration lip:** skirt carries an internal pentagonal spigot (`seam_lip`) that keys into the cap with a loose slide fit. Assembled-position boolean interference **cap ∩ skirt = 0.000000 mm³** (tol 1.25e-4) → **mates clean, zero interference.** Seam-aware displacement (`z_seam`) holds the flat mating face flush while the outer walls stay craggy.

## Print plates / swap schedule (by `plate_group`)

- **rocky_structure** — `core_plate`, `core_tub`, 5× `leg_bracket`, `belly_rx_plate` (PETG). The five 239 mm leg brackets are the bulk of the plastic — each fills most of a plate on its own (tree supports under the pivot bores).
- **rocky_limbs** — `limb_marked`, 5× `foot` (PETG). Feet fill one plate (tree supports).
- **rocky_shells** — `carapace` (PLA). Long print (~53 k tris, craggy skin). Split alternates go here if swapped in.
- **charging_base** — `charging_base` (PETG), prints alongside structure.

Single-material plates as grouped; only filament change is PLA (shells) ↔ PETG (everything else), plus the external TPU spool for the future sole. No mid-print swaps required.

## Hardware-cavity verification vs current BOM

BOM boxes come from `common/cad_lib/components.py` (single source of truth). Sizes are **correct for the tightened BOM**, but note which are realized as printed geometry:

| BOM component | Box (mm) | Provision | Realized in a printed part? |
|---|---|---|---|
| EduLite-05 servo | 52 × 52 × 34 | pocket | ✅ `leg_bracket` — 3 slide-fit pockets/leg (52.4 × 52.4 sq, 35 mm deep), ×5 legs = **15 servo pockets** |
| Jetson Orin compact carrier | 90 × 63 × 30 | tray | ✅ `core_tub` — 4 raised standoffs (84 × 50 pattern, M3), board sits above the pack and clears the rim into the dome apex |
| Battery 3S bay | 70 × 38 × 20 | bay | ✅ `core_tub` — walled bay, **72 × 40 interior** (loose +1 mm/side), 20 mm deep, low on the floor for CoM |
| IMU BNO055 | 20 × 27 × 4 | boss | ✅ `core_tub` — 22 × 29 pad + 2× M2 (offset −X of the pack; see note) |
| 40 mm fan | 40 × 40 × 10 | fan_mount | ⚠️ `core_tub` — 18 mm floor exhaust vent + **2 diagonal M3 bosses** (the full 32 mm 4-bolt square doesn't fit beside the 70 mm pack at this dome size) |
| Qi RX coil | 55 × 40 × 5 | coil_pocket | ✅ `belly_rx_plate` — pocket = 55.7 × 40.7 (loose +0.35/side), 6 mm depth, mounts + cable pass |
| Qi TX coil | 60 × 60 × 12 | coil_pocket | ✅ `charging_base` — pocket = 60.7 × 60.7, 13 mm depth, cable channel |

Preview of the two new structural parts: `docs/media/rocky_structural.png`.

**Honest status:** the load path is now authored end to end — `core_plate` → `core_tub` (electronics) and `core_plate` → `leg_bracket` (×5, servos) → `foot`. All 8 registered Rocky parts (+ the shared coupon) pass mesh QA and **`make gate-2` is green (9/9)**. Cavities are driven from `components.py`, so re-sourcing a module resizes the print. Remaining gaps are packaging/finish decisions, not missing structure. The coupon fit-test now uses the EduLite 52 × 52 × 34 box (D-019), not the legacy STS3215.

## Still needs a decision (human next actions, ranked)

1. **Lighten `leg_bracket`** — the solid 239 × 76 × 44 beam is 456 g each (2.28 kg for 5) at 100 % infill, pushing the built robot toward ~7 kg (over the 5 kg target, D-014). Add side lightening windows and/or print at 15–30 % infill before the G1 torque re-check consumes `mass_rocky.md`.
2. **Fan packaging** — a 40 mm fan can't floor-mount with its full 4-bolt pattern beside the 90 mm Jetson + 70 mm pack in the 165 mm dome. Current tub gives a 2-bolt diagonal mount + vent; confirm that holds, or move the fan to the carapace / onto the Jetson heatsink.
3. **IMU placement** — the boss is offset −X of the pack (the battery bay owns the centroid). Confirm the small offset is acceptable for the BNO055 (`forward_axis +X`) or relocate onto a bridge over the pack.
4. **TPU hemispherical foot sole** (`foot_dia_mm 19`) — model as its own soft part on the TPU spool, or confirm the PETG claw is the final foot.
5. **Audio driver vent** — `components.py` places a 40 mm audio driver on `base_link`; not yet realized as printed geometry (skirt grilles live on the carapace).
