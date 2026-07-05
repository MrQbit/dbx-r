"""ROCKY-5 culturally-marked primary limb segment — printable, qty 1 (§4, movie).

Rocky (Project Hail Mary) is an Eridian artefact; the Eridians count in BASE 3
and their limbs/carapace carry engraved cultural markings. This is the tibia
(shank) of the ONE primary limb (heading limb 0), engraved with:

  * a base-3 (ternary) numeric RULER running along the segment — short ticks are
    units, every 3rd tick is a 3^1 mark, every 9th a 3^2 mark, so ternary
    place-value is visible on the ruler, and
  * the Eridian 'MARRIAGE' symbol: two interlocking rings.

The engraving is a shallow relief CUT (ENGRAVE_DEPTH_MM, in the 0.6-1.0 mm band)
into one face, so the structural wall beneath it stays far above the 2.4 mm
minimum. It is a pure, TOGGLEABLE feature: `engrave_cultural_markings(solid)`
takes any limb solid and returns it with the markings added, so a plain limb and
the marked one share the same base geometry and both clear mesh QA.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

# --- Shank (tibia) blank -----------------------------------------------------
SHANK_LEN = float(_P["dimensions"]["tibia_mm"])   # 96 mm along +Z
SHANK_W = 22.0                                     # cross-section along X (engraved face at +X)
SHANK_T = 16.0                                     # cross-section along Y
MOUNT_BOLT_R = (S.M2_INSERT_HOLE_DIA_MM) / 2.0     # foot-bolt pilot at the tip

# --- Engraving ---------------------------------------------------------------
ENGRAVE_DEPTH_MM = 0.8                             # shallow relief (0.6-1.0 mm band)
_CUT_OVERSHOOT = 0.3                               # poke the cutter just past the face
LINE_W = 0.8                                       # engraved line width
RULER_Z0, RULER_Z1 = 10.0, 60.0                    # ruler span along the shank
RULER_DZ = 5.0                                     # tick pitch
RULER_Y = -5.0                                     # ruler spine offset on the face (Y)
TICK_LEN = {0: 3.0, 1: 6.0, 2: 9.0}                # unit / 3^1 / 3^2 tick lengths
RING_RO, RING_RI = 5.0, 3.9                        # marriage-ring outer/inner radius
RING_Z = 74.0                                      # marriage symbol centre (Z)
RING_DZ = 4.0                                      # half-separation of the two rings (interlock)
# Engraved features must keep >= min-wall (2.4 mm) of land to the +/-SHANK_T/2
# face edge, or the thin sliver reads as an under-thickness wall. The face is
# only SHANK_T = 16 mm wide (Y), so: tall ticks grow from the spine to Y=+4
# (4 mm margin); the two rings stack along the long Z axis at Y=0 (+/-5 mm span,
# 3 mm margin) instead of side-by-side (which would breach the edge).


def tibia_shank() -> Part:
    """Plain tibia shank blank (no markings). z = 0..SHANK_LEN, engraved face +X."""
    shank = Pos(0, 0, SHANK_LEN / 2) * Box(SHANK_W, SHANK_T, SHANK_LEN)
    # Foot-bolt pilot up from the bottom tip (mates the 3-pronged foot, foot.py).
    shank -= Pos(0, 0, 6.0) * Cylinder(radius=MOUNT_BOLT_R, height=12.0 + 2.0)
    return shank


def _ternary_level(k: int) -> int:
    """Ruler tick 'weight': 3^2 every 9th tick, 3^1 every 3rd, else a unit."""
    if k % 9 == 0:
        return 2
    if k % 3 == 0:
        return 1
    return 0


def _face_cut_box(face_x: float, cy: float, cz: float, ly: float, lz: float) -> Part:
    """A shallow rectangular relief cutter on the +X face (depth ENGRAVE_DEPTH_MM)."""
    dx = ENGRAVE_DEPTH_MM + _CUT_OVERSHOOT
    x = face_x - ENGRAVE_DEPTH_MM / 2.0 + _CUT_OVERSHOOT / 2.0
    return Pos(x, cy, cz) * Box(dx, ly, lz)


def _ring_cutter(face_x: float, cy: float, cz: float) -> Part:
    """A shallow annular groove (ring) engraved into the +X face."""
    dx = ENGRAVE_DEPTH_MM + _CUT_OVERSHOOT
    ring = Cylinder(radius=RING_RO, height=dx) - Cylinder(radius=RING_RI, height=dx + 0.4)
    ring = Rotation(0, 90, 0) * ring                       # ring axis: +Z -> +X (lies on the face)
    x = face_x - ENGRAVE_DEPTH_MM / 2.0 + _CUT_OVERSHOOT / 2.0
    return Pos(x, cy, cz) * ring


def engrave_cultural_markings(solid: Part, face_x: float | None = None) -> Part:
    """Return `solid` with the ternary ruler + marriage symbol engraved into its
    +X face. Pure and toggleable: callers choose whether to apply it, so plain and
    marked limbs share geometry and both stay watertight / min-wall valid."""
    if face_x is None:
        face_x = SHANK_W / 2.0
    out = solid
    # --- Base-3 ruler: a spine groove + weighted ternary ticks along Z. ---
    n_ticks = int((RULER_Z1 - RULER_Z0) / RULER_DZ) + 1
    out -= _face_cut_box(face_x, RULER_Y, (RULER_Z0 + RULER_Z1) / 2.0,
                         LINE_W, (RULER_Z1 - RULER_Z0) + LINE_W)      # spine
    for k in range(n_ticks):
        z = RULER_Z0 + k * RULER_DZ
        tlen = TICK_LEN[_ternary_level(k)]
        out -= _face_cut_box(face_x, RULER_Y + tlen / 2.0, z, tlen, LINE_W)
    # --- Marriage symbol: two interlocking rings, stacked along Z at Y=0. ---
    out -= _ring_cutter(face_x, 0.0, RING_Z - RING_DZ)
    out -= _ring_cutter(face_x, 0.0, RING_Z + RING_DZ)
    return out


META = PartMeta(
    name="limb_marked",
    material="PETG",
    qty=1,                                          # the one primary (heading) limb
    cosmetic=False,
    plate_group="rocky_limbs",
    supports="none",
    inserts=(Insert("m2_selftap", 1, "foot-bolt boss at the tibia tip"),),
    clearances={"foot_mount": "slide"},
)


def part() -> Part:
    return engrave_cultural_markings(tibia_shank())
