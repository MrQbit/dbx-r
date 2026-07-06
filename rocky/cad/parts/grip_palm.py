"""ROCKY-5 grip PALM — the stony base of the front-manipulator hand (D-008, D-027).

The palm is the fixed member of the grip assembly. It:
  * BOLTS TO THE TIBIA via the real EduLite Ø41.5 PCD flange on its top face and
    HOUSES the grip servo (coaxial with the limb) — `common.cad_lib.edulite`;
  * HIDES THE DRIVE inside a wide stony base: the servo output drops down the
    centre into an underside cavity that houses the `grip_crown` cam disc, so no
    gear is ever exposed (Rocky reads as weathered rock, not machine);
  * CARRIES THE THREE FINGER HINGES: a clevis at each 120° azimuth on the pivot
    circle (`grip_finger.R_PIV/Z_PIV`) with a Ø5 pin bore, and a radial CRANK SLOT
    per finger so each finger's crank + follower pin reaches down to the crown.

Shape: a broad base cylinder (the crown housing + the shoulder the fingers rest
their roots on at grip 0) topped by a tapering stub that seats the servo. Prints
base-down; the underside crown cavity and the clevis undercuts want tree supports.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Cone, Box, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts.grip_finger import (
    R_PIV, Z_PIV, PIN_BORE, HUB_R, HUB_L, azimuths, N_HANDS,
    CRANK_INBOARD, FOLLOW_BOSS_R,
)

# --- Base (crown housing + finger-root shoulder) ---------------------------
BASE_R = 54.0                          # Ø108 stony base (hides the Ø100 crown)
BASE_H = 12.0                          # base cylinder height (z 0 .. BASE_H)

# --- Servo stub (seats the EduLite grip servo, coaxial with the limb) -------
STUB_R_BOT = 34.0                      # foot of the stub on the base top
STUB_R_TOP = 27.0                      # top face (Ø54 ≥ Ø46 housing / Ø41.5 PCD)
STUB_H = 14.0
Z_TOP = BASE_H + STUB_H                # servo mating face

# --- EduLite grip-servo mount on the top face ------------------------------
PILOT_DEPTH = 4.0
BOLT_DEPTH = 6.0                       # blind flange bolts
OUTPUT_BORE_LEN = STUB_H + BASE_H - 2.0  # centre bore, top face down to the crown cavity

# --- Underside crown cavity (houses grip_crown, hidden) --------------------
from rocky.cad.parts.grip_crown import CROWN_R, Z_TOP as CROWN_Z_TOP
CAVITY_R = CROWN_R + 1.0               # running clearance on the crown
CAVITY_TOP = CROWN_Z_TOP + 0.1        # cavity just clears the crown top ...
CAVITY_BOT = -1.0                      # ... and opens out the palm underside
# ceiling left below the base top = BASE_H - CAVITY_TOP (≥ 2.4 mm by construction)

# --- Finger clevis (pin hinge) ---------------------------------------------
EAR_W = 5.8                            # each clevis ear width (≥ 2.4 mm)
CLEVIS_GAP = HUB_L + 2 * S.FIT_SLIDE_MM  # slot the finger knuckle drops into
CLEVIS_SPAN = CLEVIS_GAP + 2 * EAR_W

# --- Crank slot (lets a finger's crank + follower pin reach the crown) ------
# Narrow slot through the shoulder/ceiling, BETWEEN the two clevis ears, so the
# finger's crank + follower pin pass down into the crown cavity and swing.
SLOT_W = 2 * FOLLOW_BOSS_R + 2 * S.FIT_LOOSE_MM   # crank/follower running width
SLOT_R0 = 24.0                         # covers the follower band (r ≈ 29 → 43)
SLOT_R1 = 45.0


def _servo_flange(palm: Part) -> Part:
    """Cut the EduLite grip-servo mount into the top face (pilot + PCD bolts +
    output bore down to the crown cavity). Same builders as leg_bracket seats."""
    palm -= Pos(0, 0, Z_TOP) * E.pilot_recess(PILOT_DEPTH, fit="slide")
    palm -= Pos(0, 0, Z_TOP - PILOT_DEPTH) * E.bolt_holes(BOLT_DEPTH)
    palm -= Pos(0, 0, Z_TOP) * E.output_bore(OUTPUT_BORE_LEN, fit="loose", extend_up=1.0)
    return palm


def grip_palm() -> Part:
    base = Pos(0, 0, BASE_H / 2) * Cylinder(radius=BASE_R, height=BASE_H)
    stub = Pos(0, 0, BASE_H + STUB_H / 2) * Cone(
        bottom_radius=STUB_R_BOT, top_radius=STUB_R_TOP, height=STUB_H)
    palm = base + stub

    # Underside crown cavity (opens downward; ceiling left above the crown).
    palm -= Pos(0, 0, (CAVITY_TOP + CAVITY_BOT) / 2) * Cylinder(
        radius=CAVITY_R, height=CAVITY_TOP - CAVITY_BOT)

    # EduLite grip-servo mount + central output bore to the crown.
    palm = _servo_flange(palm)

    # Three finger clevises + crank slots, at 120°.
    for az in azimuths():
        # Clevis: a knuckle straddling the pivot with a central slot for the
        # finger hub and a Ø5 pin bore.
        ear = Rotation(90, 0, 0) * Cylinder(radius=HUB_R, height=CLEVIS_SPAN)
        gap = Box(2 * HUB_R + 2, CLEVIS_GAP, 2 * HUB_R + 2)
        knuckle = ear - gap
        knuckle -= Rotation(90, 0, 0) * Cylinder(radius=PIN_BORE / 2, height=CLEVIS_SPAN + 2)
        knuckle = Pos(R_PIV, 0, Z_PIV) * knuckle
        palm += Rotation(0, 0, az) * knuckle

        # Crank slot through the shoulder/ceiling so the crank + follower reach
        # the crown cavity and can swing across the full grip range. Narrow
        # (passes between the clevis ears) and only through the ceiling band.
        slot = Pos((SLOT_R0 + SLOT_R1) / 2, 0, (Z_PIV + 6.0 + CAVITY_TOP - 1.0) / 2) * Box(
            SLOT_R1 - SLOT_R0, SLOT_W, (Z_PIV + 6.0) - (CAVITY_TOP - 1.0))
        palm -= Rotation(0, 0, az) * slot

    return palm


META = PartMeta(
    name="grip_palm",
    material="PETG",
    qty=N_HANDS,                        # one palm per grip hand
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="tree",
    inserts=(
        Insert("m4_clearance", 3, "grip-servo flange bolts, Ø41.5 PCD (M4)"),
        Insert("m3_clearance", 3, "grip-servo flange bolts, Ø41.5 PCD (M3)"),
        Insert("bearing_625zz", 3, "one Ø5 finger-pivot pin per clevis"),
    ),
    clearances={"servo_flange": "slide", "output_bore": "loose",
                "pivot_pin": "press", "crown_cavity": "loose", "crank_slot": "loose"},
)


def part() -> Part:
    return grip_palm()
