"""ROCKY-5 rock carapace — shared shell + rock texture (section 4).

Low pentagonal dome shell (squat river-stone, D-006), hollow to cap the body.
This module is the reusable library; the printable pieces are carapace_cap.py
and carapace_skirt.py (section 4: 2-piece carapace — smaller prints, assembles
over the internal structure). Rock displacement is applied to the OUTER faces
only so the cosmetic wall never thins.
"""

from __future__ import annotations

import numpy as np
from build123d import BuildPart, BuildSketch, RegularPolygon, Plane, loft, Part

from common.cad_lib.rock import _value_noise
from common.params import load_params

_P = load_params("rocky")
R = _P["dimensions"]["carapace_dia_mm"] / 2.0      # 80 mm base half-width
H = _P["dimensions"]["dome_height_mm"]             # 85 mm (D-006, ~0.5 ratio)
WALL = 2.8                                          # sloped-wall offset (perp >= 1.6)
Z_SPLIT = H * 0.55                                  # cap/skirt horizontal seam
NOISE = _P["carapace"]["noise"]


def _dome(r_base: float, r_top: float, z0: float, z1: float) -> Part:
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z0)):
            RegularPolygon(r_base, 5)
        with BuildSketch(Plane.XY.offset(z1)):
            RegularPolygon(r_top, 5)
        loft()
    return bp.part


def shell() -> Part:
    """Full hollow dome shell. Inner top stops below the outer top so the cap
    isn't paper-thin."""
    outer = _dome(R, R * 0.5, 0.0, H)
    inner = _dome(R - WALL, R * 0.5 - WALL, -2.0, H - 3.5)
    return outer - inner


# --- 2-piece seam: dovetail / registration flange --------------------------
# The seam runs through the ~3 mm sloped cosmetic wall, so a joint cut INTO the
# wall would leave a sub-min-wall sliver. Instead the skirt carries an internal
# registration lip (a pentagonal spigot) that rises past the seam into the cap's
# open cavity with a loose slide fit; the pentagon keys rotation, the fit centres
# it. It adds material INWARD (never thins the wall) and is protected from rock
# displacement (see displace_outer's protect_r_below) so its fit surface stays
# clean. The two pieces butt flush at the seam plane and the lip locates them.
LIP_H = 10.0            # how far the lip rises above the seam into the cap
LIP_T = 3.5            # lip wall thickness (>= cosmetic min wall)
_LIP_R_INNER = -2.0    # inner-dome loft z-start
_LIP_R_ZTOP = H - 3.5  # inner-dome loft z-end


def _inner_r(z: float) -> float:
    """Inner-wall pentagon circumradius at height z (matches shell()'s inner loft)."""
    r0, r1 = R - WALL, R * 0.5 - WALL
    return r0 + (r1 - r0) * (z - _LIP_R_INNER) / (_LIP_R_ZTOP - _LIP_R_INNER)


def lip_protect_radius() -> float:
    """XY radius below which displacement is suppressed to keep the lip fit clean
    (midway between the inner wall and outer wall at the seam)."""
    r_out_seam = R * (1.0 - 0.5 * Z_SPLIT / H)
    return 0.5 * (_inner_r(Z_SPLIT) + r_out_seam)


