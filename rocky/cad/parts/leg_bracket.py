"""ROCKY-5 structural limb bracket — printable, one per leg (qty 5, §4).

The load path from the carapace/core to the foot. Each of Rocky's 5 identical
limbs (72 deg apart) is a single rigid printed frame that HOSTS the three
EduLite-05 QDD actuators of that leg — the coxa (yaw), femur (pitch) and tibia
(pitch) servos — plus the pivot interfaces between segments and the M3 heat-set
bosses that bolt the bracket to the core plate and hold each servo down.

Fully parametric off params.yaml segment lengths (`coxa_mm` / `femur_mm` /
`tibia_mm`) and the EduLite servo from components.py (Ø46 x 44 mm QDD, the single
source of truth). Each of the three joint seats is the REAL EduLite mount from
common.cad_lib.edulite: a round Ø46 (+slide) housing pocket, the Ø41.5 PCD bolt
ring (M3+M4), and a Ø24 output-collar bore through the floor so the output turns
freely (D-023) — not the old square drop-in slot. The three seats are laid out
inline along the leg-reach axis (+X); their centres are spaced by the segment
lengths, floored to a non-overlap pitch so a valid >= min-wall land always
separates adjacent pockets. The tibia link then runs the last `tibia_mm` out to
the foot mount.

Envelope: at the tightened params (coxa 41 / femur 72 / tibia 72) the whole leg
frame is ~230 mm along +X — inside the 250 mm P2S envelope, so it prints in ONE
piece (no dovetail split needed). If a future scale pushes it past 250 mm it must
be split at a joint with a dovetail per the carapace split pattern; see
`_needs_split()` which guards that and is asserted in gen_cad's QA.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib.components import SERVO
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

# --- Segment lengths (parametric) ------------------------------------------
COXA = float(_P["dimensions"]["coxa_mm"])
FEMUR = float(_P["dimensions"]["femur_mm"])
TIBIA = float(_P["dimensions"]["tibia_mm"])

# --- EduLite-05 servo seat (single source of truth = components.SERVO) -------
# The servo is a Ø46 round QDD (datasheet, D-022), not a square box: each joint
# seat is now a ROUND Ø46 housing pocket + the real Ø41.5 PCD flange (M3+M4) +
# a Ø24 output-collar bore through the floor so the output can rotate (E.*).
SVX, SVY, SVH = SERVO.dims_mm                       # (46, 46, 44)
POCK_DIA = S.EDULITE_HOUSING_DIA_MM + 2 * S.FIT_SLIDE_MM   # round Ø46 slide-fit seat
POCK_X = POCK_DIA                                   # footprint along X/Y (round)
POCK_Y = POCK_DIA
POCK_D = SVH + 1.0                                  # pocket depth (body H + lead-in)

# --- Beam (the structural spine that carries the three pockets) -------------
WALL = 4.0                                          # side wall each side of a pocket
FLOOR = 5.0                                         # floor beneath pockets (was 9; lightened)
SKIN = 4.0                                          # skin left around lightening windows
BEAM_W = POCK_Y + 2 * WALL                          # cross-section across Y (~60.4)
BEAM_H = POCK_D + FLOOR                             # spine thickness in Z (~44)
END_WALL = 12.0                                     # solid root flange behind the coxa pocket
PITCH_MIN = POCK_X + 2 * S.MIN_WALL_STRUCTURAL_MM   # min centre pitch keeping a valid land

# --- Pivot knuckles (625ZZ press seats = the inter-segment pivot interface) -
EAR_T = 10.0                                        # knuckle thickness in Y
EAR_L = 24.0                                        # knuckle size in X / Z (>= seat + 2*wall)
EAR_OVERLAP = 2.0                                   # fuse depth into the beam side
SEAT_DIA = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
SEAT_DEPTH = S.BEARING_625ZZ_W_MM + 1.0

M3_HOLE = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM   # heat-set boss pilot
FOOT_HOLE = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_SLIDE_MM  # foot bolt slide clearance


def _stations() -> tuple[float, float, float, float]:
    """Servo pocket centres (coxa, femur, tibia) + the foot tip, along +X.

    Spacing follows the segment lengths but is floored to PITCH_MIN so adjacent
    pockets never merge / leave a sub-min-wall sliver. At the tightened params
    the coxa segment (41 mm) is shorter than a servo (52 mm), so the coxa->femur
    pitch is floored (D-020); femur/tibia spacing tracks the real lengths."""
    x_coxa = 0.0
    x_femur = x_coxa + max(COXA, PITCH_MIN)
    x_tibia = x_femur + max(FEMUR, PITCH_MIN)
    x_tip = x_tibia + TIBIA
    return x_coxa, x_femur, x_tibia, x_tip


def _needs_split() -> bool:
    x_coxa, _, _, x_tip = _stations()
    length = (x_tip) - (x_coxa - POCK_X / 2 - END_WALL)
    return length > S.PRINT_ENVELOPE_MM[0]


def _servo_pocket(x: float) -> Part:
    """The real EduLite seat at station x, cut from the top (+Z) face:

      * round Ø46 (+slide) housing pocket, POCK_D deep, for the servo body/rim;
      * Ø41.5 PCD bolt ring (M3+M4) through the pocket floor into the servo's
        threaded flange;
      * Ø24 (+loose) output-collar bore through the floor so the output rotates
        below the beam.

    The Ø46 seat leaves the beam's square corners solid (more material than the
    old square slot), so the envelope is unchanged and the part stays one-piece.
    """
    floor_z = BEAM_H - POCK_D                       # pocket floor height (= FLOOR)
    # Round body pocket: open at the top face (z=BEAM_H), floor at floor_z.
    seat = E.housing_pocket(POCK_D, fit="slide")    # mating face at z=0
    seat = Pos(x, 0, BEAM_H) * seat                 # drop mating face onto the top
    # Flange bolts + output bore punch DOWN through the floor (floor_z -> below).
    thru = floor_z + 2.0
    flange = E.bolt_holes(thru) + E.output_bore(thru, fit="loose")
    flange = Pos(x, 0, floor_z) * flange            # cuts z=floor_z down through
    return seat + flange


def _lightening(x_tibia: float, x_tip: float):
    """Through-Y window in the solid tibia link (turns the heaviest solid run into
    an I-beam), leaving SKIN top/bottom + a solid foot-boss region. Returns the cut
    Part or None if there isn't enough room to keep min-wall."""
    start = x_tibia + POCK_X / 2 + S.MIN_WALL_STRUCTURAL_MM
    end = x_tip - 16.0                              # keep the foot-mount region solid
    wx = end - start
    wz = BEAM_H - 2 * SKIN
    if wx < 18.0 or wz < 10.0:
        return None
    return Pos((start + end) / 2, 0, BEAM_H / 2) * Box(wx, BEAM_W + 4, wz)


