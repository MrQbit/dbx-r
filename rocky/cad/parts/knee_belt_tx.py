"""ROCKY-5 KNEE BELT TRANSMISSION prototype (transmission study, NOT committed).

Worked example for the operator's directive: keep the Robstride EduLite-05 QDD's
SPEED (~15 rad/s) and BACKDRIVABILITY at the knee (tibia_pitch), but get the fat
motor OFF the joint so the leg reads SLIM — no more Ø54 side-cup at the knee.

WINNING architecture (see docs/build_plan/pitch_transmission.png + the report):
a LOCAL INLINE TIMING BELT. The QDD lies inline in the FEMUR at the proximal end
(output axis parallel to the knee axis, Y), a HTD-5M timing belt + two 1:1 pulleys
run down the femur inside a closed case, and the driven pulley spins the knee shaft
on two 625ZZ bearings. 1:1 => the QDD's full speed + backdrivability pass straight
through; a toothed belt's backlash is ~0.3-0.5 deg (vs ~2-3 deg for the driveshaft
+ bevel alternative). The knee cross-section drops from Ø54 to ~Ø30.

This module builds the PRINTED PETG belt CASE (`femur_belt_case`, the registered
`part()`), authored in the leg NEUTRAL frame (leg_geom): femur along +X from the
femur_pitch axis P1=(60,0,0) to the knee axis P2=(133,0,0); belt plane = X-Z, both
pulley axes = Y. `dummy_qdd()`, `belt_loop()` and `driven_pulley()` are render/
interference stand-ins (NOT printed). The real print is a Y-split clamshell (two
halves, like grip_palm) so the belt drops in; QA checks the fused solid.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G
from rocky.cad.parts.leg_mounts import edulite_face_cut

_QTY = int(load_params("rocky")["limb_count"])

# --- Belt / pulley selection (HTD-5M, 15 teeth, 1:1) -----------------------
BELT_PITCH_MM = 5.0            # HTD-5M tooth pitch
PULLEY_TEETH = 15
PULLEY_PD_MM = PULLEY_TEETH * BELT_PITCH_MM / math.pi   # 23.87 mm pitch dia
BELT_WIDTH_MM = 9.0           # 9 mm belt (slim knee; ~4x margin at realistic loads,
                              # near the tooth limit only at the rare 6 N·m stall)
BELT_HEIGHT_MM = 3.8          # HTD-5M belt back-to-tooth-tip height
CD_MM = G.FEMUR_MM            # pulley centre distance = femur length 73 mm
RATIO = 1.0                   # NO reduction — keep the QDD's speed

# Toothed-belt pitch length for a 1:1 wrap: 2*CD + pi*PD.
BELT_PITCH_LEN_MM = 2 * CD_MM + math.pi * PULLEY_PD_MM   # ~221 -> stock 225 (45T)
BELT_STOCK_LEN_MM = 225.0

# --- Case geometry ---------------------------------------------------------
WALL = 3.0                                        # closed-case wall (>=2.4 struct)
R_CAV = PULLEY_PD_MM / 2 + BELT_HEIGHT_MM + 1.0   # belt-loop cavity radius (~15.7)
W_CAV = BELT_WIDTH_MM + 3.0                       # cavity width in Y (belt + slop)
R_OUT = R_CAV + WALL                              # outer obround radius (X-Z)
W_CASE = W_CAV + 2 * WALL                         # outer case width in Y

P1X = G.P1[0]                                     # femur_pitch / driver-pulley x = 60
KX = G.P2[0]                                      # knee / driven-pulley x = 133

# Knee bearing bosses (625ZZ carries the driven-pulley shaft, both Y sides).
BOSS_R = S.BEARING_625ZZ_OD_MM / 2 + 3.0          # Ø22 boss
SEAT_D = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
SHAFT_BORE_D = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_SLIDE_MM

# Motor-mount pad: a flat Ø52 face on +Y at the driver station for the real Ø46
# EduLite register + Ø41.5 PCD bolts; the QDD body (Ø46x44) hangs off +Y (a dummy).
PAD_R = S.EDULITE_HOUSING_DIA_MM / 2 + 8.0        # Ø62 pad (room for the Ø41.5 PCD ring)
PAD_FACE_Y = W_CASE / 2 + 6.0                     # flat mount face sits +6 proud of the case


def _obround(radius: float, width_y: float) -> Part:
    """Solid stadium: two Y-axis cylinders at P1/KX + a bridging box, extruded Y."""
    c1 = Pos(P1X, 0, 0) * Rotation(90, 0, 0) * Cylinder(radius=radius, height=width_y)
    c2 = Pos(KX, 0, 0) * Rotation(90, 0, 0) * Cylinder(radius=radius, height=width_y)
    bridge = Pos((P1X + KX) / 2, 0, 0) * Box(KX - P1X, width_y, 2 * radius)
    return c1 + c2 + bridge


def femur_belt_case() -> Part:
    # Closed belt case: outer obround minus the internal belt-loop cavity.
    case = _obround(R_OUT, W_CASE)

    # Motor-mount pad (flat +Y face for the EduLite register + PCD).
    pad = Pos(P1X, PAD_FACE_Y - 8.0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=PAD_R, height=16.0)
    case = case + pad

    # Knee bearing bosses: thicken both Y walls out to KNEE_YFACE so the 625ZZ seat
    # floor keeps a full wall from the belt cavity.
    seat_w = S.BEARING_625ZZ_W_MM + 0.6
    knee_yface = W_CAV / 2 + WALL + seat_w          # seat floor = W_CAV/2 + WALL
    for sy in (-1, 1):
        case = case + Pos(KX, sy * (knee_yface - 3.0), 0) * Rotation(90, 0, 0) * Cylinder(
            radius=BOSS_R, height=6.0)

    # --- internal belt-loop cavity (fully enclosed -> case stays watertight) ---
    case = case - _obround(R_CAV, W_CAV)

    # --- driver side: EduLite QDD mount on the +Y pad, output bores into cavity --
    # Bolt flange + output bore only (no shallow Ø46 register — it feather-edges
    # against the Ø41.5 PCD in a thin pad; the QDD centres on its own pilot).
    case = case - edulite_face_cut((P1X, PAD_FACE_Y, 0), "+Y",
                                   through=PAD_FACE_Y - (W_CAV / 2) + 4.0,
                                   with_register=False)

    # --- knee: 625ZZ seats (both Y faces) + a through shaft clearance bore ------
    for sy in (-1, 1):
        yface = sy * knee_yface
        seat = Pos(KX, yface - sy * seat_w / 2, 0) \
            * Rotation(90, 0, 0) * Cylinder(radius=SEAT_D / 2, height=seat_w)
        case = case - seat
    case = case - Pos(KX, 0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=SHAFT_BORE_D / 2, height=W_CASE + 20)

    # --- belt-access window is a real feature but modelled CLOSED (Y-split clam) ---
    return case


# --------------------------------------------------------------------------- #
# Render / interference stand-ins (NOT printed)
# --------------------------------------------------------------------------- #
def dummy_qdd() -> Part:
    """Solid EduLite-05 (Ø46x44) on the +Y motor pad at the driver station, axis Y."""
    body = Pos(P1X, PAD_FACE_Y + S.EDULITE_HEIGHT_MM / 2, 0) * Rotation(90, 0, 0) \
        * Cylinder(radius=S.EDULITE_HOUSING_DIA_MM / 2, height=S.EDULITE_HEIGHT_MM)
    return body


def _pulley(x: float) -> Part:
    """A flanged HTD-5M pulley (render/interference stand-in) on axis Y at x."""
    hub = Pos(x, 0, 0) * Rotation(90, 0, 0) * Cylinder(
        radius=PULLEY_PD_MM / 2, height=BELT_WIDTH_MM)
    for sy in (-1, 1):
        hub = hub + Pos(x, sy * (BELT_WIDTH_MM / 2 + 1.0), 0) * Rotation(90, 0, 0) \
            * Cylinder(radius=PULLEY_PD_MM / 2 + 2.0, height=2.0)
    return hub


def driver_pulley() -> Part:
    return _pulley(P1X)


def driven_pulley() -> Part:
    return _pulley(KX)


def belt_loop() -> Part:
    """Toothed-belt loop stand-in: the outer obround minus the inner obround (a band
    at the belt pitch radius, BELT_WIDTH wide)."""
    r_out = PULLEY_PD_MM / 2 + BELT_HEIGHT_MM
    r_in = PULLEY_PD_MM / 2
    band = _obround(r_out, BELT_WIDTH_MM) - _obround(r_in, BELT_WIDTH_MM + 2)
    return band


META = PartMeta(
    name="femur_belt_case",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("bearing_625zz", 2, "knee driven-pulley shaft (both Y walls)"),
        Insert("m3_heatset", 6, "EduLite-05 QDD flange on the Ø41.5 PCD motor pad"),
    ),
    clearances={"qdd_register": "slide", "bearing_seat": "press",
                "shaft_bore": "slide", "output_bore": "loose"},
)


def part() -> Part:
    return femur_belt_case()
