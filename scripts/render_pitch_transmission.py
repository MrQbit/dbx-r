#!/usr/bin/env python3
"""Render the ROCKY-5 knee PITCH-TRANSMISSION study diagram (matplotlib Agg).

Draws BOTH options side by side — the chosen REMOTE DRIVESHAFT (winner) vs the
TIMING-BELT fallback — with the mechanism callouts, the cosmetic-shell envelope,
the M2.5 shell anchors, a to-scale cross-section comparison vs the old Ø54 cup, and
an isometric of the QA-clean shaft prototype. Reads docs/build_plan/
pitch_transmission_facts.json + the STLs from scripts/build_pitch_transmission.py
(run that first under cadpy). Host venv (matplotlib + trimesh; NO build123d).

Usage: .venv/bin/python scripts/render_pitch_transmission.py [out.png]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rocky.cad.parts import leg_geom as G  # noqa: E402

BP = ROOT / "docs" / "build_plan"
F = json.loads((BP / "pitch_transmission_facts.json").read_text())

PETG = "#8a8f98"
QDD = "#e8873a"
SHAFT = "#3a6ea8"
BEVEL = "#8e44ad"
BELT = "#2e8b57"
AXIS = "#c02b3a"
GOOD = "#2e8b57"
BAD = "#c02b3a"
SHELL = "#b0894f"

P1 = G.P1[0]          # femur_pitch axis x = 60
P2 = G.P2[0]          # knee axis x = 133
ENV = F["shell_envelope"]["mechanism_envelope_mm"]
SHELL_OD = F["shell_envelope"]["cosmetic_shell_outer_mm"]


def _tag(ax, x, y, text, color="#222", fs=8.2, weight="normal", ha="left"):
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va="center", weight=weight,
            zorder=20)


def _callout(ax, x, y, tx, ty, text, color="#222", fs=8.0):
    ax.add_patch(FancyArrowPatch((tx, ty), (x, y), arrowstyle="-", color=color,
                                 lw=0.8, alpha=0.7, zorder=15))
    _tag(ax, tx, ty, text, color=color, fs=fs)


def draw_shaft(ax):
    ax.set_title("CHOSEN — REMOTE RC DRIVESHAFT  (motor in the body, slim leg)",
                 fontsize=11, color=GOOD, weight="bold")
    # cosmetic shell envelope over the leg segments (dashed) ------------------
    for (xa, xb) in [(P1 + 8, P2 - 16), (P2 + 12, P2 + 78)]:
        ax.add_patch(Rectangle((xa, -ENV / 2), xb - xa, ENV, fill=False,
                               ec=SHELL, ls=(0, (5, 3)), lw=1.3, zorder=2))
    _tag(ax, P2 + 45, -ENV / 2 - 10, "cosmetic stone SHELL envelope (Ø%.0f leg, mech ≤Ø%.0f)"
         % (SHELL_OD, ENV), color=SHELL, fs=8.0, ha="center")

    # body / hip cluster + QDD -------------------------------------------------
    ax.add_patch(FancyBboxPatch((-18, -34), 46, 68, boxstyle="round,pad=1",
                                fc="#33373d", ec="#22252a", zorder=3))
    _tag(ax, 5, 30, "HIP CLUSTER / BODY", color="w", fs=8.0, ha="center")
    ax.add_patch(Circle((6, 0), 23, fc=QDD, ec="#a85a1a", zorder=4))
    _tag(ax, 6, 0, "QDD", color="w", fs=9, weight="bold", ha="center")
    _callout(ax, 6, -22, 40, -54, "EduLite-05 QDD in the BODY:\n15 rad/s, BACKDRIVABLE, 242 g",
             color=QDD)

    # driveshaft down the femur -----------------------------------------------
    ax.plot([P1, P2 - 8], [0, 0], color=SHAFT, lw=3.0, zorder=5)
    _callout(ax, (P1 + P2) / 2, 0, (P1 + P2) / 2 + 8, 30,
             "Ø6 RC driveshaft in a Ø12 tube\n(femur wraps a shaft, not a motor)", color=SHAFT)

    # double-cardan CVD at femur_pitch (P1) -----------------------------------
    ax.add_patch(Circle((P1, 0), 9, fc="none", ec=SHAFT, lw=2.2, zorder=6))
    ax.add_patch(Circle((P1 - 9, 0), 4.5, fc=SHAFT, ec="#22406a", zorder=6))
    ax.add_patch(Circle((P1 + 9, 0), 4.5, fc=SHAFT, ec="#22406a", zorder=6))
    _axis_pt(ax, P1)
    _callout(ax, P1, -9, P1 - 18, -34,
             "DOUBLE-CARDAN CVD on the\nfemur_pitch axis: 80°→2×40°\n(single CVD tops out ~50°)",
             color=SHAFT)

    # knee bevel box (P2) ------------------------------------------------------
    ax.add_patch(FancyBboxPatch((P2 - 14, -14), 28, 28, boxstyle="round,pad=0.6",
                                fc=PETG, ec="#5f636b", zorder=6))
    ax.add_patch(Circle((P2 - 7, 0), 8, fc=BEVEL, ec="#5b2c6f", zorder=7))
    ax.add_patch(Circle((P2, 8), 8, fc=BEVEL, ec="#5b2c6f", zorder=7))
    _axis_pt(ax, P2)
    _callout(ax, P2, -14, P2 + 6, -44,
             "KNEE miter BEVEL M1 16T:16T, 1:1\n(turns shaft→knee axis)\nbacklash ~%.1f° total"
             % F["shaft"]["backlash_deg"], color=BEVEL)

    # tibia driven segment -----------------------------------------------------
    ax.add_patch(FancyBboxPatch((P2 + 12, -ENV / 2), 66, ENV, boxstyle="round,pad=0.6",
                                fc=PETG, ec="#5f636b", alpha=0.6, zorder=3))
    _tag(ax, P2 + 45, 0, "tibia", color="#555", fs=8, ha="center")

    # M2.5 shell anchors -------------------------------------------------------
    for ax_x in (P1 + 14, P2 - 16, P2 + 46):
        ax.add_patch(Circle((ax_x, ENV / 2), 2.6, fc="none", ec="#222", lw=1.4, zorder=8))
        ax.plot([ax_x], [ENV / 2], marker="+", color="#222", ms=6, zorder=9)
    _callout(ax, P1 + 14, ENV / 2, P1 + 30, 46,
             "M2.5 heat-set + bolt shell anchors\n(2/segment, NOT clips) — shell unbolts",
             color="#222")

    ax.text(P1 + 30, -ENV / 2 - 34, "★ WINNER", fontsize=15, color=GOOD, weight="bold",
            ha="center")
    ax.set_xlim(-28, P2 + 92)
    ax.set_ylim(-74, 62)
    ax.set_aspect("equal")
    ax.axis("off")


def _axis_pt(ax, x):
    ax.plot([x], [0], marker="o", color=AXIS, ms=5, zorder=12)
    ax.plot([x, x], [-3, 3], color=AXIS, lw=1.0, zorder=12)


def draw_belt(ax):
    ax.set_title("FALLBACK — LOCAL TIMING BELT  (simpler, but motor stays on the leg)",
                 fontsize=11, color="#9a7d20", weight="bold")
    b = F["belt"]["belt"]
    pd = b["pulley_pd_mm"]
    # shell envelope
    ax.add_patch(Rectangle((P1 - 6, -ENV / 2), (P2 + 60) - (P1 - 6), ENV, fill=False,
                           ec=SHELL, ls=(0, (5, 3)), lw=1.3, zorder=2))
    _tag(ax, P1 + 40, ENV / 2 + 6, "same Ø%.0f shell envelope" % SHELL_OD, color=SHELL, fs=8)

    # femur beam
    ax.add_patch(FancyBboxPatch((P1 - 4, -pd / 2 - 6), (P2 + 4) - (P1 - 4), pd + 12,
                                boxstyle="round,pad=0.6", fc=PETG, ec="#5f636b", zorder=3))
    # QDD motor pod ON the femur (busts the shell)
    pod_r = F["belt"]["stations"][0]["cross_section_mm"] / 2
    ax.add_patch(Circle((P1, 0), pod_r, fc=QDD, ec=BAD, lw=2.4, zorder=5))
    ax.add_patch(Circle((P1, 0), pd / 2, fc="#c9752e", ec="#a85a1a", zorder=6))
    _tag(ax, P1, 0, "QDD", color="w", fs=8, weight="bold", ha="center")
    _callout(ax, P1, -pod_r, P1 - 20, -46,
             "Ø%.0f MOTOR POD on the femur\nBUSTS the slim shell (✗)" % (pod_r * 2),
             color=BAD)

    # belt + pulleys
    ax.plot([P1, P2], [pd / 2, pd / 2], color=BELT, lw=2.6, zorder=7)
    ax.plot([P1, P2], [-pd / 2, -pd / 2], color=BELT, lw=2.6, zorder=7)
    ax.add_patch(Circle((P2, 0), pd / 2, fc="none", ec=BELT, lw=2.6, zorder=7))
    _axis_pt(ax, P2)
    _callout(ax, (P1 + P2) / 2, pd / 2, (P1 + P2) / 2, 40,
             "HTD-5M %g mm belt, %g T pulleys (PD %.1f)\n1:1, L≈%.0f→%.0f mm stock; backlash ~0.5°"
             % (b["width_mm"], b["pulley_teeth"], pd, b["pitch_length_mm"], b["stock_length_mm"]),
             color=BELT)
    # idler tensioner
    ax.add_patch(Circle(((P1 + P2) / 2, -pd / 2 - 5), 4, fc="none", ec="#555", lw=1.6, zorder=7))
    _callout(ax, (P1 + P2) / 2, -pd / 2 - 5, (P1 + P2) / 2 + 20, -40,
             "625ZZ idler tensioner", color="#555")
    _tag(ax, P2, -pd / 2 - 22, "knee slim (Ø%.0f) ✓ but the motor pod is the problem"
         % F["belt"]["stations"][2]["cross_section_mm"], color="#555", fs=8, ha="center")

    ax.set_xlim(P1 - 40, P2 + 70)
    ax.set_ylim(-72, 60)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_xsec(ax):
    ax.set_title("Knee cross-section — leg slims 54 → 27 mm (to scale)", fontsize=10.5)
    items = [
        (-70, OLD_CUP_DIA := 54, BAD, "OLD Ø54\nside-cup", "the fat joint"),
        (0, F["shaft"]["stations"][2]["cross_section_mm"], GOOD, "SHAFT knee\nØ%.0f bevel box"
         % F["shaft"]["stations"][2]["cross_section_mm"], "fits shell ✓"),
        (66, F["belt"]["stations"][0]["cross_section_mm"], QDD, "BELT motor\nØ%.0f pod"
         % F["belt"]["stations"][0]["cross_section_mm"], "busts shell ✗"),
    ]
    for cx, d, col, lab, sub in items:
        # shell envelope + shell OD reference
        ax.add_patch(Circle((cx, 0), SHELL_OD / 2, fill=False, ec=SHELL, ls=(0, (4, 3)), lw=1.0))
        ax.add_patch(Circle((cx, 0), ENV / 2, fill=False, ec="#999", ls=":", lw=0.9))
        ax.add_patch(Circle((cx, 0), d / 2, fc=col, ec="#333", alpha=0.85))
        _tag(ax, cx, -38, lab, color="#222", fs=8.2, ha="center")
        _tag(ax, cx, -50, sub, color=col, fs=8, ha="center", weight="bold")
    _tag(ax, -70, 34, "— shell Ø%.0f · ⋯ mech env Ø%.0f" % (SHELL_OD, ENV), color="#666", fs=7.5)
    ax.set_xlim(-100, 100)
    ax.set_ylim(-56, 40)
    ax.set_aspect("equal")
    ax.axis("off")


def _add_mesh(ax, mesh, base, alpha=1.0):
    tr = mesh.vertices[mesh.faces]
    rgb = np.array(matplotlib.colors.to_rgb(base))
    n = np.cross(tr[:, 1] - tr[:, 0], tr[:, 2] - tr[:, 0])
    ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1.0
    f = 0.45 + 0.55 * np.abs(n[:, 2] / ln)[:, None]
    pc = Poly3DCollection(tr, alpha=alpha)
    pc.set_facecolor(np.clip(rgb[None, :] * f, 0, 1))
    pc.set_edgecolor((0, 0, 0, 0.06)); pc.set_linewidth(0.1)
    ax.add_collection3d(pc)


def draw_iso(ax):
    ax.set_title("Shaft prototype (QA-clean): femur_shaft_case + QDD + driveline",
                 fontsize=10)
    try:
        _add_mesh(ax, trimesh.load(BP / "ptx_shaft_case.stl"), PETG)
        _add_mesh(ax, trimesh.load(BP / "ptx_shaft_motor.stl"), QDD, 0.96)
        _add_mesh(ax, trimesh.load(BP / "ptx_shaft_drive.stl"), SHAFT, 0.96)
    except Exception as e:  # noqa: BLE001
        _tag(ax, 0, 0, f"(iso unavailable: {e})", fs=8)
    ax.set_box_aspect((1, 0.5, 0.5))
    ax.set_xlim(0, 150); ax.set_ylim(-40, 40); ax.set_zlim(-30, 30)
    ax.set_axis_off(); ax.view_init(elev=22, azim=-68)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BP / "pitch_transmission.png"
    fig = plt.figure(figsize=(18.0, 10.5))
    fig.suptitle("ROCKY-5 KNEE pitch transmission — get the QDD off the joint, keep speed + "
                 "backdrivability, slim the leg for the shell", fontsize=14, y=0.985)

    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], hspace=0.16, wspace=0.10,
                          left=0.02, right=0.98, top=0.93, bottom=0.10)
    draw_shaft(fig.add_subplot(gs[0, 0]))
    draw_belt(fig.add_subplot(gs[0, 1]))
    draw_xsec(fig.add_subplot(gs[1, 0]))
    draw_iso(fig.add_subplot(gs[1, 1], projection="3d"))

    cv = F["shaft"]["femur_pitch_cv"]
    foot = (
        "WINNER = REMOTE DRIVESHAFT: motor to the BODY (%.0f g/leg, %.0f g all-5) → femur/tibia "
        "wrap only a Ø12 shaft, so every LEG station fits the Ø%.0f under-shell envelope "
        "(CVD Ø24 · femur Ø%.0f · knee bevel Ø%.0f · tibia Ø%.0f).   BELT stays as fallback: "
        "lowest backlash (~0.5° vs ~2.5°) + simplest, but its Ø52 femur motor pod busts the slim shell."
        % (F["shaft"]["mass_to_body_g_per_leg"], F["shaft"]["mass_to_body_g_all5"], ENV,
           F["shaft"]["stations"][1]["cross_section_mm"],
           F["shaft"]["stations"][2]["cross_section_mm"],
           F["shaft"]["stations"][3]["cross_section_mm"]))
    fig.text(0.5, 0.055, foot, ha="center", fontsize=8.6, color="#333", wrap=True)
    fig.text(0.5, 0.022,
             "HONEST costs: femur_pitch travels %.0f° > single-CVD ~50° → needs a DOUBLE-CARDAN "
             "(2×%.0f°); knee backlash ~2.5° (2 cardans + 1 bevel) vs belt ~0.5°; hip now holds 3 QDDs "
             "(in the body). SHELL: split stone shell BOLTS on 6× M2.5 heat-set anchors/leg (2 per "
             "coxa/femur/tibia), heads hidden under a crag, unbolt to service the shafts."
             % (cv["max_bend_deg"], cv["per_cardan_deg_if_double"]),
             ha="center", fontsize=8.4, color="#555", wrap=True)
    fig.savefig(out, dpi=120)
    print(f"[render] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
