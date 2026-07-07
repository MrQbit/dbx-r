#!/usr/bin/env python3
"""Render the ROCKY-5 leg CHASSIS build diagram (LOCKED, D-042) — matplotlib Agg.

Loads the posed STL groups written by scripts/build_leg_chassis.py (run that first
under cadpy) and draws two panels — NEUTRAL and a FLEXED+ROLLED pose — showing the
LOCKED architecture: the HIP CLUSTER (3 EduLite QDD per leg, in the body), the knee
DRIVESHAFT (double-cardan CVD at femur_pitch -> Ø6 shaft down the slim femur -> miter
bevel at the knee), the inline STS3215 roll servo in the shank, the 2+1 grip hand, the
Ø44 under-shell envelope drawn around the slim leg, and the M2.5 shell-anchor points.
Host venv (matplotlib + trimesh; NO build123d).

Usage: .venv/bin/python scripts/render_leg_chassis.py [out.png]
"""
from __future__ import annotations

import json
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
sys.path.insert(0, str(ROOT))
from rocky.cad.parts import leg_geom as G   # noqa: E402  (pure python, no build123d)

BP = ROOT / "docs" / "build_plan"
FACTS = json.loads((BP / "leg_chassis_facts.json").read_text())
RP = FACTS["roll_pose_rad"]
ROLLPOSE = (RP["coxa_yaw"], RP["femur_pitch"], RP["tibia_pitch"], RP["tibia_roll"])

PETG = "#8a8f98"
SERVO = "#e8873a"
HAND = "#43a047"
AXIS = "#c02b3a"


def _tris(mesh):
    return mesh.vertices[mesh.faces]


def _shade(base, tris):
    rgb = np.array(matplotlib.colors.to_rgb(base))
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1.0
    f = 0.42 + 0.58 * np.abs(n[:, 2] / ln)[:, None]
    return np.clip(rgb[None, :] * f, 0, 1)


def _add(ax, mesh, base, alpha=1.0):
    tr = _tris(mesh)
    pc = Poly3DCollection(tr, alpha=alpha)
    pc.set_facecolor(_shade(base, tr))
    pc.set_edgecolor((0, 0, 0, 0.05)); pc.set_linewidth(0.1)
    ax.add_collection3d(pc)


def _axis(ax, p, d, half, label, lab_off):
    a = np.array(p) - np.array(d) * half
    b = np.array(p) + np.array(d) * half
    ax.plot([a[0], b[0]], [a[1], b[1]], [a[2], b[2]], color=AXIS, lw=2.0, zorder=10)
    for e in (a, b):
        ax.scatter(*e, color=AXIS, s=6)
    lp = np.array(p) + np.array(lab_off)
    ax.text(lp[0], lp[1], lp[2], label, color=AXIS, fontsize=8.5, weight="bold")


def _frame(ax, title):
    ax.set_title(title, fontsize=11, pad=-2)
    ax.set_box_aspect((1, 0.6, 0.7))
    ax.set_xlim(-30, 250); ax.set_ylim(-80, 80); ax.set_zlim(-70, 95)
    ax.set_axis_off(); ax.view_init(elev=20, azim=-72)


def load(tag):
    return {g: trimesh.load(BP / f"leg_chassis_{tag}_{g}.stl")
            for g in ("frame", "servos", "hand")}


def _unit(a, b):
    v = np.array(b) - np.array(a)
    n = np.linalg.norm(v)
    return v / n if n else v


SHELL = "#3a7bd5"
ANCHOR_C = "#8e44ad"


def _shell_tube(ax, a, b, r=22.0, n=8):
    """Draw the Ø(2r) under-shell envelope as translucent rings along segment a->b."""
    a = np.array(a, float); b = np.array(b, float); d = b - a
    L = np.linalg.norm(d)
    if L < 1e-6:
        return
    d = d / L
    up = np.array([0, 0, 1.0])
    if abs(d @ up) > 0.9:
        up = np.array([0, 1.0, 0])
    u = np.cross(d, up); u /= np.linalg.norm(u)
    v = np.cross(d, u)
    th = np.linspace(0, 2 * np.pi, 22)
    for t in np.linspace(0.08, 0.92, n):
        c = a + d * L * t
        ring = c[None, :] + r * (np.cos(th)[:, None] * u[None, :] + np.sin(th)[:, None] * v[None, :])
        ax.plot(ring[:, 0], ring[:, 1], ring[:, 2], color=SHELL, lw=0.5, alpha=0.28)


