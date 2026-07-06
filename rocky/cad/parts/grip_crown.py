"""ROCKY-5 grip DRIVE CROWN — the one-servo-drives-three-fingers synchroniser
(front manipulators, D-008, D-027).

A flat disc that seats on the grip servo's Ø24 output collar (inside the palm,
hidden). Its top face carries THREE spiral cam grooves at 120°; each finger's
vertical follower pin (`grip_finger`) drops into one groove. When the servo turns
the crown, every follower rides an identical Archimedean ramp, so all three
fingers swing about their pivots by the SAME angle at once — a synchronised
3-jaw close from one motor, in perfect phase to within print tolerance.

WHY A CAM, NOT MESHING TEETH (honest, D-027)
--------------------------------------------
The spec described a "crown gear → 3 pinions". Real bevel/face-gear TEETH are the
wrong choice for THIS part on an FDM printer:
  * at this diameter a face gear needs a small module; the resulting ~1.5–2 mm
    tooth thickness is BELOW the 2.4 mm structural min-wall screen (G2) — the
    part would fail QA;
  * hand-rolled (non-involute) teeth do not mesh cleanly and jam/backlash badly
    when printed at 0.2 mm layers.
So — exactly like the breathing `carapace_cam.py` scroll chuck already in this
repo — the crown is a SPIRAL CAM: chunky walls (all ≥ 2.4 mm), backlash-tolerant,
and it prints flat with the grooves facing up (no supports). Grooves are cut as
chains of densely-overlapping drill hits so each is one clean watertight slot.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Box, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts.grip_finger import N_HANDS

# --- Crown disc (hidden under the palm, on the servo output collar) ---------
CROWN_R = 50.0                         # covers the finger follower circle (≤ palm base)
CROWN_T = 7.0                          # disc thickness
Z_BOT = 1.5                            # sits just up off the recess floor
Z_TOP = Z_BOT + CROWN_T

# --- Central output-collar interface (Ø24 EduLite collar, keyed) ------------
COLLAR_BORE = S.EDULITE_OUTPUT_COLLAR_DIA_MM + 2 * S.FIT_PRESS_MM   # press onto the collar
KEY_FLAT = 1.0                         # D-flat on the bore (anti-rotation key to the collar)

# --- Spiral follower grooves (three, at 120°) ------------------------------
N_GROOVES = 3
GROOVE_ARC_DEG = 70.0                  # angular length of each ramp (servo sweep window)
GROOVE_R_LO = 30.0                     # follower radius at the OPEN end (grip 0)
GROOVE_R_HI = 43.0                     # ... and the CLOSED end (rim wall ≥ 2.4 mm kept)
TOOL_DIA = 5.6                         # follower-pin Ø5 + running clearance
GROOVE_DEPTH = 4.0                     # blind slot in the top face (≥ 3 mm floor left)
_STEPS = 26                            # dense enough that hits overlap → watertight


def _spiral_grooves() -> Part:
    """Three 120° spiral ramps on the top face, each a chain of overlapping drill
    hits so the groove is a single clean watertight cut."""
    cut: Part | None = None
    zc = Z_TOP - GROOVE_DEPTH / 2
    half = math.radians(GROOVE_ARC_DEG) / 2.0
    for g in range(N_GROOVES):
        ang_c = math.radians(g * 360.0 / N_GROOVES)
        for k in range(_STEPS + 1):
            f = k / _STEPS
            ang = ang_c - half + f * (2 * half)
            r = GROOVE_R_LO + (GROOVE_R_HI - GROOVE_R_LO) * f
            hit = Pos(r * math.cos(ang), r * math.sin(ang), zc) * Cylinder(
                radius=TOOL_DIA / 2, height=GROOVE_DEPTH + 0.2)
            cut = hit if cut is None else cut + hit
    return cut


def grip_crown() -> Part:
    crown = Pos(0, 0, (Z_BOT + Z_TOP) / 2) * Cylinder(radius=CROWN_R, height=CROWN_T)

    # Spiral follower grooves on the top face.
    crown -= _spiral_grooves()

    # Central bore onto the servo output collar, with a D-FLAT that keys the crown
    # to the collar (anti-rotation) so servo rotation drives it. A flat (vs a
    # radial grub-screw cross-hole) keeps every wall thick on this thin disc.
    zc = (Z_BOT + Z_TOP) / 2
    crown -= Pos(0, 0, zc) * Cylinder(radius=COLLAR_BORE / 2, height=CROWN_T + 2)
    crown -= Pos(COLLAR_BORE / 2 - KEY_FLAT / 2, 0, zc) * Box(KEY_FLAT, COLLAR_BORE, CROWN_T + 2)
    return crown


META = PartMeta(
    name="grip_crown",
    material="PETG",
    qty=N_HANDS,                        # one crown per grip hand
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="none",                   # prints flat, grooves up (self-supporting)
    inserts=(),                        # keyed D-flat onto the servo output collar (no fastener)
    clearances={"output_collar": "press", "follower_groove": "slide"},
)


def part() -> Part:
    return grip_crown()
