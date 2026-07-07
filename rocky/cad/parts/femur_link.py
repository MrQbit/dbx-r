"""ROCKY-5 FEMUR LINK — the SLIM driveshaft thigh (D-042 LOCK).

SUPERSEDES the D-041 inline-STS femur. Under the locked architecture the femur carries
NO motor — the femur_pitch AND knee QDD both live in the hip cluster. The femur is a
slim strut that wraps the Ø12 knee DRIVESHAFT and turns it at the knee:

  * ROOT (femur_pitch axis, P1): a +Y coupling collar caps the femur_pitch QDD's Ø24
    output collar (the QDD lives in the coxa_bracket/hip cluster), so that motor swings
    the whole femur about the pitch axis (Y) DIRECTLY. A short CV-support ring on the
    pitch axis carries the DOUBLE-CARDAN CVD that passes the knee driveshaft through the
    bending pitch joint (CVD centred on P1 -> the shaft just bends, no cross-coupling).
  * BEAM: a slim stadium strut (20x24, fits the Ø44 under-shell envelope) bored with the
    axial Ø12 shaft tube — the Ø6 knee shaft runs down it on MR bearings.
  * KNEE (P2): a closed M1 16T:16T MITER BEVEL box turns the femur-axis (X) shaft onto
    the knee axis (Y); the output bevel is coaxial with the knee and its Ø24 collar (on
    +Y) drives the tibia_bracket. 625ZZ on both Y faces carry the output shaft.
  * Two M2.5 heat-set SHELL ANCHOR bosses on the +Z top (the split cosmetic stone shell
    bolts on — threaded, NOT clips).

The real print is a Y-split clamshell so the shaft + bevels drop in; QA checks the fused
solid. Authored in the leg NEUTRAL frame (leg_geom): P1=(60,0,0), knee P2=(133,0,0),
femur along +X, pitch/knee axes = Y, shaft along X.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G

_QTY = int(load_params("rocky")["limb_count"])

# --- Driveshaft + bevel (RC-sourced; params knee.transmission) --------------
SHAFT_TUBE_D_MM = 12.0           # femur bore around the Ø6 shaft (shaft + MR bearings)
BEVEL_MODULE = 1.0
BEVEL_TEETH = 16
BEVEL_OD_MM = BEVEL_MODULE * (BEVEL_TEETH + 2)  # ~18 mm outer

P1X = G.P1[0]                    # femur_pitch axis x = 60 (CVD centre + root coupling)
KX = G.P2[0]                     # knee axis x = 133 (miter bevel box)

# --- Slim femur strut (wraps the shaft, NOT a motor) ------------------------
STRUT_W = 20.0                   # Y width (slim; fits the Ø44 under-shell envelope)
STRUT_H = 24.0                   # Z height
WALL = 3.0

# --- Knee miter-bevel box ---------------------------------------------------
BOX_HALF = BEVEL_OD_MM / 2 + WALL + 1.5         # ~13.5 -> box ~27 at the knee
SEAT_D = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
SHAFT_BORE_D = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_SLIDE_MM

# --- femur_pitch QDD root coupling (+Y at P1) -------------------------------
COUPLE_BORE = S.EDULITE_OUTPUT_COLLAR_DIA_MM + 2 * S.FIT_SLIDE_MM  # Ø24 collar cap (slide)
ROOT_HUB_R = COUPLE_BORE / 2 + 3.0   # Ø30 round hub (>=3 mm wall around the Ø24 collar)
ROOT_HUB_LY = 15.0                    # hub reach in +Y (socket depth over the collar)
ROOT_BORE_DEPTH = 12.0                # blind Ø24 socket (stops short of the y=0 shaft)

# --- Shell anchor bosses (M2.5 heat-set; split cosmetic shell bolts on) -----
M25_INSERT_HOLE_DIA_MM = 3.5
ANCHOR_BOSS_H = 8.0
ANCHOR_X = (P1X + 16.0, KX - 18.0)


def _stadium_x(length: float, w: float, h: float, at_x: float) -> Part:
    """Rounded (top/bottom filleted) beam along X: a box + two Z-capping cylinders."""
    beam = Pos(at_x, 0, 0) * Box(length, w, h - w) if h > w else Pos(at_x, 0, 0) * Box(length, w, h)
    if h > w:
        for sz in (-1, 1):
            beam = beam + Pos(at_x, 0, sz * (h - w) / 2) * Rotation(0, 90, 0) * Cylinder(
                radius=w / 2, height=length)
    return beam


def femur_link() -> Part:
    # --- slim femur strut carrying the axial shaft tube ----------------------
    x0, x1 = P1X - 6.0, KX - BOX_HALF + 2.0
    strut = _stadium_x(x1 - x0, STRUT_W, STRUT_H, (x0 + x1) / 2)

    # --- knee miter-bevel box (closed block at P2) ---------------------------
    box = Pos(KX, 0, 0) * Box(2 * BOX_HALF, 2 * BOX_HALF, 2 * BOX_HALF)

    # --- proximal CV-support ring at P1 (carries the femur_pitch pivot + the CVD
    # centre so the driveshaft bends over the full pitch range) ---------------
    cv = Pos(P1X, 0, 0) * Box(16.0, STRUT_W, STRUT_H)

    # --- femur_pitch QDD root coupling: a +Y round HUB whose Ø24 socket caps the QDD's
    # output collar (the QDD lives in the coxa_bracket) so it swings the femur ---
    root = Pos(P1X, STRUT_W / 2 + ROOT_HUB_LY / 2, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=ROOT_HUB_R, height=ROOT_HUB_LY)

    part = strut + box + cv + root

    # --- shell anchor PADS (+Z top): box pedestals merged into the strut cap ---
    for ax in ANCHOR_X:
        part = part + Pos(ax, 0, STRUT_H / 2) * Box(12.0, 14.0, ANCHOR_BOSS_H)

    # --- axial driveshaft tube (Ø12 bore along X, P1 -> bevel box) -----------
    part = part - Pos((x0 + KX) / 2, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=SHAFT_TUBE_D_MM / 2, height=(KX - x0) + 4.0)

    # --- femur_pitch coupling socket (Ø24 blind bore, along +Y into the hub; stops
    # short of the y=0 shaft axis so it never breaks into the shaft tube) ------
    bore_outer_y = STRUT_W / 2 + ROOT_HUB_LY
    part = part - Pos(P1X, bore_outer_y - ROOT_BORE_DEPTH / 2, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=COUPLE_BORE / 2, height=ROOT_BORE_DEPTH)

    # --- bevel-box internal cavity (closed -> watertight; real print is a clam) --
    part = part - Pos(KX, 0, 0) * Box(2 * (BOX_HALF - WALL), 2 * (BOX_HALF - WALL),
                                      2 * (BOX_HALF - WALL))

    # --- knee OUTPUT shaft on the knee axis (Y): 625ZZ seats both faces + a Ø5
    # through bore. The output bevel is keyed to this shaft; its Ø24 collar OUTSIDE
    # the box (+Y) drives the tibia_bracket. --------------------------------------
    for sy in (-1, 1):
        yface = sy * BOX_HALF
        part = part - Pos(KX, yface - sy * (S.BEARING_625ZZ_W_MM + 0.6) / 2, 0) \
            * Rotation(90, 0, 0) * Cylinder(radius=SEAT_D / 2, height=S.BEARING_625ZZ_W_MM + 0.6)
    part = part - Pos(KX, 0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=SHAFT_BORE_D / 2, height=2 * BOX_HALF + 20)

    # --- anchor pilot bores (M2.5 heat-set) ----------------------------------
    for ax in ANCHOR_X:
        part = part - Pos(ax, 0, STRUT_H / 2 + ANCHOR_BOSS_H - 3.0) * Cylinder(
            radius=(M25_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM) / 2, height=8.0)
    return part


META = PartMeta(
    name="femur_link",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 2, "knee miter-bevel output shaft (both Y walls)"),
        Insert("m25_heatset", 2, "removable cosmetic-shell anchors, M2.5 bolts (femur +Z)"),
    ),
    clearances={"shaft_tube": "slide", "bearing_seat": "press",
                "femur_pitch_collar": "slide", "knee_output": "loose", "anchor": "press"},
)


def part() -> Part:
    return femur_link()