def _pivot_knuckles(x: float) -> tuple[Part, Part]:
    """Return (add, cut): two side knuckles at joint x, each with a 625ZZ press
    seat (the inter-segment pitch pivot). The seat is blind from the OUTER face
    so it stays inside the knuckle, clear of the servo pocket."""
    add = None
    cut = None
    zc = BEAM_H / 2
    for s in (+1.0, -1.0):
        yc = s * (BEAM_W / 2 + EAR_T / 2 - EAR_OVERLAP)
        ear = Pos(x, yc, zc) * Box(EAR_L, EAR_T, EAR_L)
        add = ear if add is None else add + ear
        # Blind bearing seat, axis +/-Y, opening on the outer face.
        seat = Rotation(90, 0, 0) * Cylinder(radius=SEAT_DIA / 2, height=SEAT_DEPTH)
        y_outer = s * (BEAM_W / 2 + EAR_T - EAR_OVERLAP)
        seat = Pos(x, y_outer - s * SEAT_DEPTH / 2, zc) * seat
        cut = seat if cut is None else cut + seat
    return add, cut


def leg_bracket() -> Part:
    x_coxa, x_femur, x_tibia, x_tip = _stations()
    x0 = x_coxa - POCK_X / 2 - END_WALL
    x1 = x_tip
    cx = (x0 + x1) / 2.0
    length = x1 - x0

    beam = Pos(cx, 0, BEAM_H / 2) * Box(length, BEAM_W, BEAM_H)

    # Pivot knuckles at the two inter-segment joints (add solid, then seat cuts).
    joints = ((x_coxa + x_femur) / 2.0, (x_femur + x_tibia) / 2.0)
    seat_cuts = []
    for xj in joints:
        add, cut = _pivot_knuckles(xj)
        beam += add
        seat_cuts.append(cut)

    # Three EduLite servo pockets (coxa / femur / tibia).
    for x in (x_coxa, x_femur, x_tibia):
        beam -= _servo_pocket(x)

    # Bearing seats (after pockets so they read on the finished knuckles).
    for cut in seat_cuts:
        beam -= cut

    # M3 heat-set bosses: 2 in the solid coxa-root flange (bolt to core_plate)
    # + 1 servo hold-down tie in the wide femur/tibia solid band. (The coxa/femur
    # band is only ~min-wall wide, so no hole is placed there.)
    for y in (+18.0, -18.0):
        beam -= Pos(x0 + 6.0, y, BEAM_H / 2) * Cylinder(radius=M3_HOLE / 2, height=BEAM_H + 2)
    beam -= Pos(joints[1], 0, BEAM_H / 2) * Cylinder(radius=M3_HOLE / 2, height=BEAM_H + 2)

    # Foot mount at the tibia tip (foot bolts UP into the tip; slide clearance).
    beam -= Pos(x_tip - 8.0, 0, BEAM_H / 2) * Cylinder(radius=FOOT_HOLE / 2, height=BEAM_H + 2)

    # Lightening: I-beam the long solid tibia link (biggest single mass).
    win = _lightening(x_tibia, x_tip)
    if win is not None:
        beam -= win

    return beam


META = PartMeta(
    name="leg_bracket",
    material="PETG",
    qty=int(_P["limb_count"]),                       # one structural frame per leg
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("m3_heatset", 3, "2 coxa-root (core_plate) + 1 servo hold-down tie"),
        Insert("bearing_625zz", 4, "two pitch pivots (femur/tibia), 2 seats each"),
        # 3 servos x 6 flange fasteners on the Ø41.5 PCD; M3+M4 clearance holes,
        # bolts thread into the servo's own flange (no bracket-side inserts).
        Insert("m4_clearance", 9, "servo flange bolts (3/servo, PCD)"),
        Insert("m3_clearance", 9, "servo flange bolts (3/servo, PCD)"),
    ),
    clearances={"servo_pocket": "slide", "pivot_seat": "press", "foot_mount": "slide"},
)


def part() -> Part:
    return leg_bracket()
