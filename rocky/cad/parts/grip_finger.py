"""ROCKY-5 grip FINGER — one of three separately-printed Eridian-stone fingers
(front manipulators, legs 1 & 4; §4, D-008, D-027).

The grip hand is a real assembly now (not one fused solid): a stony PALM
(`grip_palm.py`) that bolts to the tibia and houses the grip servo, a central
DRIVE CROWN (`grip_crown.py`) on the servo output, and THREE of THESE fingers.
One servo turns the crown; the crown's three spiral cam grooves push each
finger's follower pin, so all three fingers swing about their pivots by the same
angle (`grip_rad`) — synchronised close, one motor.

This module is the geometric single-source-of-truth for the finger PIVOT circle
(`R_PIV`, `Z_PIV`, the 120° azimuths) and the Ø5 pin interfaces; `grip_palm` and
`grip_crown` import these so the pivot bosses, crank slots and cam grooves all
land on the same geometry.

Each finger is a separate print (qty 3 × 2 hands = 6), modeled CANONICAL: pivot
at the origin, pivot axis = Y, stony blade along +X and flat at grip 0. It carries
  * a knuckle HUB with a Ø5 pivot-pin bore (finger ↔ palm hinge, a 625ZZ pin),
  * a short CRANK below/inboard of the pivot ending in a vertical follower-pin
    boss (Ø5) that rides the crown's cam groove (finger ↔ crown drive).
The blade edges are filleted so the shard reads as weathered rock, not machined,
and so no acute wedge trips the min-wall ray screen.

Kinematics (forward, exact — the cam only sets HOW the servo drives it):
  ρ_tip(θ) = R_PIV + FINGER_LEN·cos(θ),   z_tip(θ) = Z_PIV + FINGER_LEN·sin(θ)
  θ = 0     → tips at ρ = R_PIV+FINGER_LEN, flat/splayed  (a broad tripod SOLE)
  θ = 2.2   → tips swing UP and PAST vertical, ρ ≈ 11 mm  (a firm 3-jaw GRASP)
See docs/reports + D-027 for the closed-pose fingertip gap and grip envelope.
"""
from __future__ import annotations

import math

from build123d import (
    Cylinder, Plane, Pos, Rot, Rotation, RegularPolygon, loft, fillet, Part,
)

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

# --- Finger population (shared) --------------------------------------------
N_FINGERS = int(_P["manipulators"]["fingers"])            # 3 per hand
N_HANDS = len(_P["manipulators"]["legs"])                 # one grip hand per manipulator leg
GRIP_OPEN_RAD, GRIP_CLOSED_RAD = (float(v) for v in _P["manipulators"]["grip_limit_rad"])

# --- Pivot circle (SINGLE SOURCE OF TRUTH — palm + crown import these) ------
R_PIV = 38.0                                              # finger-pivot radius
Z_PIV = 13.0                                              # pivot height on the palm flank
PIN_BORE = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_PRESS_MM     # Ø5 pivot pin (625ZZ)

def azimuths() -> list[float]:
    """The 120° finger azimuths (degrees)."""
    return [k * 360.0 / N_FINGERS for k in range(N_FINGERS)]

# --- Finger blade (tapered triangular Eridian-stone shard) -----------------
FINGER_LEN = 46.0                                         # pivot → blunt tip
ROOT_R = 11.0                                             # root triangle circumradius
TIP_R = 7.0                                               # blunt tip circumradius (blunt → passes min-wall)
EDGE_FILLET = 3.0                                         # weather the shard edges

# --- Knuckle hub + pivot pin -----------------------------------------------
HUB_R = 9.0                                               # Ø18 knuckle (wall ≥ 6 mm on Ø5 bore)
HUB_L = 16.0                                              # length along the pivot axis

