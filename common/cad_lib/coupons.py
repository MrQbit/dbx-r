"""Coupons plate — print plate #1 (ROBOTS_SPEC.md §8, WEEKEND_RUNBOOK.md).

Three fit-test features, all driven by common/cad_lib/standards.py so a single
clearance edit + `make regen-cad` re-cuts them (the one sanctioned human edit):
  * servo slide-fit pocket (STS3215 body drops in)
  * M3 heat-set insert boss hole
  * 625ZZ bearing press-fit seat

Prints in <60 min; the human verifies fits before committing to full plates.
"""

from __future__ import annotations

from build123d import Box, Cylinder, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta

PLATE_L = 90.0
PLATE_W = 50.0
PLATE_T = 9.0   # >=2.4 mm floor under the deepest (5.5 mm) pocket

META = PartMeta(
    name="coupons",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="coupons",
    supports="none",
    inserts=(Insert("m3_heatset", 1, "boss fit test"),
             Insert("bearing_625zz", 1, "seat press fit test")),
    clearances={"servo_pocket": "slide", "bearing_seat": "press", "m3_boss": "press"},
)


def part() -> Part:
    z_top = PLATE_T / 2
    p = Box(PLATE_L, PLATE_W, PLATE_T)

    # Servo slide-fit pocket (partial depth, opens on +Z).
    sw = S.SERVO_BOX_L_MM + 2 * S.FIT_SLIDE_MM
    sd = S.SERVO_BOX_W_MM + 2 * S.FIT_SLIDE_MM
    pocket_depth = 5.0
    p -= Pos(-18, 0, z_top - pocket_depth / 2) * Box(sw, sd, pocket_depth)

    # M3 heat-set boss hole (through), press class for the brass insert.
    m3_dia = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
    p -= Pos(30, 12, 0) * Cylinder(radius=m3_dia / 2, height=PLATE_T + 2)

    # 625ZZ bearing press-fit seat (partial depth).
    seat_dia = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
    seat_depth = S.BEARING_625ZZ_W_MM + 0.5
    p -= Pos(30, -12, z_top - seat_depth / 2) * Cylinder(radius=seat_dia / 2, height=seat_depth)

    return p
