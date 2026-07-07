"""ROCKY-5 leg HIP YOKE — the body-side mount for the coxa_yaw QDD (D-042 LOCK).

FIRST link in the leg's load path and the ONLY leg part fixed to the body: it bolts
up into the carapace/core and HOSTS the coxa_yaw actuator with a VERTICAL (Z) axis.

D-042 (supersedes the slim-STS D-041): the coxa_yaw actuator is back to a Robstride
EduLite-05 QDD (backdrivable, ~15 rad/s) — one of the THREE QDD that make up the
per-limb HIP CLUSTER inside the body. The QDD body sits UP (+Z) in a round Ø46
register cup; its Ø24 output collar drives DOWN through the floor into the
`coxa_bracket` below, so turning this motor yaws the whole leg. Three M3 heat-set
bores in the flange bolt the yoke up into the body.

Authored in the leg NEUTRAL frame (leg_geom): yaw axis = the vertical line x=y=0,
mount/output face at z = YAW_FLOOR_Z, QDD body up, leg hangs below.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G
from rocky.cad.parts.leg_mounts import edulite_face_cut

_QTY = int(load_params("rocky")["limb_count"])   # one chassis per leg (qty 5)

FLOOR_T = 9.0                              # flange plate (carries the Ø24 output bore + PCD bolts)
FLOOR_TOP = G.YAW_FLOOR_Z                  # output / mount face (QDD flange bolts here, body up)
FLOOR_BOT = FLOOR_TOP - FLOOR_T
_JOINT = (0.0, 0.0, FLOOR_TOP)

# Round flange plate: the Ø46 QDD body sits ON TOP (+Z), located by its Ø41.5 PCD bolt
# ring + Ø24 output collar (NO shallow Ø46 register — the M4 clearance holes at Ø47 would
# feather-edge against a Ø46 register wall; the belt-case dropped it for the same reason).
DISC_R = S.EDULITE_HOUSING_DIA_MM / 2 + 11.0     # ~Ø68 plate (room for PCD ring + 3 lugs)
M3_HOLE = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
LUG_R = DISC_R - 7.0                              # carapace-lug bolt ring (>=2.4 mm to the rim)


def leg_hip_yoke() -> Part:
    yoke = Pos(0, 0, (FLOOR_BOT + FLOOR_TOP) / 2) * Cylinder(radius=DISC_R, height=FLOOR_T)

    # EduLite coxa_yaw QDD flange: Ø41.5 PCD bolts + Ø24 output collar bore, punched
    # DOWN through the plate (body on +Z, output drives the coxa_bracket below).
    yoke -= edulite_face_cut(_JOINT, "+Z", through=FLOOR_T + 2.0,
                             with_register=False, with_output=True)

    # Three M3 heat-set bores in the flange rim (60deg off the PCD bolts) — bolt the yoke
    # up into the body carapace/core.
    for k in range(3):
        a = math.radians(60 + k * 120)
        yoke -= Pos(LUG_R * math.cos(a), LUG_R * math.sin(a), (FLOOR_TOP + FLOOR_BOT) / 2) \
            * Cylinder(radius=M3_HOLE / 2, height=FLOOR_T + 2)
    return yoke


META = PartMeta(
    name="leg_hip_yoke",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="none",
    inserts=(
        Insert("m3_heatset", 3, "carapace mount bores (bolt hip yoke to the body)"),
        Insert("m4_clearance", 3, "coxa_yaw EduLite flange bolts, Ø41.5 PCD (M4)"),
        Insert("m3_clearance", 3, "coxa_yaw EduLite flange bolts, Ø41.5 PCD (M3)"),
    ),
    clearances={"pcd_bolts": "loose", "output_bore": "loose", "carapace_lug": "press"},
)


def part() -> Part:
    return leg_hip_yoke()
