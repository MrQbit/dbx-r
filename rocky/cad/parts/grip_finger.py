"""ROCKY-5 grip THUMB + shared 2+1 hand geometry (front manipulators; D-008, D-027,
D-038 "2 primaries + 1 opposing thumb").

OPERATOR REDESIGN (D-038): the hand is no longer 3 symmetric fingers on a fat Ø108
crown disc. It is a **2 + 1** manipulator on a SLIM wrist, referenced from the
sculpt manipulator (docs/media/rocky_hands_before.png — a slim bent wrist ending in
tapered stone digits):

  * TWO PRIMARY fingers sit low and together and converge into a single spider-leg
    WALKING TIP — Rocky stands/walks on these fingertips, not the palm. They are
    RIGID (fused into the slim palm, `grip_palm.py`) so the foot never wobbles under
    body weight.
  * ONE THUMB (this module) is set slightly higher on the palm and OPPOSES the two.
    It is the single MOVING digit: it pivots on a Ø5 pin through a clevis and is
    driven by the grip micro-servo through a hidden crank + follower pin
    (`grip_crown.py`, tucked in the slim wrist).
      - grip OPEN  (0.0 rad): thumb raised/back out of the way -> the two primaries
        present a clean foot-tip to stand on.
      - grip CLOSED (2.2 rad): thumb swings down/forward and PINCHES an object
        against the two primary tips -> a firm 3-point grasp.

This module is the geometric single-source-of-truth for the hand FRAME (mount,
wrist, primary roots, thumb pivot, servo/drive stations, grip range). `grip_palm`
and `grip_crown` import from here so the clevis, pin bores, primaries and drive all
land on the same geometry. `part()` prints ONE thumb (qty = one per hand).

Hand LOCAL frame: Z = distal / outward (the limb axis; the wrist bolts to the tibia
tip flange at z=0 and the digits extend +Z), X = opposition (+X = thumb side,
-X = primary/foot side), Y = lateral (the two primaries splay ±Y).
"""
from __future__ import annotations

import math

from build123d import (
    Box, Cylinder, Plane, Pos, Rot, Rotation, RegularPolygon, loft, fillet, Part,
)

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

# --- Hand population (shared) ----------------------------------------------
N_PRIMARY = 2                                             # two primary (foot) fingers, fused to the palm
N_FINGERS = int(_P["manipulators"]["fingers"])           # 3 digits total = 2 primary + 1 thumb
N_HANDS = len(_P["manipulators"]["legs"])                # one 2+1 hand per manipulator leg
GRIP_OPEN_RAD, GRIP_CLOSED_RAD = (float(v) for v in _P["manipulators"]["grip_limit_rad"])

# --- Wrist / mount (SINGLE SOURCE OF TRUTH — palm imports these) -----------
MOUNT_R = 26.0            # Ø52 mount collar that catches the tibia's Ø41.5 PCD flange
COLLAR_H = 6.0           # mount-collar thickness
CONE_TOP_Z = 16.0        # collar -> slim-wrist taper ends here
WRIST_R = 17.0           # Ø34 SLIM wrist (was a Ø108 crown disc)
WRIST_TOP_Z = 44.0       # distal end of the wrist body (digit roots live here)
PIN_BORE = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_PRESS_MM     # Ø5 thumb-pivot pin

# --- Grip micro-servo (components.GRIP_SERVO 22.8 x 12.2 x 28.5) + drive ----
SERVO_BOX = (22.8, 12.2, 28.5)
SERVO_X = -1.0           # servo body centre X inside the wrist (tucked toward -X)
SERVO_Y0 = -6.5          # servo body -Y face
SERVO_Z0 = 11.0          # servo body base Z
DRIVE_Y = 8.0            # servo output shaft plane (+Y face of the servo, the crank rides here)
DRIVE_STATION = (5.0, 18.0)   # (x, z) of the grip-servo output axis (the crank hub centre)
DRIVE_CRANK_R = 9.0      # servo crank throw (follower pin radius on the crank)
FOLLOW_BORE = PIN_BORE   # Ø5 follower pin (crank <-> thumb tail slot)

# --- Thumb pivot (opposing, set slightly higher on the palm) ---------------
THUMB_PIV = (12.0, 0.0, 34.0)                            # pivot point (axis = Y)
THUMB_OPEN_A = 1.35                                      # thumb angle (about +Y) at grip 0 (raised/back)
THUMB_CLOSED_A = -0.60                                   # ... and at grip CLOSED (down/forward, pinching)

# --- Primary fingers (fused into the palm; geometry lives here for the render) ---
PRIM_ROOT = (-7.0, 0.0, WRIST_TOP_Z - 4.0)              # the pair's shared root centre on the wrist
PRIM_SPLAY_DEG = 12.0                                   # each primary splayed ±this in Y (tips converge)
PRIM_LEAN_DEG = 22.0                                    # ... and leaned toward -X (over the foot point)
PRIM_LEN = 46.0                                         # pivot -> blunt walking tip

# --- Stony digit blade (tapered triangular Eridian shard, weathered edges) --
ROOT_R = 10.0            # blade root circumradius
TIP_R = 6.5             # blunt tip circumradius (blunt -> passes the min-wall screen)
EDGE_FILLET = 3.0

