"""ROCKY-5 breathing carapace petal — one of five moving crown plates (§4, D-024).

Makes `rocky/carapace.py`'s 5-plate kinematics PHYSICAL. The top of the rock
dome (the crown, z >= Z_CROWN) is cut into five 72deg petals that slide RADIALLY
outward to "inhale" and are pulled back in by return springs to "exhale". All
five are driven synchronously by ONE central servo through a scroll/spiral cam
(`carapace_cam.py`) seated in the hub (`carapace_hub.py`) — a self-centering
5-jaw scroll-chuck mechanism, so one servo rotation moves every petal by the
same radial amount (= the A_BREATH term of carapace.plate_displacement_mm).

Each petal is a wedge of the dome shell (so it reads as continuous craggy stone
at rest) plus an underside SLIDER RIB that runs radially: the rib rides the hub's
matching radial guide, carries the cam FOLLOWER pin bore, and anchors the return
spring. Modeled at the neutral (mid-breath) radial position; qty 5.

HONESTY (see docs + D-024): the servo drives ONLY the slow ~0.25 Hz breathing.
The A_SPEECH 3 mm @ 22 Hz ripple is beyond any servo's mechanical bandwidth, so
the speech term is rendered by the seam LEDs (carapace_hub LED ring), not the
plates. The petals shingle/overlap so their 20 mm travel opens a glowing seam
rather than a bald gap.
"""
from __future__ import annotations

import math

from build123d import (
    Box, Cylinder, Pos, Rotation, Part,
    BuildPart, BuildSketch, Plane, Polygon, extrude,
)

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from rocky.cad.parts.carapace import shell, R, H, WALL

# --- Crown segmentation ----------------------------------------------------
N_PLATES = 5
SEG_DEG = 360.0 / N_PLATES            # 72deg petals
HALF_DEG = SEG_DEG / 2.0 - 1.2        # small kerf so adjacent petals never fuse
Z_CROWN = 58.0                        # crown base (above the fixed skirt seam at 55)

# --- Underside slider rib (rides the hub guide, carries follower + spring) ---
RIB_W = 12.0                          # rib width across the leg (Y)
RIB_H = 16.0                          # rib depth below the inner wall (Z)
RIB_R0 = 16.0                         # inner end of the rib (near the hub centre)
RIB_R1 = 62.0                         # outer end (fuses into the crown inner wall)
Z_RIB = Z_CROWN + 4.0                 # rib centre height
R_FOLLOW = 40.0                       # cam-follower pin radius (matches carapace_cam)
R_SPRING = 26.0                       # return-spring anchor radius
FOLLOW_BORE = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_PRESS_MM   # Ø5 follower pin
SPRING_BORE = 3.2                     # spring hook pocket


def _wedge(half_deg: float = HALF_DEG, radius: float = 400.0,
           z0: float = Z_CROWN - 30.0, z1: float = H + 20.0) -> Part:
    """A 72deg pie wedge (symmetric about +X) as a tall extruded triangle — the
    angular selector that carves one petal out of the dome crown."""
    a = math.radians(half_deg)
    x, y = radius * math.cos(a), radius * math.sin(a)
    with BuildPart() as w:
        with BuildSketch(Plane.XY.offset(z0)):
            Polygon((0.0, 0.0), (x, y), (x, -y))
        extrude(amount=z1 - z0)
    return w.part


def _crown_wedge() -> Part:
    """One petal's cosmetic shell: the crown band (z >= Z_CROWN) of the dome,
    carved to a single 72deg sector. Watertight (a thick-walled curved solid)."""
    crown = shell() & (Pos(0, 0, Z_CROWN + 200.0) * Box(600, 600, 400))
    return crown & _wedge()


def carapace_plate() -> Part:
    """One breathing petal at azimuth 0 (neutral radial position)."""
    petal = _crown_wedge()

    # Underside slider rib: a solid bar hanging radially inward from the crown
    # inner wall. It fuses to the wall (overlaps it) and provides the guide land,
    # the cam-follower boss and the spring anchor.
    rib_len = RIB_R1 - RIB_R0
    rib = Pos((RIB_R0 + RIB_R1) / 2.0, 0.0, Z_RIB) * Box(rib_len, RIB_W, RIB_H)
    petal += rib

    # Cam-follower pin bore (Ø5, vertical through the rib): the scroll cam's
    # spiral drives this pin radially -> the petal slides.
    petal -= Pos(R_FOLLOW, 0.0, Z_RIB) * Cylinder(radius=FOLLOW_BORE / 2, height=RIB_H + 6.0)
    # Return-spring anchor pocket (blind, opens downward toward the hub post).
    petal -= Pos(R_SPRING, 0.0, Z_RIB - 4.0) * Cylinder(radius=SPRING_BORE / 2, height=RIB_H)
    return petal


META = PartMeta(
    name="carapace_plate",
    material="PLA",
    qty=N_PLATES,                      # five identical crown petals
    cosmetic=True,                     # 1.6 mm cosmetic min-wall (rock shell)
    plate_group="rocky_shells",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 1, "cam-follower pin bore per petal (Ø5 pin)"),
    ),
    clearances={"guide_slide": "slide", "follower_pin": "press", "spring_anchor": "loose"},
)


def part() -> Part:
    return carapace_plate()
