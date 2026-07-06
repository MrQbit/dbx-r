"""ROCKY-5 three-finger grip hand-foot — printable, one per front manipulator
(legs 1 & 4, qty 2; ROBOTS_SPEC.md §4, D-008).

The two legs flanking the heading limb (params `manipulators.legs: [1, 4]`) end
in a grip hand instead of the passive 3-prong foot: a stony palm at the tibia tip
carrying three triangular "Eridian-stone" fingers driven by ONE grip servo
(`manipulators.servo_ids: [16, 17]`). The hand doubles as a foot — at grip 0 the
fingers lie FLAT and splayed (a broad stable sole for standing); at grip 1.4 rad
they swing up and inward into a cradling grasp (`grip_limit_rad: [0.0, 1.4]`).

Mechanism (single servo -> three synchronised fingers)
------------------------------------------------------
The grip servo (full EduLite-05, coaxial with the limb, bolted to the palm's top
face via the real Ø41.5 PCD flange — common.cad_lib.edulite) turns a central
drive disc through the Ø24 output bore. The disc is a crown/face gear meshing
with three pinions, one on each finger's pivot shaft at 120° — so ONE servo
rotation drives all three finger pivots by the SAME angle (grip_rad). A face-gear
synchroniser is the printable, backlash-tolerant choice here (a 3-bar/central-cam
alternative was considered; the crown gear keeps all three fingers exactly in
phase and hides inside the palm dome so the hand reads as stone, not machine).

Poses & feasibility
-------------------
* grip 0.0 rad — fingers horizontal, undersides ~coplanar with the palm base:
  a flat splayed tripod sole (footprint ~Ø170). The hand stands on it.
* grip 1.4 rad (~80°) — fingers swing up about their tangential pivots; tips rise
  and pull in to ~Ø90. Because 1.4 rad < 90° the fingers never pass vertical, so
  this is a CRADLE/CUP grasp (holds an object against the palm from three sides),
  not a closing fist — honest given the fixed grip limit.

Printed model altitude: like `foot.py`, this returns ONE fused sculptural solid
in the requested pose (default = open/flat, the as-modeled printed pose). The
functional build splits the three fingers as separate prints pinned to the palm
hubs (pivot bores modeled) and driven by the synchroniser; the preview renders
both the open and closed poses. Solid stony fingers keep every wall >> 2.4 mm.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Plane, Pos, Rot, Rotation, RegularPolygon, loft, fillet, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

# --- Params (law) ----------------------------------------------------------
N_FINGERS = int(_P["manipulators"]["fingers"])            # 3
GRIP_OPEN_RAD, GRIP_CLOSED_RAD = (float(v) for v in _P["manipulators"]["grip_limit_rad"])

# --- Palm (hosts the grip servo + the hidden synchroniser) -----------------
PALM_R = 38.0                                             # Ø76 stony palm
PALM_H = 20.0
Z_PIV = PALM_H / 2.0                                      # finger pivot height

# --- Finger (triangular Eridian-stone shard, solid) ------------------------
FINGER_LEN = 50.0
ROOT_R = 10.5                                             # root triangle circumradius
TIP_R = 6.0                                               # blunt tip
EDGE_FILLET = 2.5                                         # weather the shard edges (also
#   kills the acute-triangle-wedge that trips the min-wall ray screen)
R_PIV = PALM_R - 3.0                                      # hub centre radius (overlaps rim)
HUB_R = 12.0                                              # pivot knuckle radius (>= ROOT_R)
HUB_L = 16.0                                              # knuckle length along pivot axis
PIN_BORE = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_PRESS_MM     # Ø5 pivot pin / bearing pin

# --- EduLite grip-servo mount on the palm top face -------------------------
PILOT_DEPTH = 4.0
BOLT_DEPTH = 6.0                                         # blind flange bolts (keep >=2.4 mm
#   web to the drive-disc recess below: 16 - BOLT_DEPTH - DRIVE_DISC_DEPTH)
DRIVE_DISC_DIA = 40.0                                     # synchroniser (crown gear) recess
DRIVE_DISC_DEPTH = 6.0

META = PartMeta(
    name="grip_hand",
    material="PETG",
    qty=len(_P["manipulators"]["legs"]),                  # legs 1 & 4 -> qty 2
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="tree",
    inserts=(
        Insert("m4_clearance", 3, "grip-servo flange bolts, Ø41.5 PCD (M4)"),
        Insert("m3_clearance", 3, "grip-servo flange bolts, Ø41.5 PCD (M3)"),
        Insert("bearing_625zz", 3, "one finger pivot pin per finger"),
    ),
    clearances={"servo_flange": "slide", "output_bore": "loose", "pivot_pin": "press"},
)


def _finger(grip_rad: float, az_deg: float) -> Part:
    """One triangular stone finger, posed at `grip_rad` and placed at azimuth
    `az_deg`. Built canonical (pivot at origin, axis = Y, blade along +X and flat
    at grip 0), then swung about the pivot and rotated/translated to the rim."""
    # Tapered triangular blade, lofted along +Z (root -> twisted blunt tip), then
    # its edges weathered so the shard has no acute knife edges.
    root = Plane.XY * RegularPolygon(radius=ROOT_R, side_count=3)
    tip = Plane.XY.offset(FINGER_LEN) * Rot(0, 0, 18) * RegularPolygon(radius=TIP_R, side_count=3)
    blade = fillet(loft([root, tip]).edges(), radius=EDGE_FILLET)
    # Map +Z -> +X so the blade reaches radially; roll a flat facet to the floor.
    blade = Rotation(0, 90, 0) * blade
    blade = Rotation(30, 0, 0) * blade

    # Pivot knuckle (hub), axis = Y, concentric with the pivot so any swing keeps
    # it fused to the palm rim. Pin bore through it marks the finger pivot.
    hub = Rotation(90, 0, 0) * Cylinder(radius=HUB_R, height=HUB_L)
    pin = Rotation(90, 0, 0) * Cylinder(radius=PIN_BORE / 2, height=HUB_L + 2 * PALM_R)

    finger = (blade + hub) - pin

    # Swing about the pivot (canonical Y): grip 0 = flat, grip up = tip lifts +Z.
    finger = Rotation(0, -math.degrees(grip_rad), 0) * finger
    # Carry the pin bore straight through the palm at the swung-out azimuth.
    finger = Rotation(0, 0, az_deg) * finger
    return Pos(R_PIV * math.cos(math.radians(az_deg)),
               R_PIV * math.sin(math.radians(az_deg)), Z_PIV) * finger


def _palm() -> Part:
    """Stony palm puck + the real EduLite grip-servo flange on the top face + a
    central synchroniser (crown-gear) recess on the underside."""
    palm = Pos(0, 0, PALM_H / 2) * Cylinder(radius=PALM_R, height=PALM_H)
    top = PALM_H
    # EduLite grip-servo mount (servo coaxial above, output down into the palm).
    # Bolts start at the pilot-recess FLOOR (disjoint z-band) so the recess wall
    # and the bolt ring don't overlap into thin crescents (cf. leg_bracket floor).
    palm -= Pos(0, 0, top) * E.pilot_recess(PILOT_DEPTH, fit="slide")
    palm -= Pos(0, 0, top - PILOT_DEPTH) * E.bolt_holes(BOLT_DEPTH)
    palm -= Pos(0, 0, top) * E.output_bore(PALM_H + 2.0, fit="loose", extend_up=1.0)
    # Hidden synchroniser space (crown gear + finger pinions) on the underside.
    palm -= Pos(0, 0, DRIVE_DISC_DEPTH / 2) * Cylinder(radius=DRIVE_DISC_DIA / 2,
                                                       height=DRIVE_DISC_DEPTH)
    return palm


def grip_hand(grip_rad: float = GRIP_OPEN_RAD) -> Part:
    """The full hand at `grip_rad` (default open/flat = the printed pose)."""
    hand = _palm()
    for k in range(N_FINGERS):
        hand += _finger(grip_rad, k * 360.0 / N_FINGERS)
    return hand


def part() -> Part:
    return grip_hand(GRIP_OPEN_RAD)
