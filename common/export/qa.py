"""Mesh QA — the G2 print-readiness gate (ROBOTS_SPEC.md §8, §4.5).

Operates on trimesh meshes (works in the host venv; no build123d needed). QA
failure fails G2 so problems are caught here, never discovered at the slicer:

  * watertight (manifold, no holes)
  * positive volume
  * fits the Bambu P2S 250x250x250 mm envelope
  * minimum wall thickness (2.4 mm structural / 1.6 mm cosmetic)

Oversize shells are meant to be auto-split with dovetails BEFORE QA (that lives
in the export step); QA here reports the envelope violation so a part that was
never split fails loudly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh

from common.cad_lib.standards import PRINT_ENVELOPE_MM


@dataclass
class QAReport:
    name: str
    watertight: bool
    volume_mm3: float
    bbox_mm: tuple[float, float, float]
    fits_envelope: bool
    min_wall_mm: float | None          # None if not evaluated
    min_wall_required_mm: float
    min_wall_ok: bool
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def _min_wall_thickness(mesh: trimesh.Trimesh, samples: int = 400) -> float | None:
    """Estimate the thinnest wall by casting a ray inward from sampled face
    centres and measuring the distance to the opposite surface.

    Approximate (edges/thin fins can read low), so callers treat it as a
    screening check. Returns None if the ray engine yields nothing usable.
    """
    if len(mesh.faces) == 0:
        return None
    idx = np.linspace(0, len(mesh.faces) - 1, min(samples, len(mesh.faces))).astype(int)
    origins = mesh.triangles_center[idx]
    normals = mesh.face_normals[idx]
    # Step just inside the surface, cast along -normal (into the solid).
    eps = 1e-3
    ray_o = origins - normals * eps
    ray_d = -normals
    tri, ray_idx, locs = mesh.ray.intersects_id(
        ray_o, ray_d, return_locations=True, multiple_hits=False
    )
    if len(locs) == 0:
        return None
    dists = np.linalg.norm(locs - ray_o[ray_idx], axis=1)
    # Keep only hits on a wall roughly FACING the ray (a genuine opposite wall).
    # Rays that graze out through an adjacent face at a convex edge/corner strike
    # a near-perpendicular surface — reject them so corners don't read as thin.
    hit_normals = mesh.face_normals[tri]
    # The far wall's OUTWARD normal points the same way the ray travels (both away
    # from the entry face) -> dot ~ +1. A grazing convex-edge exit is ~perpendicular
    # -> dot ~ 0. Keep only genuine opposite walls.
    facing = np.einsum("ij,ij->i", hit_normals, ray_d[ray_idx]) > 0.5
    dists = dists[facing & (dists > eps * 2)]
    if dists.size == 0:
        return None
    return float(dists.min())


def check_mesh(
    mesh: trimesh.Trimesh,
    name: str,
    min_wall_required_mm: float,
    check_min_wall: bool = True,
) -> QAReport:
    failures: list[str] = []

    watertight = bool(mesh.is_watertight)
    if not watertight:
        failures.append("not watertight (open edges / non-manifold)")

    volume = float(mesh.volume) if watertight else float(mesh.convex_hull.volume)
    if volume <= 0:
        failures.append(f"non-positive volume ({volume:.3f} mm^3)")

    ext = mesh.extents if mesh.extents is not None else (0, 0, 0)
    bbox = (float(ext[0]), float(ext[1]), float(ext[2]))
    fits = all(b <= e + 1e-6 for b, e in zip(bbox, PRINT_ENVELOPE_MM))
    if not fits:
        failures.append(
            f"exceeds {PRINT_ENVELOPE_MM[0]:.0f} mm envelope "
            f"(bbox {bbox[0]:.1f}x{bbox[1]:.1f}x{bbox[2]:.1f}) — must be split with dovetails"
        )

    min_wall = None
    min_wall_ok = True
    if check_min_wall and watertight:
        min_wall = _min_wall_thickness(mesh)
        if min_wall is not None and min_wall < min_wall_required_mm:
            min_wall_ok = False
            failures.append(
                f"min wall {min_wall:.2f} mm < required {min_wall_required_mm:.2f} mm"
            )

    return QAReport(
        name=name,
        watertight=watertight,
        volume_mm3=volume,
        bbox_mm=bbox,
        fits_envelope=fits,
        min_wall_mm=min_wall,
        min_wall_required_mm=min_wall_required_mm,
        min_wall_ok=min_wall_ok,
        failures=failures,
    )
