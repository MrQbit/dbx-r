"""ROCKY-5 KNEE DRIVESHAFT TRANSMISSION prototype (transmission study, NOT committed).

CHOSEN architecture (operator directive): keep the Robstride EduLite-05 QDD's SPEED
(~15 rad/s) and BACKDRIVABILITY at the knee, but move the fat motor OFF the leg
ENTIRELY — into the hip cluster / body — and drive the knee REMOTELY through the
bending femur_pitch joint with an RC-style DRIVESHAFT. The leg segments then carry
only a thin shaft, so the slender cosmetic stone SHELL can slide over them.

Drive train (one articulating CV joint + one right-angle bevel):
  QDD in the hip cluster, output along +X (radial, down the leg)
    -> DOUBLE-CARDAN CVD centred ON the femur_pitch axis (P1) — a single RC CVD tops
       out ~50 deg but femur_pitch travels -80..+57 deg, so two cardans in series (a
       dogbone/CVD at each end of a short bisecting yoke) give constant velocity over
       the full range; the CV centre on the pitch axis means the shaft just bends,
       no epicyclic cross-coupling
    -> thin Ø6 driveshaft down the femur (along X) in a Ø12 tube
    -> M1 16T:16T MITER BEVEL at the knee (P2): turns the femur-X shaft to the knee
       axis (Y); the output bevel is coaxial with the knee axis and fixed to the tibia
    -> knee (tibia_pitch) rotates about Y, 1:1, full QDD speed.

HONEST costs (report): backlash stacks — double-cardan (2 joints) + 1 bevel mesh ~=
2-3 deg at the knee (vs ~0.5 deg for the belt fallback); the double-cardan eats femur
length; and the hip cluster now holds 3 QDDs. PAYOFF: the femur/tibia shells are truly
slim (they wrap a Ø12 shaft, not a Ø46 motor), and ~242 g/leg of motor mass moves to
the body.

This module builds the PRINTED PETG femur DRIVE CASE (`femur_shaft_case`, the
registered `part()`): the slim femur strut with the axial shaft tube, the knee bevel
housing, and the removable-SHELL ANCHOR bosses. `dummy_*` builders are render/
interference stand-ins (NOT printed). Authored in the leg NEUTRAL frame (leg_geom):
femur along +X from femur_pitch P1=(60,0,0) to knee P2=(133,0,0); shaft along X, knee
bevel output about Y. The real print is a Y-split clamshell so the shaft + bevels drop
in; QA checks the fused solid.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G

_QTY = int(load_params("rocky")["limb_count"])

# --- Driveshaft + bevel selection (RC-sourced) -----------------------------
SHAFT_D_MM = 6.0                 # 1/8-scale RC CVD / dogbone centre bar
SHAFT_TUBE_D_MM = 12.0           # femur bore around the shaft (shaft + MR bearings)
CVD_CUP_D_MM = 18.0              # RC CVD coupler / cup OD at the femur_pitch joint
BEVEL_MODULE = 1.0               # M1 miter bevel
BEVEL_TEETH = 16
BEVEL_PD_MM = BEVEL_MODULE * BEVEL_TEETH        # 16 mm pitch dia
BEVEL_OD_MM = BEVEL_PD_MM + 2 * BEVEL_MODULE    # ~18 mm outer
RATIO = 1.0                      # NO reduction — keep the QDD's speed

# Backlash budget (report): 2 cardans + 1 bevel mesh.
BACKLASH_DEG = 2.5

P1X = G.P1[0]                    # femur_pitch axis x = 60 (CV joint centre)
KX = G.P2[0]                     # knee axis x = 133 (bevel box)

# --- Femur strut cross-section (SLIM — wraps the shaft, not a motor) --------
STRUT_W = 20.0                   # Y width (slim; fits the ~Ø33 under-shell envelope)
STRUT_H = 24.0                   # Z height
WALL = 3.0

# --- Knee bevel box --------------------------------------------------------
BOX_HALF = BEVEL_OD_MM / 2 + WALL + 1.5         # ~13.5 -> box ~Ø27 at the knee
SEAT_D = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
SHAFT_BORE_D = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_SLIDE_MM
KNEE_OUT_D = S.EDULITE_OUTPUT_COLLAR_DIA_MM     # Ø24 output collar to the tibia

# --- Shell anchor bosses (removable split cosmetic shell) ------------------
# SMALL M2.5 heat-set BOSSES on the femur TOP (+Z) at the proximal + distal ends
# (operator: threaded bolts, NOT clips/snaps — clips break + can't hide under stone).
# A 2-part stone shell clamshell BOLTS onto these two bosses with M2.5 machine screws
# (heads countersunk + hidden under a crag), so it unbolts for servicing the shaft/
# bevels (report: bolt size + count per segment).
M25_INSERT_HOLE_DIA_MM = 3.5                         # M2.5 brass heat-set pilot
ANCHOR_BOSS_D = M25_INSERT_HOLE_DIA_MM + 2 * 2.6     # ~Ø8.7 boss (hides under the crag)
ANCHOR_BOSS_H = 6.0
ANCHOR_X = (P1X + 14.0, KX - 16.0)


def _stadium_x(length: float, w: float, h: float, at_x: float) -> Part:
    """A rounded (top/bottom filleted) beam along X: a box with two Z-capping
    cylinders, centred at at_x. Cross-section w(Y) x h(Z)."""
    beam = Pos(at_x, 0, 0) * Box(length, w, h - w) if h > w else Pos(at_x, 0, 0) * Box(length, w, h)
    if h > w:
        for sz in (-1, 1):
            beam = beam + Pos(at_x, 0, sz * (h - w) / 2) * Rotation(0, 90, 0) * Cylinder(
                radius=w / 2, height=length)
    return beam


def femur_shaft_case() -> Part:
    # --- slim femur strut carrying the axial shaft tube ----------------------
    x0, x1 = P1X - 6.0, KX - BOX_HALF + 2.0
    strut = _stadium_x(x1 - x0, STRUT_W, STRUT_H, (x0 + x1) / 2)

    # --- knee bevel box (closed block at P2) ---------------------------------
    box = Pos(KX, 0, 0) * Box(2 * BOX_HALF, 2 * BOX_HALF, 2 * BOX_HALF)

    # --- proximal CV-joint support ring (seats the femur_pitch pivot + shaft) --
    # A short collar on the pitch axis at P1 that carries the femur_pitch 625ZZ on
    # +Y (the actuator drives -Y) and passes the driveshaft along X on the axis.
    cv = Pos(P1X, 0, 0) * Box(16.0, STRUT_W, STRUT_H)

    part = strut + box + cv

    # --- shell anchor PADS (+Z top): box pedestals that merge into the strut cap
    # (a box base avoids the thin tangent lens a cylinder-on-round-cap leaves). -----
    for ax in ANCHOR_X:
        part = part + Pos(ax, 0, STRUT_H / 2) * Box(12.0, 14.0, 8.0)

    # --- axial driveshaft tube (Ø12 bore along X, P1 -> bevel box) -----------
    part = part - Pos((x0 + KX) / 2, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=SHAFT_TUBE_D_MM / 2, height=(KX - x0) + 4.0)

    # --- bevel-box internal cavity (closed -> watertight; real print is a clam) --
    part = part - Pos(KX, 0, 0) * Box(2 * (BOX_HALF - WALL), 2 * (BOX_HALF - WALL),
                                      2 * (BOX_HALF - WALL))

    # --- knee OUTPUT shaft on the knee axis (Y): 625ZZ seats both faces + a Ø5
    # through bore. The output bevel is keyed to this shaft; a small coupling disc
    # OUTSIDE the box (+Y) drives the tibia (no fat Ø24 collar cutting the box). ---
    for sy in (-1, 1):
        yface = sy * BOX_HALF
        part = part - Pos(KX, yface - sy * (S.BEARING_625ZZ_W_MM + 0.6) / 2, 0) \
            * Rotation(90, 0, 0) * Cylinder(radius=SEAT_D / 2, height=S.BEARING_625ZZ_W_MM + 0.6)
    part = part - Pos(KX, 0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=SHAFT_BORE_D / 2, height=2 * BOX_HALF + 20)

    # NOTE: the femur_pitch pivot 625ZZ + the CVD centre are COAXIAL on the Y axis
    # at P1 (the shaft passes through the pivot centre, differential-style); that
    # bearing seats in the mating coxa_bracket/hip yoke, not this femur case (keeping
    # a Ø16 seat and the Ø12 shaft bore out of the same P1 point here). The femur root
    # couples to the femur_pitch output on the body side of the CVD.

    # --- anchor pilot bores (M2.5 heat-set) ----------------------------------
    for ax in ANCHOR_X:
        part = part - Pos(ax, 0, STRUT_H / 2 + 4.0 - 3.0) * Cylinder(
            radius=(M25_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM) / 2, height=8.0)
    return part


# --------------------------------------------------------------------------- #
# Render / interference stand-ins (NOT printed)
# --------------------------------------------------------------------------- #
def dummy_qdd_hip() -> Part:
    """EduLite-05 (Ø46x44) in the hip cluster, axis +X, feeding the CVD at P1."""
    cx = P1X - S.EDULITE_HEIGHT_MM / 2 - 8.0
    return Pos(cx, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=S.EDULITE_HOUSING_DIA_MM / 2, height=S.EDULITE_HEIGHT_MM)


def dummy_cvd() -> Part:
    """Double-cardan CVD across the femur_pitch joint: two cups + a bisecting bar,
    centred on P1 (render/interference stand-in)."""
    bar = Pos(P1X, 0, 0) * Rotation(0, 90, 0) * Cylinder(radius=SHAFT_D_MM / 2, height=34.0)
    for sx in (-1, 1):
        bar = bar + Pos(P1X + sx * 15.0, 0, 0) * Rotation(0, 90, 0) * Cylinder(
            radius=CVD_CUP_D_MM / 2, height=10.0)
    return bar


def dummy_shaft() -> Part:
    return Pos((P1X + KX) / 2, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=SHAFT_D_MM / 2, height=(KX - P1X))


def dummy_bevels() -> Part:
    """Input pinion (on X) + output bevel (on Y) meshing at the knee."""
    pin = Pos(KX - BEVEL_PD_MM / 2, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=BEVEL_OD_MM / 2, height=6.0)
    out = Pos(KX, BEVEL_PD_MM / 2, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=BEVEL_OD_MM / 2, height=6.0)
    return pin + out


META = PartMeta(
    name="femur_shaft_case",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 3, "knee bevel output (2, both Y walls) + femur_pitch pivot (1)"),
        Insert("m25_heatset", 2, "removable cosmetic-shell anchors, M2.5 bolts (femur +Z)"),
    ),
    clearances={"shaft_tube": "slide", "bearing_seat": "press",
                "knee_output": "loose", "anchor": "press"},
)


def part() -> Part:
    return femur_shaft_case()
