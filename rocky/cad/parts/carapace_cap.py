"""ROCKY-5 carapace — upper cap piece (2-piece carapace, section 4).

The top of the rock dome (z=seam..H). Lifts off the skirt to assemble over the
internal structure. Watertight via the half-space intersection.
"""
from __future__ import annotations

from build123d import Box, Pos, Part

from common.cad_lib.part_meta import PartMeta
from rocky.cad.parts.carapace import shell, Z_SPLIT, displace_outer

META = PartMeta(name="carapace_cap", material="PLA", qty=1, cosmetic=True,
                plate_group="rocky_shells", supports="tree")


def part() -> Part:
    upper = Pos(0, 0, Z_SPLIT + 100) * Box(400, 400, 200)   # keep z >= seam
    return shell() & upper


def displace(mesh):
    return displace_outer(mesh)
