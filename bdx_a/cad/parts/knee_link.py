"""BDX-A thigh/shin link — structural PETG (ROBOTS_SPEC.md §3, §4.5).

A flat link connecting two joints: a 625ZZ bearing bore at the knee end and the
STS3215 output-spline clearance at the drive end. Length is parametric from
`bdx_a/design/params.yaml` (thigh == shin == 96 mm), so a params edit reshapes it.
"""

from __future__ import annotations

from build123d import Box, Cylinder, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("bdx_a")
LENGTH = float(_P["dimensions"]["thigh_mm"])   # 96 mm
WIDTH = 22.0
THICK = 8.0

META = PartMeta(
    name="knee_link",
    material="PETG",
    qty=4,                       # 2 per leg (thigh + shin) x 2 legs
    cosmetic=False,
    plate_group="bdx_a_structure",
    supports="none",
    inserts=(Insert("bearing_625zz", 1, "knee pivot"),),
    clearances={"bearing_bore": "press", "spline_clear": "loose"},
)


def part() -> Part:
    p = Box(LENGTH, WIDTH, THICK)
    x_end = LENGTH / 2 - 13.0
    # 625ZZ bearing bore (through) at the knee end.
    bore = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
    p -= Pos(x_end, 0, 0) * Cylinder(radius=bore / 2, height=THICK + 2)
    # Servo spline clearance hole at the drive end.
    spline = 7.0 + 2 * S.FIT_LOOSE_MM
    p -= Pos(-x_end, 0, 0) * Cylinder(radius=spline / 2, height=THICK + 2)
    return p