def seam_lip() -> Part:
    """Skirt's internal registration lip: a collar fused into the inner wall just
    below the seam + a spigot ring rising LIP_H above it into the cap cavity."""
    from common.cad_lib.standards import FIT_LOOSE_MM as CLR
    # Collar (below seam): bites +2 mm into the inner wall so it fuses to the skirt.
    collar_out = _dome(_inner_r(Z_SPLIT - 8) + 2.0, _inner_r(Z_SPLIT) + 2.0, Z_SPLIT - 8, Z_SPLIT)
    collar_hole = _dome(_inner_r(Z_SPLIT - 8) + 2.0 - 6.0, _inner_r(Z_SPLIT) + 2.0 - 6.0,
                        Z_SPLIT - 10, Z_SPLIT + 2)
    collar = collar_out - collar_hole
    # Spigot ring (crosses the seam up into the cap): outer follows inner wall - CLR
    # for a slide fit; starts below the seam so it fuses to the collar volume.
    reg_out = _dome(_inner_r(Z_SPLIT - 3) - CLR, _inner_r(Z_SPLIT + LIP_H) - CLR,
                    Z_SPLIT - 3, Z_SPLIT + LIP_H)
    reg_hole = _dome(_inner_r(Z_SPLIT - 3) - CLR - LIP_T, _inner_r(Z_SPLIT + LIP_H) - CLR - LIP_T,
                     Z_SPLIT - 5, Z_SPLIT + LIP_H + 2)
    reg = reg_out - reg_hole
    return collar + reg


def displace_outer(mesh, z_seam: float | None = None,
                   seam_band: float = 6.0, seam_nz: float = 0.5,
                   seam_smooth: float = 2.5, protect_r_below: float | None = None):
    """Subdivide, then rock-texture the OUTER surface only. 'Outer' = the vertex
    normal points away from the shell's centroid ((v-c)·n > 0): the whole outer
    dome INCLUDING the apex gets craggy, the inner wall never moves (so it can't
    thin below min-wall).

    z_seam: for a CUT piece (carapace_cap / carapace_skirt), hold the flat mating
    face at this Z flush — vertices within seam_band of the seam plane whose normal
    is near-vertical (|n_z| > seam_nz) are NOT displaced, so the two pieces still
    mate flush while their surrounding outer wall stays craggy/full-thickness.
    Single-piece carapace passes z_seam=None -> the whole dome is textured."""
    mesh.merge_vertices()
    for _ in range(5):                 # ~53k tris, ~2.5 mm edges (fine craggy)
        mesh = mesh.subdivide()
    c = mesh.centroid
    n = mesh.vertex_normals
    v = mesh.vertices
    mask = np.einsum("ij,ij->i", v - c, n) > 0        # outer faces (craggy apex)
    if z_seam is not None:
        dz = np.abs(v[:, 2] - z_seam)
        # Flat mating face flush, PLUS a thin flush band across the seam so the two
        # pieces' craggy outer walls meet cleanly (no cross-seam texture overlap).
        seam = ((dz < seam_band) & (np.abs(n[:, 2]) > seam_nz)) | (dz < seam_smooth)
        mask &= ~seam                                 # keep the seam flush
    if protect_r_below is not None:                   # keep the registration lip clean
        mask &= (v[:, 0] ** 2 + v[:, 1] ** 2) > protect_r_below ** 2
    raw = _value_noise(v, NOISE["freq_per_mm"], 4, 1.0)
    d = ((raw + 1.0) * 0.5) * NOISE["amp_mm"]      # outward-only [0, amp]
    d[~mask] = 0.0
    mesh.vertices = v + n * d[:, None]
    return mesh


# --- Single-piece registration (the working carapace: it FITS the 250 mm P2S
# envelope at ~211 mm, so it stays the default one-print part). The 2-piece split
# (carapace_cap.py / carapace_skirt.py) is now VALIDATED, not WIP: seam-aware
# displacement (z_seam) keeps the mating face flush + the outer walls meeting
# cleanly, and the skirt carries a dovetail registration lip (seam_lip) so the
# pieces key together — both clear mesh QA and assemble with zero interference.
# Kept unregistered (redundant while the single piece fits); swap the two in if a
# future scale pushes the carapace past the envelope. ---
from common.cad_lib.part_meta import PartMeta  # noqa: E402

META = PartMeta(name="carapace", material="PLA", qty=1, cosmetic=True,
                plate_group="rocky_shells", supports="tree")


def part() -> Part:
    return shell()


def displace(mesh):
    return displace_outer(mesh)
