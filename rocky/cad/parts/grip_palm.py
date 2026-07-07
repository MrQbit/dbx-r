"""ROCKY-5 grip PALM — the SLIM wrist of the 2+1 manipulator (D-008, D-027, D-038).

OPERATOR REDESIGN (D-038): the old palm was a fat Ø108 crown disc with three
symmetric fingers. It is now a SLIM tapered WRIST — referenced from the sculpt
manipulator (docs/media/rocky_hands_before.png) — that:

  * BOLTS TO THE TIBIA tip via the real EduLite Ø41.5 PCD flange on a short mount
    collar (z = 0 face), then tapers to a slim Ø34 wrist (no crown disc);
  * FUSES THE TWO PRIMARY fingers low on the wrist — they converge into a single
    spider-leg WALKING TIP (Rocky stands on the fingertips, not the palm) and are
    rigid so the foot never wobbles under body weight;
  * CARRIES THE THUMB on a Ø5-pin clevis set slightly higher and opposing the two
    primaries (`grip_finger.THUMB_PIV`);
  * HIDES THE DRIVE inside the wrist: a back bay houses the grip micro-servo and its
    `grip_crown` drive crank, whose follower pin swings the thumb's crank tail. The
    bay opens on the -X (back) face and is closed by a snap cover — the slim wrist
    reads as solid weathered stone, no exposed mechanism.

Hand LOCAL frame (see grip_finger): Z = distal/outward, +X = thumb side,
-X = primary/foot side, Y = lateral. Prints wrist-down; the primaries + thumb clevis
want tree supports.
"""
from __future__ import annotations

from build123d import Box, Cone, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts import grip_finger as GF

# --- Wrist body (mount collar -> taper -> slim Ø34 wrist) -------------------
MOUNT_R = GF.MOUNT_R          # Ø52 collar (catches the tibia Ø41.5 PCD flange)
COLLAR_H = GF.COLLAR_H
CONE_TOP_Z = GF.CONE_TOP_Z
WRIST_R = GF.WRIST_R          # Ø34 slim wrist
WRIST_TOP_Z = GF.WRIST_TOP_Z

# --- Thumb clevis (Ø5 pin hinge) -------------------------------------------
EAR_W = 5.0
CLEVIS_GAP = GF.HUB_L + 2 * S.FIT_SLIDE_MM     # slot the thumb knuckle drops into
CLEVIS_SPAN = CLEVIS_GAP + 2 * EAR_W

# --- Hidden drive bay (servo + crank + thumb tail) --------------------------
# A blind internal bay (the slim wrist prints as a Y-split clamshell: two mirror
# halves bolted on the Y=0 plane, so the micro-servo + grip_crown drive crank drop
# in and the mechanism is fully hidden). It stays inside the round wrist (thick
# walls everywhere) and its top (z=25) meets the clevis gap (which reaches z≈24) so
# the thumb's crank tail passes down into the bay and swings on the drive crank.
BAY_X0 = -12.0                 # stays inside the round wrist (no thin edge slivers)
BAY_X1 = 12.0                  # reaches under the thumb tail (drive crank lives here)
BAY_Y = 8.5                   # half-width (Y) — clears the 12.2 mm servo body + crank
BAY_Z0 = 11.0
BAY_Z1 = 25.0

# --- Mount flange bolts (Ø41.5 PCD, into the tibia heat-sets) ---------------
BOLT_DEPTH = COLLAR_H + 4.0


def _clevis() -> Part:
    """Two-ear Ø5-pin clevis at the thumb pivot on a flat PEDESTAL (the pedestal's
    flat faces tie the round ears to the round wrist without a tangent feather-edge).
    The thumb knuckle drops in the central gap."""
    px, _py, pz = GF.THUMB_PIV
    ear = Pos(px, 0, pz) * Rotation(90, 0, 0) * Cylinder(radius=GF.HUB_R, height=CLEVIS_SPAN)
    ped = Pos(px - 5.0, 0, pz - 8.0) * Box(2 * GF.HUB_R + 6, CLEVIS_SPAN, 22)  # into the wrist
    solid = ear + ped
    solid -= Pos(px, 0, pz) * Box(2 * GF.HUB_R + 6, CLEVIS_GAP, 2 * GF.HUB_R + 4)  # thumb-hub gap
    solid -= Pos(px, 0, pz) * Rotation(90, 0, 0) * Cylinder(
        radius=GF.PIN_BORE / 2, height=CLEVIS_SPAN + 1)
    return solid


def grip_palm() -> Part:
    collar = Pos(0, 0, COLLAR_H / 2) * Cylinder(radius=MOUNT_R, height=COLLAR_H)
    cone = Pos(0, 0, (COLLAR_H + CONE_TOP_Z) / 2) * Cone(
        bottom_radius=MOUNT_R, top_radius=WRIST_R, height=CONE_TOP_Z - COLLAR_H)
    wrist = Pos(0, 0, (CONE_TOP_Z + WRIST_TOP_Z) / 2) * Cylinder(
        radius=WRIST_R, height=WRIST_TOP_Z - CONE_TOP_Z)
    palm = collar + cone + wrist

    # Two fused primary fingers (the walking tip) + the thumb clevis.
    palm += GF.primaries()
    palm += _clevis()

    # --- Hidden drive bay (opens -X) ----------------------------------------
    palm -= Pos((BAY_X0 + BAY_X1) / 2, 0, (BAY_Z0 + BAY_Z1) / 2) * Box(
        BAY_X1 - BAY_X0, 2 * BAY_Y, BAY_Z1 - BAY_Z0)

    # --- Mount flange: 6 clearance bolts on the Ø41.5 PCD (z=0 face) ---------
    palm -= Pos(0, 0, 0) * E.bolt_holes(BOLT_DEPTH, extend_up=1.0)

    return palm


META = PartMeta(
    name="grip_palm",
    material="PETG",
    qty=GF.N_HANDS,                       # one slim wrist per 2+1 hand
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="tree",
    inserts=(
        Insert("m4_clearance", 3, "tibia-flange bolts, Ø41.5 PCD (M4)"),
        Insert("m3_clearance", 3, "tibia-flange bolts, Ø41.5 PCD (M3)"),
        Insert("bearing_625zz", 1, "Ø5 thumb-pivot pin (clevis)"),
    ),
    clearances={"mount_flange": "slide", "thumb_pin": "press",
                "servo_bay": "slide", "drive_crank": "loose"},
)


def part() -> Part:
    return grip_palm()
