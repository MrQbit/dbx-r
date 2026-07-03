"""ROCKY-5 pentagonal core plate — structural PETG (ROBOTS_SPEC.md §4).

The central chassis: a regular pentagon with a Jetson-tray vent aperture and 5
coxa mounting bosses at 72 deg. Radius is parametric from `rocky/design/params.yaml`
(carapace circumscribed diameter). One plate, qty 1.
"""

from __future__ import annotations

import math

from build123d import RegularPolygon, Cylinder, Pos, extrude, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")
RADIUS = float(_P["dimensions"]["carapace_dia_mm"]) / 2.0   # 80 mm
THICK = 4.0
COXA_BOLT_RADIUS = RADIUS - 28.0   # inside the edge apothem (RADIUS*cos36) w/ wall margin
VENT_DIA = 30.0

META = PartMeta(
    name="core_plate",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="none",
    inserts=(Insert("m3_heatset", 5, "coxa mounts"),),
    clearances={"coxa_bolt": "press", "vent": "loose"},
)


def part() -> Part:
    # extrude() builds z=0..THICK (not centered), so cutters are placed at
    # z=THICK/2 to pass fully through — otherwise a THICK/2 cap is left on top.
    zc = THICK / 2
    plate = extrude(RegularPolygon(radius=RADIUS, side_count=5), amount=THICK)
    # Central Jetson-tray vent aperture.
    plate -= Pos(0, 0, zc) * Cylinder(radius=VENT_DIA / 2, height=THICK + 2)
    # 5 coxa mounting holes at 72 deg (limb 0 heading at +X).
    m3 = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
    for i in range(int(_P["limb_count"])):
        a = math.radians(i * _P["limb_angle_deg"])
        x, y = COXA_BOLT_RADIUS * math.cos(a), COXA_BOLT_RADIUS * math.sin(a)
        plate -= Pos(x, y, zc) * Cylinder(radius=m3 / 2, height=THICK + 2)
    return plate
