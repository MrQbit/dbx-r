"""Assembly interference check (ROBOTS_SPEC.md §4.5) — a G2 test.

Boolean-intersects two positioned part meshes (manifold3d backend) and returns
the overlap volume. Anything above the 0.05 mm^3 tolerance is a real clash that
must be resolved before the parts are declared assemble-able.
"""

from __future__ import annotations

import trimesh

from common.cad_lib.standards import INTERFERENCE_TOL_MM


def pair_interference_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    """Overlap volume (mm^3) between two meshes; 0.0 if disjoint."""
    try:
        inter = trimesh.boolean.intersection([a, b])
    except Exception:  # noqa: BLE001 — degenerate booleans read as "no overlap"
        return 0.0
    if inter is None or inter.is_empty or len(inter.faces) == 0:
        return 0.0
    return abs(float(inter.volume))


def clashes(a: trimesh.Trimesh, b: trimesh.Trimesh) -> bool:
    # tol is a length; cube it for the volume threshold.
    return pair_interference_volume(a, b) > INTERFERENCE_TOL_MM ** 3
