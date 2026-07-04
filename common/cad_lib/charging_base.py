"""Wireless charging base / dock (operator requirement) — printable.

A pad the robot parks on. The Qi 15 W transmitter (QI_TX) drops into a top-opening
pocket housed in a raised central boss; a lead-in ring self-centres the robot's
underside receiver (QI_RX) over the transmitter. A side cable channel routes the
barrel-jack input to the coil. The matching receiver pocket lives on each robot's
belly (see the robot belly parts) so RX and TX align when docked.

Pocket sizes come straight from components.py, so if you source a different Qi
module you change ONE dataclass and both the dock and the belly pocket update.
"""

from __future__ import annotations

from build123d import Cylinder, Box, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.components import QI_TX
from common.cad_lib.part_meta import Insert, PartMeta

PAD_R = 65.0
PAD_H = 6.0
BOSS = 16.0          # raised housing height for the TX pocket

META = PartMeta(
    name="charging_base",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="charging_base",
    supports="none",
    inserts=(Insert("m3_heatset", 4, "TX retention + rubber feet"),),
    clearances={"tx_pocket": "loose", "cable_channel": "loose"},
)


def part() -> Part:
    tx_l, tx_w, tx_h = QI_TX.dims_mm
    clr = S.FIT_LOOSE_MM
    # Base pad (z 0..PAD_H).
    p = extrude_pad()
    # Central raised housing (z PAD_H .. PAD_H+BOSS).
    house = tx_l + 2 * clr + 8, tx_w + 2 * clr + 8, BOSS
    p += Pos(0, 0, PAD_H + BOSS / 2) * Box(*house)
    # TX coil pocket, opening upward (robot parks its RX over this).
    pocket_depth = tx_h + 1.0
    top_z = PAD_H + BOSS
    p -= Pos(0, 0, top_z - pocket_depth / 2) * Box(tx_l + 2 * clr, tx_w + 2 * clr, pocket_depth)
    # Side cable channel from the pocket out to the pad edge (barrel-jack input).
    p -= Pos(0, (tx_w / 2 + 6), PAD_H + 4) * Box(6.0, PAD_R, 6.0)
    return p


def extrude_pad() -> Part:
    # Cylinder is centered on the origin; shift so the pad sits on z 0..PAD_H.
    return Pos(0, 0, PAD_H / 2) * Cylinder(radius=PAD_R, height=PAD_H)
