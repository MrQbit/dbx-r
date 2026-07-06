#!/usr/bin/env python3
"""Preview the ROCKY-5 grip HAND mechanism (D-027) — matplotlib Agg, no pyglet/GL.

Loads the generated part STLs (run `make _cad ROBOT=rocky` first) and draws three
panels:
  1. EXPLODED — the four printed pieces separated: stony palm, hidden spiral drive
     crown, and three Eridian-stone fingers.
  2. FLAT FOOT — grip 0.0 rad: fingers splayed horizontal, a broad tripod sole.
  3. GRASP — fingers closed onto a Ø50 mm object (the real 40–60 mm grip).

One grip servo turns the crown; its three spiral grooves push each finger's
follower pin, so all three swing in sync.

Runs in the HOST venv (matplotlib + trimesh; NO build123d), like
render_carapace_mech.py. Usage: .venv/bin/python scripts/render_grip_mech.py [out.png]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import yaml
import matplotlib
matplotlib.use("Agg")                       # headless, no pyglet/GL
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "rocky" / "cad" / "parts"

# Geometry constants MIRROR rocky/cad/parts/grip_finger.py (that module imports
# build123d, so it can't load in the host venv). Keep these in sync with it.
R_PIV, Z_PIV, FINGER_LEN, TIP_R = 38.0, 13.0, 46.0, 7.0
_MAN = yaml.safe_load((ROOT / "rocky" / "design" / "params.yaml").open())["manipulators"]
N_FINGERS = int(_MAN["fingers"])
GRIP_OPEN_RAD, GRIP_CLOSED_RAD = (float(v) for v in _MAN["grip_limit_rad"])


def azimuths():
    return [k * 360.0 / N_FINGERS for k in range(N_FINGERS)]


STONE = "#8d8377"
STONE_HI = "#a49a8c"
BRONZE = "#b08d57"
STEEL = "#6b7079"
OBJ = "#4f7d9e"

GRASP_OBJ_MM = 50.0
GRASP_RAD = math.acos(max(-1.0, (GRASP_OBJ_MM / 2 - R_PIV) / FINGER_LEN))   # grip that meets Ø50


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _finger_xf(grip_rad, az_deg):
    """Replicates grip_finger.finger_placed as a (R, t) affine on canonical verts."""
    az = math.radians(az_deg)
    R = _rot_z(az) @ _rot_y(-grip_rad)
    t = np.array([R_PIV * math.cos(az), R_PIV * math.sin(az), Z_PIV])
    return R, t


def _tris(mesh, R=np.eye(3), t=(0, 0, 0)):
    v = mesh.vertices @ R.T + np.asarray(t, float)
    return v[mesh.faces]


def _shade(base, tris):
    rgb = np.array(matplotlib.colors.to_rgb(base))
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1.0
    f = 0.45 + 0.55 * np.abs(n[:, 2] / ln)[:, None]
    return np.clip(rgb[None, :] * f, 0, 1)


def _add(ax, mesh, base, R=np.eye(3), t=(0, 0, 0), alpha=1.0):
    tr = _tris(mesh, R, t)
    pc = Poly3DCollection(tr, alpha=alpha)
    pc.set_facecolor(_shade(base, tr))
    pc.set_edgecolor((0, 0, 0, 0.06)); pc.set_linewidth(0.12)
    ax.add_collection3d(pc)


def _ball(ax, r, c=(0, 0, 0), color=OBJ, alpha=0.85):
    u, v = np.mgrid[0:2 * np.pi:20j, 0:np.pi:10j]
    x = c[0] + r * np.cos(u) * np.sin(v); y = c[1] + r * np.sin(u) * np.sin(v); z = c[2] + r * np.cos(v)
    ax.plot_surface(x, y, z, color=color, alpha=alpha, linewidth=0, shade=True)


def _frame(ax, title, lim=98, zlo=-70, zhi=95, elev=22, azim=-62):
    ax.set_title(title, fontsize=11, pad=0)
    ax.set_box_aspect((1, 1, 0.82))
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(zlo, zhi)
    ax.set_axis_off(); ax.view_init(elev=elev, azim=azim)


def _panel_exploded(ax, palm, crown, finger):
    _add(ax, palm, STONE, t=(0, 0, -55))
    _add(ax, crown, BRONZE, t=(0, 0, -18))
    # fingers floated outward/up along their azimuths at a half-open pose
    for az in azimuths():
        R, t = _finger_xf(0.6, az)
        d = math.radians(az)
        shift = np.array([48 * math.cos(d), 48 * math.sin(d), 48])
        _add(ax, finger, STONE_HI, R=R, t=t + shift)
    _frame(ax, "EXPLODED  ·  palm + drive crown + 3 fingers", zlo=-70, zhi=95)


def _panel_pose(ax, palm, crown, finger, grip, title, obj_mm=None, elev=22):
    _add(ax, palm, STONE)
    _add(ax, crown, BRONZE, t=(0, 0, 0))
    for az in azimuths():
        R, t = _finger_xf(grip, az)
        _add(ax, finger, STONE, R=R, t=t)
    if obj_mm:
        rho = R_PIV + FINGER_LEN * math.cos(grip)
        z = Z_PIV + FINGER_LEN * math.sin(grip)
        _ball(ax, obj_mm / 2, c=(0, 0, z - 4))
    _frame(ax, title, zlo=-5, zhi=95, elev=elev)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "media" / "rocky_grip_mech.png"
    palm = trimesh.load(PARTS / "grip_palm.stl")
    crown = trimesh.load(PARTS / "grip_crown.stl")
    finger = trimesh.load(PARTS / "grip_finger.stl")

    fig = plt.figure(figsize=(16.5, 6.0))
    fig.suptitle("ROCKY-5 grip hand (D-027) — one servo · hidden spiral crown · three synced Eridian-stone fingers",
                 fontsize=13, y=0.99)
    ax1 = fig.add_subplot(1, 3, 1, projection="3d"); _panel_exploded(ax1, palm, crown, finger)
    ax2 = fig.add_subplot(1, 3, 2, projection="3d")
    _panel_pose(ax2, palm, crown, finger, GRIP_OPEN_RAD,
                f"FLAT FOOT  ·  grip 0.0 rad  ·  tripod sole Ø{2*(R_PIV+FINGER_LEN):.0f}", elev=52)
    ax3 = fig.add_subplot(1, 3, 3, projection="3d")
    _panel_pose(ax3, palm, crown, finger, GRASP_RAD,
                f"GRASP  ·  grip {GRASP_RAD:.2f} rad  ·  holding Ø{GRASP_OBJ_MM:.0f} mm", obj_mm=GRASP_OBJ_MM)

    rho_c = R_PIV + FINGER_LEN * math.cos(GRIP_CLOSED_RAD)
    gap = rho_c * math.sqrt(3) - 2 * TIP_R
    fig.text(0.5, 0.02,
             f"grip range [0.0, {GRIP_CLOSED_RAD:.1f}] rad: 0 = flat splayed foot; fingers pass vertical into a firm "
             f"3-jaw grasp. Full close (2.2): tips at Ø{2*rho_c:.0f}, clearance ≈ {gap:.1f} mm (no self-collision). "
             f"Ø40–60 mm objects grip at 1.75–1.97 rad. Bronze = hidden spiral drive crown (a printable cam, not gear teeth).",
             ha="center", fontsize=8.5, color="#444")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=125, bbox_inches="tight")
    print(f"[render] {out}  (palm {len(palm.faces)} tris, crown {len(crown.faces)}, finger {len(finger.faces)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
