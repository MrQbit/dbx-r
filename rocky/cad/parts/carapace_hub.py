"""ROCKY-5 breathing hub — the stationary carrier for the crown mechanism (D-024).

Sits inside the dome apex, above the core tub, and hosts everything that drives
the five breathing petals (`carapace_plate.py`):

  * central micro-servo pocket (components.BREATH_SERVO, MG90S-class) — ONE servo
    that turns the scroll cam (`carapace_cam.py`);
  * five RADIAL GUIDE SLOTS at 72deg — each receives a petal's slider rib so the
    petal can only translate radially (the linear guide);
  * five RETURN-SPRING posts near the centre — the springs pull the petals back
    in (exhale); the cam only has to push them out (inhale);
  * an LED RING CHANNEL near the rim (Task 2 / D-024): a shallow annular seat for
    a hidden WS2812 ring. The five guide ribs cross the ring, dividing it into the
    five arc segments (components.SEAM_LED, qty 5) that backlight each petal seam
    so Rocky glows along the gaps when he breathes/speaks. No LED is ever exposed.
  * a central shaft bore + three rim M3 bosses that fix the hub to the structure.

Structural (PETG); everything keys off components.py so re-sourcing the servo or
LED resizes the seats.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Box, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.components import BREATH_SERVO, SEAM_LED
from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts.carapace_plate import (
    N_PLATES, RIB_W, R_SPRING, Z_CROWN,
)

# --- Hub disc --------------------------------------------------------------
R_HUB = 66.0
Z_TOP = Z_CROWN - 2.0                  # top face just below the crown base
T_HUB = 14.0
Z_BOT = Z_TOP - T_HUB

# --- Radial guide slots (receive the petal ribs) ---------------------------
SLOT_W = RIB_W + 2 * S.FIT_SLIDE_MM    # sliding fit on the petal rib
SLOT_R0 = 30.0                         # inner end (clears the servo pocket)
SLOT_R1 = R_HUB                        # runs out to the rim
SLOT_DEPTH = 8.0                       # leaves a >= 6 mm floor

# --- LED ring channel (hidden WS2812 seam backlight) -----------------------
LED_R = 59.0                           # ring radius (under the petal seams)
LED_W = SEAM_LED.dims_mm[1] + 2.0      # channel width from the strip box (+slack)
LED_DEPTH = SEAM_LED.dims_mm[2] + 1.0  # channel depth from the strip box

# --- Return-spring posts ---------------------------------------------------
POST_R = R_SPRING - 6.0                # anchor radius (inboard of the petal anchor)
POST_RAD = 2.5
POST_H = 6.0

M3_HOLE = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
M2_HOLE = S.M2_INSERT_HOLE_DIA_MM


def carapace_hub() -> Part:
    hub = Pos(0, 0, (Z_TOP + Z_BOT) / 2) * Cylinder(radius=R_HUB, height=T_HUB)

    # --- Central servo well: MG90S-class body through the hub + 2 flange screws.
    sl, sw, sh = BREATH_SERVO.dims_mm                      # (22.8, 12.2, 28.5)
    clr = S.FIT_SLIDE_MM
    hub -= Pos(0, 0, (Z_TOP + Z_BOT) / 2) * Box(sl + 2 * clr, sw + 2 * clr, T_HUB + 2)
    for lug_x in (+ (sl / 2 + 5.0), - (sl / 2 + 5.0)):    # flange lugs clear of the well wall
        hub -= Pos(lug_x, 0, (Z_TOP + Z_BOT) / 2) * Cylinder(radius=M2_HOLE / 2, height=T_HUB + 2)
    # Output-shaft clearance up to the cam (central Ø6 bore).
    hub -= Pos(0, 0, Z_TOP) * Cylinder(radius=3.0, height=T_HUB + 2)

    # --- LED ring channel: shallow annulus on the top face (backlights seams).
    ring = (Pos(0, 0, Z_TOP - LED_DEPTH / 2) * Cylinder(radius=LED_R + LED_W / 2, height=LED_DEPTH + 0.2)
            - Pos(0, 0, Z_TOP - LED_DEPTH / 2) * Cylinder(radius=LED_R - LED_W / 2, height=LED_DEPTH + 0.2))
    hub -= ring

    # --- Five radial guide slots + a spring post at each 72deg petal centre. ---
    for k in range(N_PLATES):
        az = k * 360.0 / N_PLATES
        slot = Pos((SLOT_R0 + SLOT_R1) / 2, 0, Z_TOP - SLOT_DEPTH / 2) * Box(
            SLOT_R1 - SLOT_R0, SLOT_W, SLOT_DEPTH + 0.2)
        hub -= Rotation(0, 0, az) * slot
        post = Pos(POST_R, 0, Z_TOP + POST_H / 2) * Cylinder(radius=POST_RAD, height=POST_H)
        hub += Rotation(0, 0, az) * post

    # --- Three rim M3 bosses (fix the hub to the structure), between the slots.
    for k in range(3):
        az = math.radians(36 + k * 120)
        x, y = (R_HUB - 6.0) * math.cos(az), (R_HUB - 6.0) * math.sin(az)
        hub -= Pos(x, y, (Z_TOP + Z_BOT) / 2) * Cylinder(radius=M3_HOLE / 2, height=T_HUB + 2)

    return hub


META = PartMeta(
    name="carapace_hub",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("m3_heatset", 3, "rim bosses fixing the hub to the structure"),
        Insert("m2_selftap", 2, "central breathing-servo flange screws"),
    ),
    clearances={"servo_well": "slide", "guide_slot": "slide",
                "shaft_bore": "loose", "led_ring": "loose"},
)


def part() -> Part:
    return carapace_hub()
