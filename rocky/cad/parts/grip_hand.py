"""ROCKY-5 grip HAND — the ASSEMBLY of the 2+1 manipulator (D-008, D-027, D-038).

The hand is a real mechanism split into separately-printed, separately-registered
parts:

  * `grip_palm`   — SLIM wrist: bolts to the tibia via the EduLite Ø41.5 PCD flange,
                    fuses the TWO PRIMARY fingers (the rigid walking tip), carries the
                    thumb clevis, and hides the drive in a Y-split bay.        (qty 5)
  * `grip_finger` — the THUMB: one moving Eridian-stone digit on a Ø5 pivot with a
                    crank tail.                                                (qty 5)
  * `grip_crown`  — the hidden DRIVE CRANK on the micro-servo horn; its Ø5 follower
                    pin swings the thumb tail.                                 (qty 5)

ONE grip micro-servo turns the drive crank → the follower pin pushes the thumb tail
→ the thumb swings. grip 0 = thumb raised so the two primaries stand as a foot-tip;
grip 2.2 = thumb pinches an object against the two primary tips. This module is NOT
registered/printed; it just poses the real parts into a hand at a given `grip_rad`
for the preview render (`scripts/render_grip_mech.py`, `scripts/build_leg_chassis.py`)
and for assembly checks. See the part modules + D-038 for the printable geometry.
"""
from __future__ import annotations

import math

from build123d import Pos, Rotation, Part

from rocky.cad.parts.grip_finger import (
    GRIP_OPEN_RAD, GRIP_CLOSED_RAD, DRIVE_STATION, DRIVE_CRANK_R, thumb_placed,
)
from rocky.cad.parts.grip_palm import grip_palm
from rocky.cad.parts.grip_crown import grip_crown


def _crank_angle(grip_rad: float) -> float:
    """Illustrative crank angle (deg about +Y) that tracks the thumb sweep — the
    exact 4-bar timing is set at assembly; here it just shows the crank turning."""
    frac = grip_rad / GRIP_CLOSED_RAD
    return 90.0 - 150.0 * frac


def assembly(grip_rad: float = GRIP_OPEN_RAD) -> Part:
    """Slim palm (+ 2 fused primaries) + thumb + hidden drive crank, fused into one
    solid at pose `grip_rad` (default open / foot-tip). For rendering — not printed."""
    hand = grip_palm() + thumb_placed(grip_rad)
    dx, dz = DRIVE_STATION
    hand += Pos(dx, 0, dz) * Rotation(0, _crank_angle(grip_rad), 0) * grip_crown()
    return hand


def part() -> Part:
    """Back-compat: the open-pose assembled hand (used by the stance render's STL
    glob). The registered, QA'd, printed parts are grip_palm / grip_finger /
    grip_crown — NOT this fused solid."""
    return assembly(GRIP_OPEN_RAD)
