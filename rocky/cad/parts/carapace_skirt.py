"""ROCKY-5 carapace — lower skirt piece (2-piece carapace, section 4).

The lower band of the rock dome (z=0..seam). Intersecting the shell with a solid
half-space caps the cut so the piece stays watertight. Mates with carapace_cap.
"""
from __future__ import annotations

from build123d import Box, Pos, Part

from common.cad_lib.part_meta import PartMeta
from rocky.cad.parts.carapace import shell, Z_SPLIT, displace_outer

META = PartMeta(name="carapace_skirt", material="PLA", qty=1, cosmetic=True,
                plate_group="rocky_shells", supports="none")


def part() -> Part:
    lower = Pos(0, 0, Z_SPLIT - 100) * Box(400, 400, 200)   # keep z <= seam
    return shell() & lower


def displace(mesh):
    return displace_outer(mesh)
