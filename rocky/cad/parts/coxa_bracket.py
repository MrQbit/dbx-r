"""ROCKY-5 COXA BRACKET — the HIP CLUSTER frame (D-042 LOCK).

Rides the coxa_yaw QDD output and carries the other TWO hip-cluster QDD, so all the
leg's heavy motors sit at the body (mass off the moving leg). It:

  * COUPLES to the coxa_yaw QDD output through a top hub (slide cap over the Ø24
    collar + centre screw), so yawing the hip motor turns this whole bracket about the
    vertical (Z) axis;
  * reaches out COXA_MM to the femur_pitch station P1 and there presents the femur_pitch
    EduLite QDD flange (Ø46 body toward -Y, Ø24 output +Y) that DIRECTLY swings the slim
    femur about the pitch axis (Y);
  * carries the KNEE QDD on a matching flange low in the cluster (output +X): the knee
    motor drives the knee REMOTELY, its output coupling to the double-cardan CVD centred
    on the femur_pitch axis at P1 and then the Ø6 shaft down the femur (see femur_link);
  * carries two M2.5 heat-set SHELL ANCHOR bosses (the split cosmetic shell bolts on).

This is the perpendicular hip cluster the spec calls for (yaw Z ⟂ pitch Y). Authored in
the leg NEUTRAL frame (leg_geom): hub on the yaw axis (x=y=0), femur_pitch flange on
P1 = (COXA_MM, 0, 0). The QDD bodies are dummies (in the body); this part is the printed
frame that seats + bolts them. Each QDD flange is cut into a chunky BOX knuckle (the
flanges locate on their own pilot + Ø41.5 PCD ring — NO Ø46 register, whose M4 clearance
at Ø47 would feather-edge it, as on the belt case).
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G
from rocky.cad.parts.leg_mounts import edulite_face_cut

_QTY = int(load_params("rocky")["limb_count"])

JX = G.P1[0]                                   # femur_pitch station x (= 60)

HUB_D = 34.0
HUB_TOP = G.YAW_FLOOR_Z - 2.0                  # just under the yaw floor (caps the coxa_yaw horn)
HUB_BOT = 8.0

BODY_HH = 15.0                                 # hip-body half-height (Z)
BODY_HY = 11.0                                 # hip-body half-width (Y)
KNK = 56.0                                     # flange-knuckle face size (>= Ø54 for the PCD ring)

KNEE_Z = -38.0                                 # knee-QDD sits LOW in the cluster, below the yaw
KNEE_X = -8.0                                  # hub + femur_pitch bolt rings — no collisions

M25_HOLE = (3.5 + 2 * S.FIT_PRESS_MM)
ANCHOR = [(JX - 12.0, BODY_HH + 3.0), (24.0, BODY_HH + 3.0)]  # 2 shell anchors (+Z top), clear
#                                                               of the coxa_yaw horn bore


def coxa_bracket() -> Part:
    # --- yaw hub (couples the coxa_yaw QDD output from above) -----------------
    hub = Pos(0, 0, (HUB_BOT + HUB_TOP) / 2) * Cylinder(radius=HUB_D / 2, height=HUB_TOP - HUB_BOT)
    riser = Pos(0, 0, (6 + HUB_TOP) / 2) * Box(HUB_D, 2 * BODY_HY, HUB_TOP - 6)

    # --- hip body: a spar from the hub out to P1 -----------------------------
    body = Pos((-8 + JX) / 2, 0, 0) * Box(JX + 16.0, 2 * BODY_HY, 2 * BODY_HH)

    # --- femur_pitch knuckle at P1 (chunky box; +Y face carries the Ø41.5 PCD flange —
    # the box face is >= Ø56 in X and Z to hold the whole bolt ring, and its front stands
    # 2 mm PROUD of the hip body's +Y face so no thin body ledge protrudes past it) -----
    fem_front = BODY_HY + 2.0                       # y=13, proud of the body (+Y at 11)
    fem_depth = KNK / 2 + fem_front
    fem_knk = Pos(JX, fem_front - fem_depth / 2, 0) * Box(KNK, fem_depth, KNK)

    # --- knee-QDD knuckle (low; +X face carries the flange, output toward the CVD) --
    knee_knk = Pos(KNEE_X - 10, 0, KNEE_Z) * Box(KNK / 2 + 10, KNK, KNK)
    knee_tie = Pos(KNEE_X, 0, (KNEE_Z + KNK / 2 + BODY_HH) / 2) * Box(
        22.0, 26.0, BODY_HH - (KNEE_Z + KNK / 2))   # ties the knuckle up into the hip body

    part = hub + riser + body + fem_knk + knee_knk + knee_tie

    # --- hollow the two chunky QDD knuckles (closed inner cavities -> the QDD bodies
    # nest inside; keeps min wall >= 5 mm and stays watertight, ~halves the mass) -----
    part -= Pos(JX, fem_front - fem_depth / 2, 0) * Box(KNK - 12, fem_depth - 12, KNK - 12)
    part -= Pos(KNEE_X - 10, 0, KNEE_Z) * Box(KNK / 2 + 10 - 12, KNK - 12, KNK - 12)

    # --- shell anchor PADS (+Z top) ------------------------------------------
    for ax, az in ANCHOR:
        part = part + Pos(ax, 0, az - 4.0) * Box(12.0, 14.0, 8.0)

    # --- Couple to the coxa_yaw output horn (slide cap bore, top-down) --------
    part -= Pos(0, 0, HUB_TOP - 6.0) * Cylinder(radius=G.COUPLE_BORE / 2, height=18.0)

    # --- femur_pitch EduLite flange: PCD bolts + Ø24 output +Y (into the +Y knuckle face) --
    part -= edulite_face_cut((JX, fem_front, 0), "-Y", through=20.0,
                             with_register=False, with_output=True)
    # --- knee-QDD EduLite flange: PCD bolts + Ø24 output +X (into the +X knuckle face) --
    part -= edulite_face_cut((KNEE_X, 0, KNEE_Z), "-X", through=18.0,
                             with_register=False, with_output=True)

    # --- anchor pilot bores (M2.5 heat-set) ----------------------------------
    for ax, az in ANCHOR:
        part -= Pos(ax, 0, az) * Cylinder(radius=M25_HOLE / 2, height=8.0)
    return part


META = PartMeta(
    name="coxa_bracket",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("m4_clearance", 6, "femur_pitch + knee QDD flange bolts, Ø41.5 PCD (M4/M3)"),
        Insert("m25_heatset", 2, "removable cosmetic-shell anchors, M2.5 bolts (coxa/hip +Z)"),
    ),
    clearances={"yaw_horn": "slide", "femur_pitch_flange": "loose",
                "knee_flange": "loose", "output_bore": "loose", "anchor": "press"},
)


def part() -> Part:
    return coxa_bracket()
