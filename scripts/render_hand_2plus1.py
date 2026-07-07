#!/usr/bin/env python3
"""Render the ROCKY-5 2+1 grip HAND close-up (D-038) — matplotlib Agg, no GL.

Loads the generated part STLs (run `make _cad ROBOT=rocky` first) and draws two
poses of the slim 2+1 manipulator:

  1. OPEN  (grip 0.0 rad): the thumb is raised/back and the TWO PRIMARY fingers
     stand together as a single spider-leg WALKING TIP (Rocky stands on the
     fingertips, not the palm).
  2. CLOSED (grip 2.2 rad): the thumb swings down/forward and PINCHES an object
     against the two primary tips — a firm 3-point grasp.

Runs in the HOST venv (matplotlib + trimesh; NO build123d). The pose math mirrors
rocky/cad/parts/grip_finger.py (that module imports build123d, so it can't load in
the host venv). Keep these constants in sync with it.

Usage: .venv/bin/python scripts/render_hand_2plus1.py [out.png]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "rocky" / "cad" / "parts"

# --- constants MIRROR rocky/cad/parts/grip_finger.py -----------------------
GRIP_OPEN_RAD, GRIP_CLOSED_RAD = 0.0, 2.2
THUMB_PIV = (12.0, 0.0, 34.0)
THUMB_OPEN_A, THUMB_CLOSED_A = 1.35, -0.60
DRIVE_STATION = (5.0, 18.0)
PRIM_TIP = (-24.2, 0.0, 82.7)
GRASP_OBJ_MM = 26.0

STONE = "#8d8377"
STONE_HI = "#a49a8c"
STEEL = "#6b7079"
BRONZE = "#b08d57"
OBJ = "#4f7d9e"
AXIS = "#c02b3a"


def _roty(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _thumb_angle(grip):
    return THUMB_OPEN_A + (grip / GRIP_CLOSED_RAD) * (THUMB_CLOSED_A - THUMB_OPEN_A)


def _crank_angle(grip):
    return math.radians(90.0 - 150.0 * (grip / GRIP_CLOSED_RAD))


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
    pc.set_edgecolor((0, 0, 0, 0.10)); pc.set_linewidth(0.15)
    ax.add_collection3d(pc)


def _ball(ax, r, c, color=OBJ, alpha=0.85):
    u, v = np.mgrid[0:2 * np.pi:20j, 0:np.pi:10j]
    x = c[0] + r * np.cos(u) * np.sin(v); y = c[1] + r * np.sin(u) * np.sin(v); z = c[2] + r * np.cos(v)
    ax.plot_surface(x, y, z, color=color, alpha=alpha, linewidth=0, shade=True)


def _frame(ax, title):
    ax.set_title(title, fontsize=12, pad=-2)
    ax.set_box_aspect((1, 1, 1.35))
    ax.set_xlim(-40, 40); ax.set_ylim(-40, 40); ax.set_zlim(-2, 92)
    ax.set_axis_off(); ax.view_init(elev=14, azim=-70)


def _panel(ax, palm, thumb, crown, grip, title, grasp=False):
    _add(ax, palm, STONE)                                   # slim wrist + 2 fused primaries
    # hidden drive crank in the wrist bay
    Rc = _roty(_crank_angle(grip))
    _add(ax, crown, BRONZE, R=Rc, t=(DRIVE_STATION[0], 0, DRIVE_STATION[1]), alpha=0.9)
    # the moving thumb
    Rt = _roty(_thumb_angle(grip))
    _add(ax, thumb, STONE_HI, R=Rt, t=THUMB_PIV)
    if grasp:
        _ball(ax, GRASP_OBJ_MM / 2, c=(-6, 0, 74))
    # labels
    ax.text(PRIM_TIP[0] - 4, 0, PRIM_TIP[2] + 6, "2 PRIMARIES\n(walking tip)",
            color="#2e6b34", fontsize=9, weight="bold", ha="center")
    tt = (THUMB_PIV[0] + 44 * math.sin(_thumb_angle(grip)),
          0, THUMB_PIV[2] + 44 * math.cos(_thumb_angle(grip)))
    ax.text(tt[0] + 8, 0, tt[2] + 4, "THUMB\n(opposing)", color="#8a4b1e",
            fontsize=9, weight="bold", ha="center")
    ax.text(0, 0, -2, "slim wrist\n(hidden micro-servo\n+ drive crank)", color="#555",
            fontsize=8, ha="center")
    _frame(ax, title)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "build_plan" / "hand_2plus1.png"
    palm = trimesh.load(PARTS / "grip_palm.stl")
    thumb = trimesh.load(PARTS / "grip_finger.stl")
    crown = trimesh.load(PARTS / "grip_crown.stl")

    fig = plt.figure(figsize=(13.5, 7.4))
    fig.suptitle("ROCKY-5 grip hand (D-038) — SLIM 2+1 wrist · two primary fingers = walking tip · "
                 "one opposing thumb · hidden micro-servo drive", fontsize=13, y=0.98)

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    _panel(ax1, palm, thumb, crown, GRIP_OPEN_RAD,
           "OPEN · grip 0.0 rad · thumb raised → foot-tip to STAND on")
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    _panel(ax2, palm, thumb, crown, GRIP_CLOSED_RAD,
           f"CLOSED · grip {GRIP_CLOSED_RAD:.1f} rad · thumb pinches → 3-point GRASP", grasp=True)

    fig.text(0.5, 0.03,
             "One grip micro-servo turns a hidden drive crank (bronze); its Ø5 follower pin swings the thumb's crank tail. "
             "The two primary fingers are fused rigid (a stable foot); only the thumb moves. Mount = tibia Ø41.5 PCD flange.",
             ha="center", fontsize=8.6, color="#444")
    fig.text(0.5, 0.008,
             "stone = printed PETG (slim palm + 2 primaries, and the thumb)   bronze = hidden micro-servo drive crank   "
             "blue = a grasped Ø26 mm object.  Cosmetic sculpt shell scales over this functional hand in Phase 2.",
             ha="center", fontsize=8.2, color="#666")

    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.09, wspace=0.02)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=125)
    print(f"[render] {out}  (palm {len(palm.faces)} tris, thumb {len(thumb.faces)}, crank {len(crown.faces)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
