"""ROCKY-5 grip DRIVE CRANK — the hidden micro-servo → thumb link (D-027, D-038).

OPERATOR REDESIGN (D-038): the old part was a Ø100 spiral-cam crown that synced
three symmetric fingers. The 2+1 hand has ONE moving digit (the thumb), so this
part is now a small **drive crank**: it presses onto the grip micro-servo output
horn and carries a Ø5 FOLLOWER PIN at a short throw. As the servo sweeps, the
follower pin pushes the thumb's crank tail (`grip_finger`), swinging the thumb from
open (raised) to closed (pinching the two primary fingertips). It lives fully
hidden inside the slim wrist's drive bay (`grip_palm`).

WHY A CRANK + PIN, NOT GEAR TEETH (honest, inherits D-027)
----------------------------------------------------------
Same reasoning as the retired crown cam: printable involute teeth at this size fall
below the 2.4 mm structural min-wall. A chunky crank + a Ø5 steel follower pin
riding the thumb tail is backlash-tolerant, prints without supports, and needs no
sliver-thin teeth. The crank is modelled in its own frame: rotation axis = Y (the
servo output), the throw arm in the X-Z plane.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts import grip_finger as GF

# --- Crank body (on the micro-servo output horn) ---------------------------
CROWN_T = 8.0                     # thickness along the servo axis (Y)
HUB_R = 7.0                       # Ø14 hub around the servo horn
THROW = GF.DRIVE_CRANK_R         # follower-pin throw radius (= 9 mm)
BOSS_R = 5.4                      # Ø10.8 follower boss (wall ≥ 2.7 mm on the Ø5 pin)
HORN_BORE = 4.8                   # micro-servo output horn seat (splined / horn-screw)
FOLLOW_BORE = GF.FOLLOW_BORE      # Ø5 follower pin

# Back-compat: the assembly/render seat the crank at this station in the wrist.
Z_TOP = CROWN_T                   # (kept so importers referencing grip_crown.Z_TOP don't break)
CROWN_R = HUB_R                   # (kept for the same reason)


def grip_crown() -> Part:
    hub = Rotation(90, 0, 0) * Cylinder(radius=HUB_R, height=CROWN_T)          # axis Y
    arm = Pos(THROW / 2, 0, 0) * Box(THROW + HUB_R, CROWN_T, 2 * BOSS_R)       # throw arm
    boss = Pos(THROW, 0, 0) * Rotation(90, 0, 0) * Cylinder(radius=BOSS_R, height=CROWN_T)
    crank = hub + arm + boss

    # Servo-horn seat (centre) + follower-pin bore (at the throw).
    crank -= Rotation(90, 0, 0) * Cylinder(radius=HORN_BORE / 2, height=CROWN_T + 2)
    crank -= Pos(THROW, 0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=FOLLOW_BORE / 2, height=CROWN_T + 2)
    return crank


META = PartMeta(
    name="grip_crown",
    material="PETG",
    qty=GF.N_HANDS,                   # one drive crank per 2+1 hand
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="none",                  # prints flat
    inserts=(
        Insert("dowel_5x20", 1, "Ø5 follower pin (drive crank ↔ thumb tail)"),
    ),
    clearances={"servo_horn": "press", "follower_pin": "press"},
)


def part() -> Part:
    return grip_crown()
