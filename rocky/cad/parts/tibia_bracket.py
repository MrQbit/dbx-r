"""ROCKY-5 TIBIA BRACKET — the knee-BEVEL-driven carrier of the inline ROLL actuator
(D-039 tibia_roll; slim STS3215 per D-041; knee now REMOTE-driven per D-042).

It is the MOVING side of the knee (tibia_pitch) joint and it HOSTS the 4th servo — the
tibia_roll wrist actuator (the ONLY motor that rides the leg):

  * ROOT (x = knee): caps the knee MITER-BEVEL OUTPUT collar (Ø24) on the -Y face (a
    slide cap + centre screw). D-042: the knee is driven REMOTELY — the femur_link's
    miter-bevel box turns the Ø6 driveshaft onto the knee axis (Y) and its Ø24 output
    collar bends the whole tibia here (was the inline knee STS horn in D-041; the coupling
    interface is the same Ø24 collar, so the shank is unchanged).
  * an on-axis SPINE runs out along the leg axis to the roll SERVO HOUSING: the tibia_roll
    STS3215 lies INLINE with its 24.7-slim body proximal (-X) of the roll station PR, its
    output horn on +X driving the shank (tibia_link), which then ROLLS about the leg long
    axis. A 625ZZ IDLER in the housing back wall carries the far end of the roll shaft.
  * two M2.5 heat-set SHELL ANCHOR bosses on the +Z top (the split cosmetic shank shell
    bolts on — threaded, NOT clips).

The tibia wraps only the slim roll body + the Ø12-shaft-fed bevel collar (no QDD on the
leg), so the shank reads slim under the Ø44 shell. PR/TIP are UNCHANGED so leg reach and
the description kinematics are unaffected; the spine routes -Y clear of the femur knee
bevel box so the knee folds freely.

Authored in the leg NEUTRAL frame (leg_geom): knee axis on P2, roll axis on the leg's +X
long axis at PR.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G
from rocky.cad.parts.leg_mounts import sts_face_cut, idler_seat_cut, box_from_aabb, lattice_beam

_QTY = int(load_params("rocky")["limb_count"])

KX = G.P2[0]                       # knee (root) station = 133
PR = G.PR[0]                       # roll output (shank-root) station = 212
W = G.HOUS_WALL
BACK_EXTRA = G.IDLER_W + 2.4

ROOT_HY = 14.0                     # knee coupling reach in -Y
ROOT_BLK_HX = G.COUPLE_D / 2 + 2.0
ROOT_BLK_H = G.HORN_D + 6.0

_RJOINT = (PR, 0.0, 0.0)
_RAABB = G.joint_housing_aabb(_RJOINT, "+X")   # roll housing (body -X + horn envelope)

# Shell anchor bosses (M2.5 heat-set; split cosmetic shell bolts on) — 2 per tibia.
M25_HOLE = 3.5 + 2 * S.FIT_PRESS_MM
ANCHOR_X = (KX + 22.0, PR - 20.0)


def _roll_housing() -> Part:
    x0, x1, y0, y1, z0, z1 = _RAABB    # x1 == PR (the open +X joint face toward the shank)
    return box_from_aabb((x0 - (W + BACK_EXTRA), x1, y0 - W, y1 + W, z0 - W, z1 + W))


def tibia_bracket() -> Part:
    # --- Knee root: SOLID block capping the knee horn on -Y at P2. Kept strictly on
    # -Y (y <= -0.5) so it clears the femur's +Y knee body across the joint plane. --
    root = Pos(KX, -((ROOT_HY + 8.0) / 2 + 0.5), 0) * Box(
        2 * ROOT_BLK_HX, ROOT_HY + 8.0, ROOT_BLK_H)

    # --- Spine: knee -> roll housing (D-040 thin-wall/gyroid strut). Routed on the
    # -Y side (like the knee coupling) so it clears the femur's +Y knee servo body,
    # which extends ~9 mm distal of the knee axis. A lateral (Y) offset does not
    # affect the knee FOLD (pitch is about Y, in the X-Z plane), so the knee still
    # folds far more freely than the old on-axis spine allowed. -------------------
    spine_y = -(G.BEAM_W / 2 + 1.0)
    spine_x0, spine_x1 = KX + ROOT_BLK_HX - 2.0, _RAABB[0] + 6.0
    spine = Pos((spine_x0 + spine_x1) / 2, spine_y, 0) * lattice_beam(
        spine_x1 - spine_x0, G.BEAM_W, G.BEAM_H)

    part = root + spine + _roll_housing()

    # --- shell anchor PADS (+Z top of the spine; pilots stay ABOVE the hollow core) --
    for ax in ANCHOR_X:
        part = part + Pos(ax, spine_y, G.BEAM_H / 2 + 2.0) * Box(12.0, 14.0, 8.0)

    # --- Knee coupling bore over the miter-bevel output collar (slide; -Y face) --
    part -= Pos(KX, -8.0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=G.COUPLE_BORE / 2, height=18.0)

    # --- anchor pilot bores (M2.5 heat-set; shallow, stay in the solid pad) ---
    for ax in ANCHOR_X:
        part -= Pos(ax, spine_y, G.BEAM_H / 2 + 3.5) * Cylinder(radius=M25_HOLE / 2, height=5.0)

    # --- tibia_roll STS3215 pocket (+ horn bore +X) + case screws ------------
    part -= sts_face_cut(_RJOINT, "+X", through=G.HORN_PROTRUDE + 4.0)

    # --- 625ZZ idler on the -X back wall (far end of the roll shaft) ----------
    part -= idler_seat_cut(_RJOINT, "+X", back=-G.SV_H, depth=G.IDLER_W + 0.6)
    return part


META = PartMeta(
    name="tibia_bracket",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 1, "tibia_roll output-shaft idler (-X back wall)"),
        Insert("m2_selftap", 4, "tibia_roll STS3215 case screws"),
        Insert("m25_heatset", 2, "removable cosmetic-shell anchors, M2.5 bolts (tibia +Z)"),
    ),
    clearances={"knee_bevel_collar": "slide", "servo_pocket": "slide",
                "horn_bore": "loose", "idler_seat": "press", "anchor": "press"},
)


def part() -> Part:
    return tibia_bracket()