# --- Thumb knuckle hub + crank tail ----------------------------------------
HUB_R = 8.0             # Ø16 knuckle (wall ≥ 5 mm on the Ø5 pivot bore)
HUB_L = 14.0            # length along the pivot axis (Y)
CRANK_DROP = 15.5      # crank tail length (-Z below the pivot; keeps the follower bore
#                        clear of the pivot bore by ≥2.4 mm)
CRANK_BOSS_R = 5.7     # Ø11.4 follower foot on the tail (wall ≥ 2.8 mm on Ø5 bore)
THUMB_LEN = 44.0       # pivot -> blunt thumb tip


def azimuths() -> list[float]:
    """Back-compat shim: the two primary splay angles (deg) about the pair root."""
    return [+PRIM_SPLAY_DEG, -PRIM_SPLAY_DEG]


def _blade(length: float, root_r: float, tip_r: float, twist: float = 16.0) -> Part:
    """A tapered triangular stone blade along +Z (root at origin), edges weathered."""
    root = Plane.XY * RegularPolygon(radius=root_r, side_count=3)
    tip = Plane.XY.offset(length) * Rot(0, 0, twist) * RegularPolygon(radius=tip_r, side_count=3)
    return fillet(loft([root, tip]).edges(), radius=EDGE_FILLET)


def _thumb_canonical() -> Part:
    """The thumb in its own frame: pivot at origin, pivot axis = Y, blade along +Z,
    a crank tail hanging -Z with a follower-pin boss. Returned unposed (printable)."""
    blade = Pos(0, 0, HUB_R * 0.2) * _blade(THUMB_LEN, ROOT_R, TIP_R)

    hub = Rotation(90, 0, 0) * Cylinder(radius=HUB_R, height=HUB_L)       # knuckle, axis Y

    # Crank tail: a stubby slab hanging below the pivot; its foot carries the Ø5
    # follower pin that the grip_crown drive crank pushes (the hidden cam/link).
    tail = Pos(0, 0, -CRANK_DROP / 2) * Box(2 * CRANK_BOSS_R, HUB_L, CRANK_DROP + 2)

    thumb = blade + hub + tail

    # Ø5 pivot bore (through the hub, along Y) and Ø5 follower bore (through the
    # tail foot, along Y) — both take a 625ZZ-class steel pin.
    thumb -= Rotation(90, 0, 0) * Cylinder(radius=PIN_BORE / 2, height=HUB_L + 2 * HUB_R)
    thumb -= Pos(0, 0, -CRANK_DROP + CRANK_BOSS_R) * Rotation(90, 0, 0) * Cylinder(
        radius=FOLLOW_BORE / 2, height=HUB_L + 2)
    return thumb


def thumb_placed(grip_rad: float) -> Part:
    """The thumb swung to `grip_rad` and placed on its palm pivot (for the assembly
    render + interference checks; not the printed pose)."""
    a = THUMB_OPEN_A + (grip_rad / GRIP_CLOSED_RAD) * (THUMB_CLOSED_A - THUMB_OPEN_A)
    t = Rotation(0, math.degrees(a), 0) * _thumb_canonical()
    return Pos(*THUMB_PIV) * t


def _primary_placed(splay_deg: float) -> Part:
    """One primary (foot) finger, leaned over the foot point and splayed ±Y. Fused
    into the palm by grip_palm; modelled here so the render/reports share the same
    geometry. Canonical blade is built along +Z then leaned toward -X and splayed."""
    f = _blade(PRIM_LEN, ROOT_R, TIP_R)
    f = Rotation(0, -PRIM_LEAN_DEG, 0) * f                 # lean toward -X (over the foot point)
    f = Rotation(0, 0, splay_deg) * f                      # splay ±Y so the two tips converge
    return Pos(*PRIM_ROOT) * f


def primaries() -> Part:
    """The two fused primary fingers (a walking tip). Used by grip_palm + the render."""
    a, b = azimuths()
    return _primary_placed(a) + _primary_placed(b)


def primary_tip_xyz() -> tuple[float, float, float]:
    """Approx walking-tip position (the converged primary fingertips), for reports."""
    lean = math.radians(PRIM_LEAN_DEG)
    x = PRIM_ROOT[0] - PRIM_LEN * math.sin(lean)
    z = PRIM_ROOT[2] + PRIM_LEN * math.cos(lean)
    return (round(x, 1), 0.0, round(z, 1))


def thumb_tip_xyz(grip_rad: float) -> tuple[float, float, float]:
    """Approx thumb-tip position at a grip pose, for reports."""
    a = THUMB_OPEN_A + (grip_rad / GRIP_CLOSED_RAD) * (THUMB_CLOSED_A - THUMB_OPEN_A)
    x = THUMB_PIV[0] + THUMB_LEN * math.sin(a)
    z = THUMB_PIV[2] + THUMB_LEN * math.cos(a)
    return (round(x, 1), 0.0, round(z, 1))


# Back-compat alias used by older render helpers.
def finger_placed(grip_rad: float, az_deg: float = 0.0) -> Part:
    return thumb_placed(grip_rad)


def fingertip_xyz(grip_rad: float, az_deg: float = 0.0) -> tuple[float, float, float]:
    return thumb_tip_xyz(grip_rad)


META = PartMeta(
    name="grip_finger",
    material="PETG",
    qty=N_HANDS,                                         # one THUMB per 2+1 hand
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 1, "Ø5 thumb-pivot pin (thumb ↔ palm clevis)"),
        Insert("dowel_5x20", 1, "Ø5 follower pin (thumb tail ↔ grip_crown drive crank)"),
    ),
    clearances={"pivot_pin": "press", "follower_pin": "press"},
)


def part() -> Part:
    """One thumb, canonical (printable) pose."""
    return _thumb_canonical()
