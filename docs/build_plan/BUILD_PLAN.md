# ROCKY-5 — Leg Build Plan (servos modelled in the joints)

**Purpose.** The exterior renders read as "detached pieces / flat cuts" because the
**servo that bridges each joint gap was never modelled.** This build plan models the
EduLite-05 leg servos and the grip micro-servo and shows them **embedded in the
joints**, so the operator can see how a leg actually assembles and believe it builds.

**Verdict on the "floating" segments:** *No segment is truly detached.* Every distal
segment is bridged by a servo. The alarming ~25 mm gap between the coxa and femur at
knee1 is **the Ø46 servo seat pocket** — the leg neck there is only 37 mm, thinner than
the 46 mm servo body, so the seat carves the whole joint cross-section away and the
segments are joined *only through the servo* (then hidden under a cosmetic cover
sleeve). Drawing the servo in that pocket fixes the read; it was a missing-model
problem, not a broken-geometry problem. See the fit check below.

## Sheets (this folder)
| File | View |
|------|------|
| `exploded_leg.png`   | One leg exploded along its axis, 10 numbered assembly steps |
| `cutaway_joint.png`  | Longitudinal cutaway — servos seated inside the hollow segments |
| `assembled_ghost.png`| Whole 5-leg robot, segments ghosted, all servos visible |
| `servo_layout.png`   | Top-down servo schematic + actuator BOM |
| `build_plan_sheets.pdf` | All four sheets, one per page |

Source geometry: `rocky/cad/stl_derived/refined_{thorax,coxa,femur,tibia}.stl` +
`refined_knee1_cover.stl` / `refined_knee2_cover.stl` (official craggy sculpt,
bisect/boolean only — no remesh). The servos are modelled by
`scripts/build_plan_rocky.py`; sheets composited by `scripts/annotate_build_plan.py`.
Modelled servo solids are written to `servo_edulite05.stl` / `servo_grip_micro.stl`
(gitignored).

## Part list (printed, per leg × 5 legs)
| Part | Size (mm) | Qty | Notes |
|------|-----------|-----|-------|
| Thorax dome | 191.7 × 166.5 × 137.8 | 1 | 3 mm shell; hip sockets on the flank; Jetson + battery bays |
| Coxa | 28.8 × 38.3 × 47.7 | 5 | 3 mm shell |
| Femur | 33.1 × 51.9 × 58.6 | 5 | 3 mm shell |
| Tibia + hand | 74.5 × 31.3 × 83.8 | 5 | 3 mm shell; **sacred 3-finger manipulator hand** at the distal end (1:1 from sculpt) |
| Knee1 cover | sleeve | 5 | cosmetic stone sleeve over the knee1 flat mount + servo |
| Knee2 cover | sleeve | 5 | cosmetic stone sleeve over the knee2 flat mount + servo |

## Servo list (actuators)
| Servo | Size (mm) | Qty | Role |
|-------|-----------|-----|------|
| **EduLite-05** | Ø46 × 44 body, Ø24 × 8 output collar, Ø52 flange (Ø41.5 PCD), 242 g | **17** | 15 leg joints (5 legs × hip/knee1/knee2) + 2 grip-drive on manipulator legs 1 & 4 |
| **Grip micro (MG90S)** | 22.8 × 12.2 × 28.5, 13.4 g | **5** | one per 3-finger hand; drives the finger crown cam |
| MG90S (breathing) | 22.8 × 12.2 × 28.5 | 1 | carapace scroll-cam — not a joint (listed for completeness) |

Counts are the single source of truth in `common/cad_lib/components.rocky_components()`.

## The EduLite-05, as modelled
- **Ø46 × 44 mm cylindrical housing** — seats in the proximal segment's Ø46 pocket
  (Ø38.5 pilot centres it).
- **Ø24 × 8 mm output collar** — coaxial on the pitch axis; the distal segment mounts
  to it and is what the joint rotates.
- **Ø52 mounting flange** — Ø41.5 PCD, 6 bolts on a 30° grid (alternating M4 / M3),
  from `common/cad_lib/edulite.py`.
- Every leg servo's rotation (pitch) axis is the world **Y** axis; the seat opens on the
  hidden inner (−Y) face.

## Assembly, per leg (proximal → distal)
1. **Hip servo** (EduLite-05) → drop into the **thorax hip socket** (Ø46 pocket, Ø38.5
   pilot). Flange bolts to the socket floor; output collar faces outward.
2. **Coxa** → mount onto the hip servo output collar. The coxa root sinks deep into the
   thorax socket (≈20 mm), so the craggy flank overlaps and hides the junction.
3. **Knee1 servo** (EduLite-05) → body seats in the coxa's distal flat mount. Because
   the 37 mm neck < 46 mm body, this is a **flat mount** (not buried).
4. **Femur** → mount onto the knee1 servo output collar.
5. **Knee1 cover** → slide the cosmetic stone sleeve over the knee1 servo + joint; clip
   / bolt so the outer surface matches the sculpt.
6. **Knee2 servo** (EduLite-05) → body seats in the femur's distal flat mount (48 mm
   neck — still a flat mount + cover).
7. **Tibia (with hand)** → mount onto the knee2 servo output collar.
8. **Knee2 cover** → sleeve over the knee2 servo + joint.
9. **Grip micro-servo (MG90S)** → into the hand pocket; couples to the finger crown cam
   that drives the three fingers.

Repeat ×5 (true 5-fold radial symmetry, legs at 72°). Legs 1 & 4 additionally carry a
grip-drive EduLite (IDs 16–17).

## Fastener / fit notes
- Servo flange: Ø41.5 PCD, 6 holes at 60° (offset 30°) — 3 × M4-clearance (Ø5.5) +
  3 × M3, heat-set inserts in the printed seat.
- Servo body slide-fit: pocket Ø = 46.0 + 0.20 mm (FIT_SLIDE); pilot Ø38.5 + fit centres it.
- Output collar bore: Ø24 loose fit so it rotates free.
- Wide joints (hip) bury the body in the socket; slender joints (knee1 37 mm, knee2
  48 mm) use a flat mount **plus** the cosmetic cover sleeve — this is by design.

## Fit / bridge verification (honest check)
For each joint, both the proximal and distal segments must fall inside the modelled
Ø46 servo body (radius 23 mm from the servo axis) for the servo to truly bridge them:

| Joint | Proximal seg / min radial | Distal seg / min radial | Bridged? |
|-------|---------------------------|--------------------------|----------|
| Hip   | thorax  6.2 mm | coxa  0.3 mm | **yes** |
| Knee1 | coxa 10.9 mm | femur 11.8 mm | **yes** (both well inside the 23 mm body radius — the pocket is filled) |
| Knee2 | femur  3.0 mm | tibia  0.4 mm | **yes** |

(Generated by `scripts/build_plan_rocky.py` → `build_plan_facts.json`.)

## Torque fact
EduLite-05: 1.8 N·m continuous / 6 N·m peak QDD on the Ø41.5 PCD — torque-valid for the
light compact ROCKY-5 body; Ø46 gives a slenderer leg-neck than an RS00-class actuator.

---
*Regenerate:* `blender --background --python scripts/build_plan_rocky.py` then
`.venv/bin/python scripts/annotate_build_plan.py`.
