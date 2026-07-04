"""Procedural rock-surface displacement for ROCKY-5's carapace (§4).

Rocky (Project Hail Mary) is described as "a tarantula made of rocks" — a
blackish-brown stony carapace. This displaces a mesh's vertices along their
normals by smooth multi-octave value noise (spec: amp 1.2 mm, freq 0.08 /mm) to
give the granite/river-stone texture. Deterministic (seeded by coordinates) and
small/smooth, so a watertight input stays watertight.
"""

from __future__ import annotations

import numpy as np


def _value_noise(pts: np.ndarray, freq: float, octaves: int, seed: float) -> np.ndarray:
    """Smooth deterministic pseudo-noise in [-1, 1], summed over octaves."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    out = np.zeros(len(pts))
    amp = 1.0
    total = 0.0
    for o in range(octaves):
        f = freq * (2 ** o)
        s = seed + o * 7.13
        # three phase-shifted sinusoid products -> isotropic, seamless, smooth
        n = (np.sin(f * (1.3 * x + 0.7 * y) + s)
             * np.cos(f * (0.9 * y - 1.1 * z) + 1.7 * s)
             + np.sin(f * (1.1 * z + 0.6 * x) + 2.3 * s))
        out += amp * 0.5 * n
        total += amp
        amp *= 0.5
    return out / total


def rock_displace(mesh, amp_mm: float = 1.2, freq_per_mm: float = 0.08,
                  octaves: int = 3, seed: float = 1.0, outward_only: bool = False):
    """Displace vertices along normals by rock noise. Mutates + returns.

    outward_only maps the noise to [0, amp] so bumps only push OUT — a shell's
    wall then only ever thickens, never thinning below the min-wall minimum.
    """
    v = mesh.vertices.copy()
    n = mesh.vertex_normals
    raw = _value_noise(v, freq_per_mm, octaves, seed)
    d = ((raw + 1.0) * 0.5 if outward_only else raw) * amp_mm
    mesh.vertices = v + n * d[:, None]
    return mesh
