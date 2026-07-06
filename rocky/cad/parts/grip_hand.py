"""ROCKY-5 grip HAND — the ASSEMBLY of the three printed grip parts (D-008, D-027).

The hand is no longer one fused solid. It is a real mechanism split into three
separately-printed, separately-registered parts:

  * `grip_palm`   — stony base: bolts to the tibia via the EduLite Ø41.5 PCD
                    flange, houses the grip servo, hides the drive, carries the
                    three finger hinges.                              (qty 2)
  * `grip_crown`  — spiral cam disc on the servo Ø24 output collar; its three
                    120° grooves drive all three finger followers in sync. (qty 2)
  * `grip_finger` — one Eridian-stone finger with a Ø5 pivot bore + a follower
                    pin on a crank.                                    (qty 6)

ONE grip servo turns the crown → three follower pins ride identical spiral
grooves → three fingers close in phase. This module is NOT registered/printed;
it just poses the three real parts into a hand at a given `grip_rad` for the
preview render (`scripts/render_grip_mech.py`) and for assembly interference
checks. See the part modules for the printable geometry and D-027 for the honest
teeth-vs-cam call and the closed-pose grasp numbers.
"""
from __future__ import annotations

from build123d import Part

from rocky.cad.parts.grip_finger import (
    GRIP_OPEN_RAD, GRIP_CLOSED_RAD, N_FINGERS, azimuths, finger_placed,
)
from rocky.cad.parts.grip_palm import grip_palm
from rocky.cad.parts.grip_crown import grip_crown


def assembly(grip_rad: float = GRIP_OPEN_RAD) -> Part:
    """Palm + crown + three fingers, fused into one solid at pose `grip_rad`
    (default open/flat). For rendering / a quick look — not a printed part."""
    hand = grip_palm() + grip_crown()
    for az in azimuths():
        hand += finger_placed(grip_rad, az)
    return hand


def part() -> Part:
    """Back-compat: the open-pose assembled hand (used by the stance render's STL
    glob). The registered, QA'd, printed parts are grip_palm / grip_crown /
    grip_finger — NOT this fused solid."""
    return assembly(GRIP_OPEN_RAD)
