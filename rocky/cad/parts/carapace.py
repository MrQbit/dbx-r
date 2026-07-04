"""ROCKY-5 rock carapace — the movie-accurate stony dome (§4).

A low pentagonal dome shell (squat river-stone silhouette per D-006), hollow so
it caps the body over the electronics, with procedural rock displacement applied
to the exported mesh (see `displace`). PLA, matte blackish-brown when printed.

part() returns the smooth base shell (build123d); gen_cad.py then calls
`displace(mesh)` on the exported mesh to add the rock texture and re-checks QA.
"""

from __future__ import annotations

import numpy as np
from build123d import BuildPart, BuildSketch, RegularPolygon, Plane, loft, Part

from common.cad_lib.part_meta import PartMeta
from common.cad_lib.rock import _value_noise
from common.params import load_params

_P = load_params("rocky")
R = _P["dimensions"]["carapace_dia_mm"] / 2.0      # 80 mm base half-width
H = _P["dimensions"]["dome_height_mm"]             # 85 mm (D-006, ~0.5 ratio)
# Sloped dome walls: the perpendicular thickness is less than the offset, so use
# a generous offset to keep the cosmetic min wall (1.6 mm) with margin.
WALL = 2.8
NOISE = _P["carapace"]["noise"]                     # amp 1.2, freq 0.08

META = PartMeta(
    name="carapace",
    material="PLA",
    qty=1,
    cosmetic=True,                                  # 1.6 mm min wall class
    plate_group="rocky_shells",
    supports="tree",
    clearances={},
)


def _dome(r_base: float, r_top: float, z0: float, z1: float) -> Part:
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z0)):
            RegularPolygon(r_base, 5)
        with BuildSketch(Plane.XY.offset(z1)):
            RegularPolygon(r_top, 5)
        loft()
    return bp.part


def part() -> Part:
    # Hollow shell = outer dome minus a slightly smaller inner dome that pokes
    # below z=0, leaving the bottom open to sit over the body.
    # inner top stops WALL_CAP below the outer top so the cap isn't paper-thin.
    outer = _dome(R, R * 0.5, 0.0, H)
    inner = _dome(R - WALL, R * 0.5 - WALL, -2.0, H - 3.5)
    return outer - inner


def displace(mesh):
    """Subdivide to a fine mesh, then apply rock texture to the OUTER faces ONLY
    (§4) so the shell wall never thins. Midpoint subdivide preserves manifoldness;
    'outer' = vertices whose normal points away from the centroid."""
    mesh.merge_vertices()
    for _ in range(5):                # 52 -> ~53k tris, ~2.5 mm edges (fine craggy)
        mesh = mesh.subdivide()
    c = mesh.centroid
    outer = np.einsum("ij,ij->i", mesh.vertices - c, mesh.vertex_normals) > 0
    raw = _value_noise(mesh.vertices, NOISE["freq_per_mm"], 4, 1.0)
    d = ((raw + 1.0) * 0.5) * NOISE["amp_mm"]     # outward-only [0, amp]
    d[~outer] = 0.0                                # inner surface stays put
    mesh.vertices = mesh.vertices + mesh.vertex_normals * d[:, None]
    return mesh
