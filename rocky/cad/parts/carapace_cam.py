"""ROCKY-5 breathing scroll cam — the ONE-servo-drives-FIVE-petals part (D-024).

A flat scroll plate (like a self-centering lathe chuck's scroll): the central
breathing servo rotates this disc, and its Archimedean spiral groove drives all
five petal follower pins radially at once, in perfect sync. Rotate one way =
inhale (petals pushed out); the return springs pull them back on the way back =
exhale. Because every follower rides the SAME spiral, the five petals stay in
phase to within print tolerance — no linkage per petal.

Travel math (honest, see docs/reports + D-024): petal radial travel = pitch x
(servo_sweep / 360deg). At the modeled pitch (~40 mm/turn effective) a 180deg
hobby-servo sweep gives the ~20 mm A_BREATH stroke; a gentler resting breath uses
a smaller sweep. This is the slow (~0.25 Hz) breathing channel ONLY — the servo
cannot do the 3 mm @ 22 Hz speech ripple (that is LED-only, carapace_hub).

Altitude (cf. grip_hand.py): the printed part is the scroll disc + a servo-horn
interface + the spiral groove as a follower track; a production scroll uses a
flat spiral thread meshing racks on the petal ribs. QDD-free, cheap, printable.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts.carapace_hub import Z_TOP        # cam sits on the hub top face

# --- Scroll disc -----------------------------------------------------------
R_CAM = 50.0                           # keeps a >= 2.4 mm rim outboard of the ramps
T_CAM = 10.0
Z_BOT = Z_TOP + 0.5                    # rests just above the hub top face
Z_TOP_FACE = Z_BOT + T_CAM

# --- Scroll follower slots: five short spiral ramps at 72deg ----------------
# One per petal follower (matching carapace_plate R_FOLLOW). Each slot ramps the
# follower radius as the disc turns, so a single servo rotation moves all five in
# sync — a 5-jaw scroll. Modeled as densely-overlapping drill hits (watertight).
N_SLOTS = 5
SLOT_ARC_DEG = 58.0                    # angular length of each ramp
SLOT_R_LO = 33.0                       # follower radius at one slot end
SLOT_R_HI = 45.0                       # ... and the other (12 mm ramp per slot)
TOOL_DIA = 4.6                         # follower-pin Ø + clearance
GROOVE_DEPTH = 3.5
_STEPS_PER_SLOT = 24                   # dense enough that hits overlap (watertight)

# --- Servo-horn interface (centre) -----------------------------------------
# MG90S-class horns fasten with ONE central self-tapping screw into the output
# spline, so the interface is a central bore + a recess that seats the horn body.
SHAFT_BORE = 4.0                       # central horn screw into the servo spline
HORN_RECESS_DIA = 18.0                 # horn body seats flush in the disc underside
HORN_RECESS_DEPTH = 3.0


def _spiral_groove() -> Part:
    """The follower track: five short spiral ramps at 72deg, each a chain of
    densely-overlapping drill hits (so the groove is one clean watertight cut)."""
    cut: Part | None = None
    zc = Z_TOP_FACE - GROOVE_DEPTH / 2
    half = math.radians(SLOT_ARC_DEG) / 2.0
    for s in range(N_SLOTS):
        ang_c = math.radians(s * 360.0 / N_SLOTS)
        for k in range(_STEPS_PER_SLOT + 1):
            f = k / _STEPS_PER_SLOT
            ang = ang_c - half + f * (2 * half)
            r = SLOT_R_LO + (SLOT_R_HI - SLOT_R_LO) * f
            x, y = r * math.cos(ang), r * math.sin(ang)
            hit = Pos(x, y, zc) * Cylinder(radius=TOOL_DIA / 2, height=GROOVE_DEPTH + 0.2)
            cut = hit if cut is None else cut + hit
    return cut


def carapace_cam() -> Part:
    cam = Pos(0, 0, (Z_BOT + Z_TOP_FACE) / 2) * Cylinder(radius=R_CAM, height=T_CAM)

    # Spiral follower groove on the top face.
    cam -= _spiral_groove()

    # Servo-horn interface on the underside: central screw bore + horn seat.
    cam -= Pos(0, 0, (Z_BOT + Z_TOP_FACE) / 2) * Cylinder(radius=SHAFT_BORE / 2, height=T_CAM + 2)
    cam -= Pos(0, 0, Z_BOT + HORN_RECESS_DEPTH / 2) * Cylinder(radius=HORN_RECESS_DIA / 2,
                                                              height=HORN_RECESS_DEPTH)
    return cam


META = PartMeta(
    name="carapace_cam",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="none",
    inserts=(Insert("m2_selftap", 1, "central servo-horn screw"),),
    clearances={"shaft_bore": "loose", "horn_recess": "slide", "follower_track": "slide"},
)


def part() -> Part:
    return carapace_cam()
