"""ROCKY-5 TIBIA LINK — the roll-driven SHANK that carries the hand (Phase 1, D-039;
slim STS3215 roll servo per D-041).

After the D-039 wrist-roll split, the tibia is two links: `tibia_bracket` (knee-driven,
hosts the roll actuator) and THIS shank. The shank is the MOVING side of the roll
joint: its root caps the tibia_roll STS3215's output HORN (axis = X, the leg long
axis), so the roll servo TWISTS the whole shank + hand about the leg axis. The shank
runs to a tip PAD that presents the Ø41.5 PCD hand-mount flange, so the existing 2+1
grip hand (`grip_palm` …) bolts straight on — the hand mount is a plain bolt flange
(not a servo) and is UNCHANGED.

The shank is now a short ~26 mm wrist (the roll actuator took the proximal length of
the old 105 mm tibia); it is near-axisymmetric, so rolling ±1.5 rad is self-collision
free. Too short to be worth hollowing — the D-040 gyroid strut work moved to the long
`tibia_bracket` keel. The hand mount TIP is UNCHANGED (238), so leg reach is unchanged.

Authored in the leg NEUTRAL frame (leg_geom): roll axis on PR (on the leg +X axis),
hand mount on TIP, shank along +X.
"""
from __future__ import annotations

from build123d import Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params
from rocky.cad.parts import leg_geom as G
from rocky.cad.parts.leg_mounts import edulite_face_cut

_QTY = int(load_params("rocky")["limb_count"])

RX = G.PR[0]                     # roll output (shank root) station = 212
TX = G.TIP[0]                    # hand-mount station              = 238
HUB_R = 16.0                     # shank body radius (>=2.7 mm wall around the Ø24 collar bore)
PAD_T = 8.0                      # tip flange pad thickness
PAD_R = G.FLANGE_DISC / 2        # Ø52 pad (covers the PCD + rim)
BODY_X1 = TX - PAD_T             # shank body -> pad transition = 230

COUPLE_BORE = G.COUPLE_BORE      # slide cap over the Ø24 roll horn


def tibia_link() -> Part:
    # --- Shank body: a stubby cylinder on the roll axis (rolls about X) -------
    body = Pos((RX + BODY_X1) / 2, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=HUB_R, height=BODY_X1 - RX)

    # --- Tip pad: presents the hand-mount flange ------------------------------
    pad = Pos(TX - PAD_T / 2, 0, 0) * Rotation(0, 90, 0) * Cylinder(radius=PAD_R, height=PAD_T)

    part = body + pad

    # --- Root coupling: slide cap over the roll output HORN (+X) --------------
    part -= Pos(RX + 7.0, 0, 0) * Rotation(0, 90, 0) * Cylinder(
        radius=COUPLE_BORE / 2, height=14.0)

    # --- Hand mount: EduLite Ø41.5 PCD flange on the +X tip face (grip_palm bolts
    # on; no servo body here, so no housing register). Ø24 relief is a BLIND recess
    # in the pad only (a through bore would be wider than the shank body behind it).
    part -= edulite_face_cut((TX, 0, 0), "+X", through=PAD_T + 3.0,
                             with_register=False, with_output=False)
    part -= Pos(TX, 0, 0) * Rotation(0, 90, 0) * E.output_bore(PAD_T - 2.0, fit="loose", extend_up=1.0)
    return part


META = PartMeta(
    name="tibia_link",
    material="PETG",
    qty=_QTY,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(
        Insert("m3_heatset", 6, "hand-mount flange (grip_palm bolts on, Ø41.5 PCD)"),
    ),
    clearances={"roll_collar": "press", "hand_flange": "slide"},
)


def part() -> Part:
    return tibia_link()
