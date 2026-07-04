"""ROCKY-5 belly plate — hosts the Qi 15 W receiver (wireless charging improvement).

Bolts under the core plate; the RX coil sits in a downward-facing pocket so it
aligns over the charging base's transmitter when Rocky parks on the dock. Pocket
size comes from components.py (QI_RX), so sourcing a different Qi module updates
this and the dock together.
"""

from __future__ import annotations

from build123d import Cylinder, Box, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.components import QI_RX
from common.cad_lib.part_meta import Insert, PartMeta

PLATE_R = 38.0
PLATE_H = 9.0   # >= RX pocket depth + 2.4 mm floor

META = PartMeta(
    name="belly_rx_plate",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="none",
    inserts=(Insert("m3_heatset", 3, "mounts under core plate"),),
    clearances={"rx_pocket": "loose", "cable": "loose"},
)


def part() -> Part:
    rx_l, rx_w, rx_h = QI_RX.dims_mm
    clr = S.FIT_LOOSE_MM
    p = Pos(0, 0, PLATE_H / 2) * Cylinder(radius=PLATE_R, height=PLATE_H)

    # RX coil pocket on the BOTTOM face (z=0), coil faces down toward the dock.
    pocket_depth = rx_h + 1.0
    p -= Pos(0, 0, pocket_depth / 2) * Box(rx_l + 2 * clr, rx_w + 2 * clr, pocket_depth)

    # Cable pass-through up into the body.
    p -= Pos(rx_w / 2 - 4, 0, 0) * Cylinder(radius=3.0, height=PLATE_H + 2)

    # 3 M3 mounting holes at 120 deg near the rim (bolt up into the core plate).
    import math
    m3 = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
    for i in range(3):
        a = math.radians(90 + i * 120)
        x, y = (PLATE_R - 6) * math.cos(a), (PLATE_R - 6) * math.sin(a)
        p -= Pos(x, y, PLATE_H / 2) * Cylinder(radius=m3 / 2, height=PLATE_H + 2)
    return p
