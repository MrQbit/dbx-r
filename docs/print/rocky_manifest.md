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
| `limb_marked` | PETG | 1 | 22.0 × 16.0 × 72.0 | ✅ | none | upright along Z; engraved +X face vertical (no support on the ternary/marriage relief) | M2 self-tap ×1 (foot boss) | PASS (min-wall 2.60) |
| `foot` | PETG* | 5 | 40.7 × 47.0 × 26.6 | ✅ | tree | hub axis vertical, prongs up; tree supports under the 35° splayed prongs | M3 heat-set ×1 (tibia bolt) | PASS (min-wall 3.00) |
| `carapace` | PLA | 1 | 153.1 × 158.4 × 93.5 | ✅ | tree | rim-down (open mouth on the plate), apex up; tree supports for the crown overhang | — | PASS (min-wall 3.68) |
| `belly_rx_plate` | PETG | 1 | 76.0 × 76.0 × 9.0 | ✅ | none | flip pocket-side **up** on the bed → self-supporting Qi pocket | M3 heat-set ×3 (under core plate) | PASS (min-wall 3.00) |
| `charging_base` | PETG | 1 | 129.9 × 130.0 × 22.0 | ✅ | none | pad flat on bed, TX pocket opens up (self-supporting) | M3 heat-set ×4 (TX + feet) | PASS (min-wall 4.00) |

Total registered printed mass (unit×qty): **core 78.3 g + 5×foot 70.5 g + tibia 32.0 g + carapace 140.9 g + belly 34.2 g + dock 135.6 g ≈ 491 g of plastic** (robot mass is motor-dominated; the 17 EduLite servos add ~4.1 kg — see `docs/reports/mass_rocky.md`).

\* **Foot filament note:** the generator currently tags the 3-prong claw `foot` as **PETG** (it is the structural end-effector). The movie-accurate **TPU hemispherical sole** (`foot_dia_mm: 19`, params §dimensions) is a separate soft cap that is **not yet modeled** as its own part — see "Still needs a decision" below. Print the claw in PETG; the TPU sole prints on the external TPU spool once authored.

## Carapace split (validated alternate — currently UNREGISTERED)

The single-piece `carapace` (153 × 158 × 93 mm) fits the envelope with wide margin, so it stays the default one-print shell (registry keeps the split out). The 2-piece split is **validated at the tightened params** and swaps in unchanged if a future scale pushes the dome past 250 mm:

| Part | Filament | Qty | Bbox L×W×H (mm) | Fits 250? | Supports | Orientation | QA |
|---|---|---:|---|:--:|---|---|:--:|
| `carapace_cap` | PLA | 1 | 108.8 × 113.8 × 42.3 | ✅ | tree | seam-face down on bed, apex up | PASS (min-wall 3.14) |
| `carapace_skirt` | PLA | 1 | 153.1 × 158.4 × 61.1 | ✅ | none | seam-face up (rim on bed) | PASS (min-wall 2.15) |

**Dovetail / registration lip:** skirt carries an internal pentagonal spigot (`seam_lip`) that keys into the cap with a loose slide fit. Assembled-position boolean interference **cap ∩ skirt = 0.000000 mm³** (tol 1.25e-4) → **mates clean, zero interference.** Seam-aware displacement (`z_seam`) holds the flat mating face flush while the outer walls stay craggy.

## Print plates / swap schedule (by `plate_group`)

- **rocky_structure** — `core_plate`, `belly_rx_plate` (PETG)
- **rocky_limbs** — `limb_marked`, 5× `foot` (PETG). Feet fill one plate (tree supports).
- **rocky_shells** — `carapace` (PLA). Long print (~53 k tris, craggy skin). Split alternates go here if swapped in.
- **charging_base** — `charging_base` (PETG), prints alongside structure.

Single-material plates as grouped; only filament change is PLA (shells) ↔ PETG (everything else), plus the external TPU spool for the future sole. No mid-print swaps required.

## Hardware-cavity verification vs current BOM

BOM boxes come from `common/cad_lib/components.py` (single source of truth). Sizes are **correct for the tightened BOM**, but note which are realized as printed geometry:

| BOM component | Box (mm) | Provision | Realized in a printed part? |
|---|---|---|---|
| EduLite-05 servo | 52 × 52 × 34 | pocket | ❌ **not modeled** — no coxa/femur/hip bracket parts exist in the registry yet |
| Jetson Orin compact carrier | 90 × 63 × 30 | tray | ❌ **not modeled** — `core_plate` has only a 30 mm vent + 5 coxa holes, no tray/walls |
| Battery 3S bay | 70 × 38 × 20 | bay | ❌ **not modeled** — no walled compartment on the (4 mm) core plate |
| IMU BNO055 | 20 × 27 × 4 | boss | ❌ not modeled |
| Qi RX coil | 55 × 40 × 5 | coil_pocket | ✅ `belly_rx_plate` — pocket = 55.7 × 40.7 (loose +0.35/side), 6 mm depth, mounts + cable pass |
| Qi TX coil | 60 × 60 × 12 | coil_pocket | ✅ `charging_base` — pocket = 60.7 × 60.7, 13 mm depth, cable channel |

**Honest status:** the registered Rocky set is a **seed part set** — chassis plate + one marked tibia + foot + shell + the two Qi charging parts. The load-bearing **leg brackets that would host the EduLite servo pockets, and the core compartment that would host the Jetson tray + battery bay, are not authored yet.** Their dimensions are already correct in `components.py`, so realizing them is geometry work, not a BOM change. (Also flagged: `common/cad_lib/coupons.py` still fit-tests the old **STS3215** body 45.2 × 24 × 32 via `standards.SERVO_BOX_*`; if the coupon is meant to validate Rocky's EduLite slide-fit, that box needs updating to 52 × 52 × 34.)

## Still needs a decision (human next actions, ranked)

1. **Author the leg brackets** (coxa / femur / hip) that carry the EduLite-05 **52 × 52 × 34 servo pockets** — currently no part hosts a servo. Blocks a fully assemblable robot.
2. **Author the core "tub"** (or thicken `core_plate` into a compartment) to realize the **Jetson tray 90 × 63 × 30**, **battery bay 70 × 38 × 20**, IMU boss, audio driver vent, and fan mount that `components.py` already places on `base_link`.
3. **TPU hemispherical foot sole** (`foot_dia_mm 19`) — model as its own soft part on the TPU spool, or confirm the PETG claw is the final foot.
4. **Coupon servo box** — update `standards.SERVO_BOX_*` (or add a Rocky-specific coupon) to the EduLite 52 × 52 × 34 before the human prints the fit-test plate.
