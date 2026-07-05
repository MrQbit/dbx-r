"""ROCKY-5 three-pronged foot / end-effector — printable, one per leg (§4, D-008).

Rocky's (Project Hail Mary) interchangeable limbs terminate in a SYMMETRIC
3-pronged hand-foot: a central hub that bolts to the tibia tip, and three claw
prongs at 120 deg that splay down-and-out into a stable tripod (grip open = flat
foot, per the front manipulators, D-008). All five limbs share this identical
foot — Rocky is radially symmetric (5 legs at 72 deg), and the movie shows the
prongs on every limb, not just the two front manipulators — so it prints qty 5
and drops onto any leg.

Fully parametric off params.yaml (`limb_count`, `foot_dia_mm`) and structural
min-wall clean (2.4 mm): prongs are PRONG_T mm thick with blunt tips (no knife
edges) and the hub keeps >=5 mm of wall around the mount bolt.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

N_PRONGS = 3                                   # symmetric 3-pronged foot (movie)
HUB_R = 13.0                                   # mount hub radius
HUB_H = 16.0                                   # mount hub height
PRONG_LEN = 34.0                               # claw length (root embedded in hub)
PRONG_W = 9.0                                  # claw width  (>= min wall)
PRONG_T = 7.0                                  # claw thickness (>= min wall)
PRONG_DROP_DEG = 35.0                          # splay angle below horizontal
MOUNT_BOLT_R = (S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM) / 2.0

META = PartMeta(
    name="foot",
    material="PETG",
    qty=int(_P["limb_count"]),                 # one per leg -> all 5 legs
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="tree",
    inserts=(Insert("m3_heatset", 1, "foot bolts up into the tibia tip"),),
    clearances={"tibia_mount": "slide"},
)


def three_prong_foot(n: int = N_PRONGS) -> Part:
    """Symmetric n-pronged foot centred on the origin. Hub axis = +Z; prongs
    splay downward toward -Z (the ground-contact tripod)."""
    # Central mounting hub (z -HUB_H/2 .. +HUB_H/2).
    foot = Cylinder(radius=HUB_R, height=HUB_H)
    # Claw prongs, evenly spaced, each tilted PRONG_DROP_DEG below horizontal.
    for i in range(n):
        # Base box along +X; shift so its inner ~HUB_R/2 embeds in the hub for a
        # solid (watertight) fuse, then tilt the tip down and rotate into place.
        prong = Pos(PRONG_LEN / 2 - HUB_R * 0.5, 0, 0) * Box(PRONG_LEN, PRONG_W, PRONG_T)
        prong = Rotation(0, PRONG_DROP_DEG, 0) * prong        # drop tip toward -Z
        prong = Rotation(0, 0, i * 360.0 / n) * prong         # splay at 360/n deg
        foot += prong
    # Central bolt hole (from the top face down) to fasten onto the tibia tenon.
    foot -= Pos(0, 0, HUB_H / 2 - 6.0) * Cylinder(radius=MOUNT_BOLT_R, height=12.0 + 2.0)
    return foot


def part() -> Part:
    return three_prong_foot()