# --- Crank + follower pin (finger ↔ crown drive) ---------------------------
# A short crank hangs inboard/below the pivot; a vertical Ø5 follower pin at its
# tip rides the crown's spiral cam groove. Kept SHORT so the follower stays over
# the (hidden) crown across the whole 0 → 2.2 rad swing.
CRANK_INBOARD = 8.0                                       # follower boss offset −X of the pivot
#   (≥ 7.6 mm keeps the vertical follower bore clear of the horizontal pivot bore)
CRANK_DROP = 0.0                                          # follower boss on the pivot axis height
FOLLOW_BOSS_R = 5.5                                       # Ø11 boss (wall ≥ 2.9 mm on Ø5 bore)
FOLLOW_BOSS_H = 20.0                                      # long enough to reach into the crown groove
FOLLOW_BORE = PIN_BORE                                    # Ø5 follower pin


def _finger_canonical() -> Part:
    """One finger in the canonical frame: pivot at origin, pivot axis = Y, stony
    blade along +X and flat (grip 0). Returned unposed — the printable pose."""
    # Tapered triangular blade, lofted root → twisted blunt tip, edges weathered.
    root = Plane.XY * RegularPolygon(radius=ROOT_R, side_count=3)
    tip = Plane.XY.offset(FINGER_LEN) * Rot(0, 0, 18) * RegularPolygon(radius=TIP_R, side_count=3)
    blade = fillet(loft([root, tip]).edges(), radius=EDGE_FILLET)
    blade = Rotation(0, 90, 0) * blade                    # map +Z → +X (blade reaches radially)
    blade = Rotation(30, 0, 0) * blade                    # roll a flat facet to the floor

    # Knuckle hub (axis = Y), concentric with the pivot so any swing keeps it fused
    # to the blade root; Ø5 pivot-pin bore straight through.
    hub = Rotation(90, 0, 0) * Cylinder(radius=HUB_R, height=HUB_L)

    # Crank + follower-pin boss: a stubby post hanging inboard/below the pivot,
    # overlapping the hub so it fuses watertight.
    boss = Pos(-CRANK_INBOARD, 0, -CRANK_DROP) * Cylinder(radius=FOLLOW_BOSS_R, height=FOLLOW_BOSS_H)

    finger = blade + hub + boss

    # Pivot-pin bore (Ø5 along Y) and follower-pin bore (Ø5 along Z).
    finger -= Rotation(90, 0, 0) * Cylinder(radius=PIN_BORE / 2, height=HUB_L + 2 * HUB_R)
    finger -= Pos(-CRANK_INBOARD, 0, -CRANK_DROP) * Cylinder(radius=FOLLOW_BORE / 2,
                                                             height=FOLLOW_BOSS_H + 2)
    return finger


def finger_placed(grip_rad: float, az_deg: float) -> Part:
    """A finger swung to `grip_rad` and placed at azimuth `az_deg` on the pivot
    circle — used by the assembly render and interference checks (not printed)."""
    f = _finger_canonical()
    f = Rotation(0, -math.degrees(grip_rad), 0) * f       # swing: grip 0 = flat, up = tip lifts
    f = Rotation(0, 0, az_deg) * f                        # to its 120° azimuth
    return Pos(R_PIV * math.cos(math.radians(az_deg)),
               R_PIV * math.sin(math.radians(az_deg)), Z_PIV) * f


def fingertip_xyz(grip_rad: float, az_deg: float) -> tuple[float, float, float]:
    """Forward-kinematics fingertip position (blade tip) at a pose — for reports."""
    rho = R_PIV + FINGER_LEN * math.cos(grip_rad)
    z = Z_PIV + FINGER_LEN * math.sin(grip_rad)
    a = math.radians(az_deg)
    return (rho * math.cos(a), rho * math.sin(a), z)


META = PartMeta(
    name="grip_finger",
    material="PETG",
    qty=N_FINGERS * N_HANDS,                              # 3 fingers × one hand per manipulator leg
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 1, "Ø5 pivot pin (finger ↔ palm hinge)"),
        Insert("bearing_625zz", 1, "Ø5 follower pin (finger ↔ crown cam groove)"),
    ),
    clearances={"pivot_pin": "press", "follower_pin": "press"},
)


def part() -> Part:
    """One finger, canonical (printable) pose."""
    return _finger_canonical()
