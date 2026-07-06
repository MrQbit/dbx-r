#!/usr/bin/env python3
"""Preview the ROCKY-5 breathing carapace mechanism (D-024) — matplotlib Agg.

Loads the generated STLs (run `make _cad ROBOT=rocky` first) and draws the five
crown petals + the scroll cam + the hub in two states: EXHALE (petals retracted)
and INHALE (all five slid out by A_BREATH via the one central scroll cam). No
pyglet / no GL — pure matplotlib Agg so it runs headless in the host venv.

Usage: .venv/bin/python scripts/render_carapace_mech.py [out.png]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")                       # headless, no pyglet/GL
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "rocky" / "cad" / "parts"
sys.path.insert(0, str(ROOT))
from rocky.carapace import A_BREATH_MM       # noqa: E402  (the physical stroke)

N = 5
STONE = "#8d8377"
STEEL = "#6b7079"
BRONZE = "#b08d57"
GLOW = "#ff9d3a"


def _rotz(deg: float) -> np.ndarray:
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _tris(mesh: trimesh.Trimesh, xf: np.ndarray, shift=(0.0, 0.0, 0.0)) -> np.ndarray:
    v = mesh.vertices @ xf.T + np.asarray(shift)
    return v[mesh.faces]


def _shade(base: str, tris: np.ndarray) -> np.ndarray:
    """Cheap lambert shading from a face's z-facing so the solids read as 3D."""
    rgb = np.array(matplotlib.colors.to_rgb(base))
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ln[ln == 0] = 1.0
    nz = np.abs(n[:, 2] / ln)
    f = 0.45 + 0.55 * nz[:, None]
    return np.clip(rgb[None, :] * f, 0, 1)


def _add(ax, mesh, xf, base, shift=(0, 0, 0), alpha=1.0):
    t = _tris(mesh, xf, shift)
    pc = Poly3DCollection(t, alpha=alpha)
    pc.set_facecolor(_shade(base, t))
    pc.set_edgecolor((0, 0, 0, 0.06))
    pc.set_linewidth(0.15)
    ax.add_collection3d(pc)


def _panel(ax, plate, hub, cam, stroke, title):
    # Hub + scroll cam (shared, stationary in XY).
    _add(ax, hub, np.eye(3), STEEL, alpha=0.9)
    _add(ax, cam, np.eye(3), BRONZE, alpha=1.0)
    # Five petals at 72deg, each slid radially out by `stroke` along its azimuth.
    for k in range(N):
        az = k * 360.0 / N
        xf = _rotz(az)
        d = np.radians(az)
        shift = (stroke * np.cos(d), stroke * np.sin(d), 0.0)
        _add(ax, plate, xf, STONE, shift=shift, alpha=0.96)
        # Seam-LED glow hint: a bright short line on the trailing seam edge.
        se = np.radians(az + 36)
        r0, r1 = 46, 63
        ax.plot([r0 * np.cos(se), r1 * np.cos(se)],
                [r0 * np.sin(se), r1 * np.sin(se)],
                [59, 92], color=GLOW, lw=1.6 + 2.4 * (stroke / A_BREATH_MM), alpha=0.9)
    ax.set_title(title, fontsize=11, pad=0)
    ax.set_box_aspect((1, 1, 0.7))
    ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_zlim(35, 105)
    ax.set_axis_off()
    ax.view_init(elev=26, azim=-60)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "media" / "rocky_carapace_mech.png"
    plate = trimesh.load(PARTS / "carapace_plate.stl")
    hub = trimesh.load(PARTS / "carapace_hub.stl")
    cam = trimesh.load(PARTS / "carapace_cam.stl")

    fig = plt.figure(figsize=(12, 6.2))
    fig.suptitle("ROCKY-5 breathing carapace — one micro-servo, scroll cam, 5 petals (D-024)",
                 fontsize=13, y=0.98)
    for i, (stroke, title) in enumerate([(0.0, "EXHALE  (petals retracted, springs return)"),
                                         (A_BREATH_MM, f"INHALE  (+{A_BREATH_MM:.0f} mm radial, seams glow)")]):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        _panel(ax, plate, hub, cam, stroke, title)
    fig.text(0.5, 0.02,
             "1 servo turns the bronze scroll cam -> 5 stone petals slide radially in sync; "
             "orange = hidden WS2812 seam glow (speech ripple is LED-only, not servo).",
             ha="center", fontsize=9, color="#444")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130, bbox_inches="tight")
    print(f"[render] {out}  (plates {len(plate.faces)} tris, hub {len(hub.faces)}, cam {len(cam.faces)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