def panel(ax, tag, q, title, label_axes):
    g = load(tag)
    _add(ax, g["frame"], PETG)
    _add(ax, g["servos"], SERVO, alpha=0.96)
    _add(ax, g["hand"], HAND, alpha=0.96)
    fk = G.fk(*q)
    # Ø44 under-shell envelope around the SLIM femur + tibia (the shaft-wrap sections).
    _shell_tube(ax, fk["p1"], fk["knee"])
    _shell_tube(ax, fk["knee"], fk["tip"])
    if label_axes:
        _axis(ax, (0, 0, 35), (0, 0, 1), 58, "coxa_yaw QDD (Z)", (8, 0, 46))
        _axis(ax, fk["p1"], (0, 1, 0), 52, "femur_pitch QDD (Y) + CVD", (-52, 56, 30))
        _axis(ax, fk["knee"], (0, 1, 0), 52, "knee — miter bevel (Y)", (-6, 58, 34))
        # tibia_roll (D-039): the 4th axis runs ALONG the tibia long axis (X).
        _axis(ax, fk["roll"], _unit(fk["knee"], fk["tip"]), 40,
              "tibia_roll STS (X)", (2, -34, -26))
        ax.text(G.TIP[0] + 8, 40, 44, "2+1 hand\n(2 primaries\n+ opposing thumb)",
                color=HAND, fontsize=8, weight="bold")
        # M2.5 shell-anchor markers on the slim femur/tibia tops.
        mid_f = (np.array(fk["p1"]) + np.array(fk["knee"])) / 2 + np.array([0, 0, 16])
        mid_t = (np.array(fk["knee"]) + np.array(fk["tip"])) / 2 + np.array([0, 0, 16])
        for p in (mid_f, mid_t):
            ax.scatter(*p, color=ANCHOR_C, s=14, marker="^", zorder=11)
        ax.text(mid_f[0] - 6, mid_f[1], mid_f[2] + 10, "M2.5 shell anchors",
                color=ANCHOR_C, fontsize=7.5, weight="bold")
        ax.text(-6, 0, -34, "Ø44 under-shell envelope", color=SHELL, fontsize=7.5, weight="bold")
    _frame(ax, title)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BP / "leg_chassis.png"
    fig = plt.figure(figsize=(16.0, 7.2))
    fig.suptitle("ROCKY-5 leg CHASSIS — LOCKED (D-042) · hip-cluster QDD (3/leg, in BODY) + knee DRIVESHAFT + inline roll STS · "
                 "coxa_yaw · femur_pitch · knee · tibia_ROLL", fontsize=13, y=0.98)

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    panel(ax1, "neutral", (0.0, 0.0, 0.0, 0.0),
          "NEUTRAL  ·  all joints 0  ·  3 hip QDD (ghost body) + CVD + Ø6 shaft + knee bevel + inline roll STS  ·  grip OPEN (foot-tip)", label_axes=True)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    panel(ax2, "rolled", ROLLPOSE,
          f"FLEXED + ROLLED  ·  femur {ROLLPOSE[1]:+.2f}, knee {ROLLPOSE[2]:+.2f}, tibia_ROLL {ROLLPOSE[3]:+.2f} rad  ·  grip CLOSED (grasp)",
          label_axes=False)

    env = FACTS["reach_envelope"]
    knee = FACTS["knee_selfcollision_free_max_rad"]
    roll_lim = FACTS["params_joint_limits_rad"]["tibia_roll"]
    foot = "  ·  ".join([
        "actuators: 3× EduLite-05 QDD in the HIP CLUSTER (coxa_yaw + femur_pitch + knee, ~242 g each — mass in the BODY) · knee driven REMOTELY via double-cardan CVD → Ø6 shaft → M1 16T:16T miter bevel (1:1, ~2.5° backlash, 0.9 eff) · inline STS3215 roll · grip micro",
        f"reach r {env['radius_mm'][0]:.0f}–{env['radius_mm'][1]:.0f} mm, z {env['z_mm'][0]:.0f}…{env['z_mm'][1]:.0f} mm, yaw {env['yaw_sweep_deg']:.0f}°",
        f"knee free ≤ {knee:.2f} rad ({math.degrees(knee):.0f}°, slim femur restores the FULL fold); tibia_roll ±{roll_lim[1]:.1f} rad free (0 mm³)",
    ])
    fig.text(0.5, 0.045, foot, ha="center", fontsize=7.6, color="#444")
    fig.text(0.5, 0.018,
             "grey = printed PETG frame (hip yoke · coxa bracket = hip cluster · SLIM femur = Ø12-shaft wrap · tibia bracket + shank)   "
             "orange = EduLite QDD hip cluster + double-cardan CVD + Ø6 shaft + knee miter bevel + inline STS3215 roll   green = 2+1 grip hand   "
             "blue = Ø44 under-shell envelope   ▲ = M2.5 shell anchors (2/segment).  Cosmetic stone shell scales over this frame in Phase 2.",
             ha="center", fontsize=7.6, color="#666")

    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.09, wspace=0.02)
    fig.savefig(out, dpi=125)
    print(f"[render] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
