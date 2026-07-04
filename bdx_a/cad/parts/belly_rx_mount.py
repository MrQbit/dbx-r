"""BDX-A (BDX-R) Qi 15 W receiver mount — wireless charging improvement.

A compact printed plate that bolts to the BDX-R bottom cover and holds the Qi RX
coil in a downward-facing pocket. When BDX-A parks on the charging_base dock, the
coil aligns over the transmitter. This is an ADD-ON to the unchanged BDX-R
chassis (D-007: build BDX-R exactly, improve via charging) — no BDX-R part is
modified. Pocket size from components.QI_RX.
"""

from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.components import QI_RX
from common.cad_lib.part_meta import Insert, PartMeta

PLATE_L = 66.0
PLATE_W = 50.0
PLATE_H = 9.0   # >= RX pocket depth + 2.4 mm floor

META = PartMeta(
    name="belly_rx_mount",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="bdx_a_addons",
    supports="none",
    inserts=(Insert("m3_heatset", 4, "bolts to BDX-R bottom cover"),),
    clearances={"rx_pocket": "loose", "cable": "loose"},
)


def part() -> Part:
    rx_l, rx_w, rx_h = QI_RX.dims_mm
    clr = S.FIT_LOOSE_MM
    p = Pos(0, 0, PLATE_H / 2) * Box(PLATE_L, PLATE_W, PLATE_H)

    # RX coil pocket on the BOTTOM face (coil faces down to the dock).
    pocket_depth = rx_h + 1.0
    p -= Pos(0, 0, pocket_depth / 2) * Box(rx_l + 2 * clr, rx_w + 2 * clr, pocket_depth)

    # Cable pass-through up into the chassis.
    p -= Pos(rx_l / 2 - 5, 0, 0) * Cylinder(radius=3.0, height=PLATE_H + 2)

    # 4 M3 mounting holes near the corners (bolt up into the bottom cover).
    m3 = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
    dx, dy = PLATE_L / 2 - 6, PLATE_W / 2 - 6
    for sx in (-1, 1):
        for sy in (-1, 1):
            p -= Pos(sx * dx, sy * dy, PLATE_H / 2) * Cylinder(radius=m3 / 2, height=PLATE_H + 2)
    return p
