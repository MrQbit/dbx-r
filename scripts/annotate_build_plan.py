"""Annotate the Blender build-plan renders into the operator-facing deliverables.

Reads  docs/build_plan/_raw_{exploded,cutaway,ghost}.png  + build_plan_coords.json
       + build_plan_facts.json  and writes the LABELLED sheets:
   exploded_leg.png   cutaway_joint.png   assembled_ghost.png   servo_layout.png
   build_plan_sheets.pdf   (all four, one per page)

Run:  .venv/bin/python scripts/annotate_build_plan.py
"""
import json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle, FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "docs", "build_plan")
COORDS = json.load(open(os.path.join(BP, "build_plan_coords.json")))
FACTS = json.load(open(os.path.join(BP, "build_plan_facts.json")))

BG = "#20242e"; PANEL = "#2a2f3b"; INK = "#eef1f6"; SUB = "#aab3c2"
ORANGE = "#ee7f2b"; CYAN = "#3ec3e0"; GREEN = "#3ecf72"; STONE = "#b9b2a6"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.edgecolor": SUB})


def _img_ax(fig, rect, png):
    ax = fig.add_axes(rect); ax.imshow(mpimg.imread(png)); ax.axis("off")
    return ax


def callout(ax, xy, text, tx, ty, color=ORANGE, ha="left", fs=13):
    ax.annotate(text, xy=xy, xycoords="data", xytext=(tx, ty), textcoords="data",
                color=INK, fontsize=fs, ha=ha, va="center", weight="medium",
                bbox=dict(boxstyle="round,pad=0.35", fc=PANEL, ec=color, lw=1.6),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8,
                                shrinkA=6, shrinkB=4,
                                connectionstyle="arc3,rad=0.15"))


def dot(ax, xy, color):
    ax.add_patch(Circle(xy, 7, fc=color, ec="white", lw=1.2, zorder=5))


def header(fig, title, sub):
    fig.text(0.5, 0.965, title, ha="center", va="top", fontsize=21, weight="bold", color=INK)
    fig.text(0.5, 0.925, sub, ha="center", va="top", fontsize=12.5, color=SUB)


# =========================================================================
def sheet_exploded():
    c = COORDS["exploded"]; W = 1100
    fig = plt.figure(figsize=(15, 11), dpi=100); fig.patch.set_facecolor(BG)
    header(fig, "ROCKY-5  —  Exploded Leg",
           "One leg along its axis: thorax socket → hip servo → coxa → knee1 servo → femur → "
           "knee2 servo → tibia → hand.  Assemble proximal → distal.")
    ax = _img_ax(fig, [0.0, 0.02, 0.72, 0.88], os.path.join(BP, "_raw_exploded.png"))
    ax.set_xlim(0, W); ax.set_ylim(W, 0)
    steps = [
        ("thorax", "1", "Thorax dome", "hosts the hip socket (Ø46 pilot); leg root sinks in", STONE),
        ("servo_hip", "2", "HIP servo", "EduLite-05  Ø46×44  — buried in the thorax socket", ORANGE),
        ("coxa", "3", "Coxa", "28.8×38.3×47.7 mm shell (×5)", STONE),
        ("knee1_cover", "4", "Knee1 cover", "cosmetic stone sleeve — clips over servo (×5)", STONE),
        ("servo_knee1", "5", "KNEE1 servo", "EduLite-05  Ø46×44  — flat mount (37 mm neck)", ORANGE),
        ("femur", "6", "Femur", "33.1×51.9×58.6 mm shell (×5)", STONE),
        ("knee2_cover", "7", "Knee2 cover", "cosmetic stone sleeve — clips over servo (×5)", STONE),
        ("servo_knee2", "8", "KNEE2 servo", "EduLite-05  Ø46×44  — flat mount (48 mm neck)", ORANGE),
        ("tibia", "9", "Tibia + hand", "74.5×31.3×83.8 mm; sacred 3-finger hand distal (×5)", STONE),
        ("servo_grip", "10", "GRIP micro", "MG90S  22.8×12.2×28.5  — drives the 3 fingers", GREEN),
    ]
    # numbered badges on the parts, de-clumped so none overlap (thin leader back
    # to the true anchor when a badge is nudged clear)
    anchors = [(k, n, tuple(c[k][:2]), col) for k, n, _, _, col in steps if k in c]
    pos = [list(a[2]) for a in anchors]
    R = 19.0; MIN = 2 * R + 6
    for _ in range(220):
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                dx = pos[j][0] - pos[i][0]; dy = pos[j][1] - pos[i][1]
                d = math.hypot(dx, dy) or 0.01
                if d < MIN:
                    push = (MIN - d) / 2; ux, uy = dx / d, dy / d
                    pos[i][0] -= ux * push; pos[i][1] -= uy * push
                    pos[j][0] += ux * push; pos[j][1] += uy * push
    for (key, num, anch, col), (bx, by) in zip(anchors, pos):
        if math.hypot(bx - anch[0], by - anch[1]) > 6:
            ax.plot([anch[0], bx], [anch[1], by], color="white", lw=1.0, alpha=0.6, zorder=5)
            ax.add_patch(Circle(anch, 3.5, fc=col, ec="white", lw=0.8, zorder=5))
        ax.add_patch(Circle((bx, by), R, fc=col, ec="white", lw=1.8, zorder=6))
        ax.text(bx, by, num, ha="center", va="center", fontsize=12.5, weight="bold",
                color="#1a1d24", zorder=7)
    # legend panel on the right
    px0 = 0.735
    fig.patches.append(FancyBboxPatch((px0, 0.05), 0.25, 0.85, transform=fig.transFigure,
                       boxstyle="round,pad=0.006", fc=PANEL, ec=SUB, lw=1.2, zorder=1))
    fig.text(px0 + 0.012, 0.87, "ASSEMBLY ORDER", fontsize=13.5, weight="bold", color=INK)
    yy = 0.835
    for key, num, name, desc, col in steps:
        fig.text(px0 + 0.016, yy, num, fontsize=12, weight="bold", color=col)
        fig.text(px0 + 0.042, yy, name, fontsize=11.5, weight="bold", color=INK)
        fig.text(px0 + 0.042, yy - 0.022, desc, fontsize=8.6, color=SUB)
        yy -= 0.052
    fig.text(px0 + 0.012, 0.075, "Orange = EduLite-05 leg servo   Green = grip micro\n"
             "Stone = printed shell / cover", fontsize=8.8, color=SUB)
    out = os.path.join(BP, "exploded_leg.png")
    fig.savefig(out, facecolor=BG); plt.close(fig); print("[sheet]", out); return out


def sheet_cutaway():
    c = COORDS["cutaway"]; W = 1100
    fig = plt.figure(figsize=(15, 11), dpi=100); fig.patch.set_facecolor(BG)
    header(fig, "ROCKY-5  —  Leg Cutaway",
           "Near shell wall clipped away: each EduLite-05 body sits in the proximal socket, "
           "its Ø24 output collar drives the next segment.  Now the joint reads as a mechanism.")
    ax = _img_ax(fig, [0.04, 0.02, 0.92, 0.88], os.path.join(BP, "_raw_cutaway.png"))
    ax.set_xlim(0, W); ax.set_ylim(W, 0)
    cuts = [
        ("servo_hip", "HIP  ·  EduLite-05 Ø46×44", "body seated in the thorax socket;\noutput collar drives the coxa", 140, 150, ORANGE),
        ("servo_knee1", "KNEE1  ·  EduLite-05 Ø46×44", "flat mount (37 mm neck < 46 mm body);\ncover sleeve hides body + gap", 470, 130, ORANGE),
        ("servo_knee2", "KNEE2  ·  EduLite-05 Ø46×44", "flat mount (48 mm neck);\ncover sleeve over the joint", 830, 250, ORANGE),
        ("grip", "GRIP  ·  MG90S 22.8×12.2×28.5", "micro-servo in the hand,\ndrives the 3-finger crown cam", 900, 640, GREEN),
    ]
    for key, title, desc, tx, ty, col in cuts:
        xy = c[key][:2]; dot(ax, xy, col)
        callout(ax, xy, f"{title}\n{desc}", tx, ty, color=col)
    # tiny "what the servo is" key
    fig.text(0.045, 0.055,
             "EduLite-05 = Ø46×44 housing  +  Ø24×8 output collar  +  Ø52 mounting flange (Ø41.5 PCD).\n"
             "The 25 mm coxa↔femur gap at knee1 is the servo seat pocket — the modelled Ø46 body fills it "
             "(coxa 10.9 mm & femur 11.8 mm from the servo axis → both inside the 23 mm body radius: BRIDGED).",
             fontsize=9.6, color=SUB)
    out = os.path.join(BP, "cutaway_joint.png")
    fig.savefig(out, facecolor=BG); plt.close(fig); print("[sheet]", out); return out


def sheet_ghost():
    c = COORDS["ghost"]; W = 1100
    fig = plt.figure(figsize=(14, 12), dpi=100); fig.patch.set_facecolor(BG)
    header(fig, "ROCKY-5  —  Ghosted Assembly",
           "Segments semi-transparent so every servo is visible in place: 3 EduLite-05 per leg × 5 legs, "
           "plus a grip micro-servo in each hand.")
    ax = _img_ax(fig, [0.05, 0.02, 0.90, 0.87], os.path.join(BP, "_raw_ghost.png"))
    ax.set_xlim(0, W); ax.set_ylim(W, 0)
    for key, title, tx, ty, col in [
        ("hip", "HIP servo (×5)", 250, 250, ORANGE),
        ("knee1", "KNEE1 servo (×5)", 250, 470, ORANGE),
        ("knee2", "KNEE2 servo (×5)", 250, 900, ORANGE),
        ("grip", "GRIP micro-servo (×5 hands)", 900, 980, GREEN),
        ("thorax", "Thorax dome (ghosted)", 620, 120, STONE)]:
        if key not in c: continue
        xy = c[key][:2]; dot(ax, xy, col)
        callout(ax, xy, title, tx, ty, color=col)
    fig.text(0.5, 0.055,
             "17 × EduLite-05 total  =  15 leg-joint servos (5×3)  +  2 grip-drive (manipulator legs).   "
             "5 × grip micro-servo (MG90S).",
             ha="center", fontsize=11, color=SUB)
    out = os.path.join(BP, "assembled_ghost.png")
    fig.savefig(out, facecolor=BG); plt.close(fig); print("[sheet]", out); return out


def sheet_layout():
    piv = FACTS["pivots_world_mm"]
    hip = piv["hip"][:2]; kn1 = piv["knee1"][:2]; kn2 = piv["knee2"][:2]; hand = piv["hand"][:2]
    fig = plt.figure(figsize=(15, 10.5), dpi=100); fig.patch.set_facecolor(BG)
    header(fig, "ROCKY-5  —  Servo Layout & BOM",
           "Top-down schematic of all servo positions (true 5-fold radial symmetry) with the actuator bill of materials.")
    ax = fig.add_axes([0.02, 0.03, 0.60, 0.86]); ax.set_facecolor(BG)
    ax.set_aspect("equal"); ax.axis("off")
    lim = 230; ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    # thorax footprint
    ax.add_patch(Circle((0, 0), 96, fc="none", ec=STONE, lw=1.5, ls="--"))
    ax.text(0, 0, "THORAX\n(hip sockets)", ha="center", va="center", color=SUB, fontsize=9)
    def rot(p, a):
        ca, sa = math.cos(a), math.sin(a)
        return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)
    for k in range(5):
        a = math.radians(72 * k)
        H, K1, K2, HD = rot(hip, a), rot(kn1, a), rot(kn2, a), rot(hand, a)
        ax.plot(*zip(H, K1, K2, HD), color="#6f7787", lw=2.0, zorder=1)
        for p, col, r in [(H, ORANGE, 11), (K1, ORANGE, 11), (K2, ORANGE, 11)]:
            ax.add_patch(Circle(p, r, fc=col, ec="white", lw=1.2, zorder=3))
        ax.add_patch(Rectangle((HD[0] - 9, HD[1] - 9), 18, 18, fc=GREEN, ec="white", lw=1.2, zorder=3))
        ax.text(HD[0] * 1.12, HD[1] * 1.12, f"leg {k+1}", ha="center", va="center",
                color=SUB, fontsize=9)
    # legend for the schematic
    ax.add_patch(Circle((-lim + 22, -lim + 30), 9, fc=ORANGE, ec="white", lw=1))
    ax.text(-lim + 40, -lim + 30, "EduLite-05 leg joint (hip / knee1 / knee2)", va="center", fontsize=9.5, color=INK)
    ax.add_patch(Rectangle((-lim + 13, -lim + 8), 18, 18, fc=GREEN, ec="white", lw=1))
    ax.text(-lim + 40, -lim + 17, "grip micro-servo (one per hand)", va="center", fontsize=9.5, color=INK)

    # BOM table on the right
    tx = 0.635
    fig.patches.append(FancyBboxPatch((tx, 0.06), 0.345, 0.80, transform=fig.transFigure,
                       boxstyle="round,pad=0.006", fc=PANEL, ec=SUB, lw=1.2))
    fig.text(tx + 0.015, 0.83, "ACTUATOR BOM", fontsize=15, weight="bold", color=INK)
    # column header + divider
    fig.text(tx + 0.015, 0.792, "QTY", fontsize=9.5, weight="bold", color=SUB)
    fig.text(tx + 0.055, 0.792, "SERVO  ·  SIZE  ·  ROLE", fontsize=9.5, weight="bold", color=SUB)
    fig.add_artist(plt.Line2D([tx + 0.012, tx + 0.332], [0.783, 0.783],
                   color=SUB, lw=1, transform=fig.transFigure))
    rows = [
        ("15", "EduLite-05", "Ø46×44, 242 g", "leg joints: 5 legs × (hip, knee1, knee2)"),
        ("2", "EduLite-05", "Ø46×44, 242 g", "grip drive (manipulator legs 1 & 4)"),
        ("= 17", "EduLite-05 total", "Ø41.5 PCD, Ø24 output", "1.8 / 6 N·m QDD actuator"),
        ("5", "grip micro MG90S", "22.8×12.2×28.5, 13.4 g", "3-finger hand — one per hand"),
        ("1", "MG90S (breathing)", "22.8×12.2×28.5", "carapace scroll-cam (not a joint)"),
    ]
    yy = 0.752
    for qty, servo, size, role in rows:
        fig.text(tx + 0.015, yy, qty, fontsize=11, color=CYAN, weight="bold")
        fig.text(tx + 0.055, yy, servo, fontsize=11, color=INK, weight="bold")
        fig.text(tx + 0.055, yy - 0.021, size, fontsize=8.6, color=SUB)
        fig.text(tx + 0.055, yy - 0.038, role, fontsize=8.6, color=SUB)
        yy -= 0.078
    fig.text(tx + 0.015, 0.145,
             "EduLite-05 total: 17\nGrip micro total: 5  (+1 breathing-cam micro)\n"
             "Source: common/cad_lib/components.rocky_components()", fontsize=9, color=SUB)
    out = os.path.join(BP, "servo_layout.png")
    fig.savefig(out, facecolor=BG); plt.close(fig); print("[sheet]", out); return out


def main():
    sheets = [sheet_exploded(), sheet_cutaway(), sheet_ghost(), sheet_layout()]
    pdf_path = os.path.join(BP, "build_plan_sheets.pdf")
    with PdfPages(pdf_path) as pdf:
        for s in sheets:
            fig = plt.figure(figsize=(15, 11), dpi=110); fig.patch.set_facecolor(BG)
            ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
            ax.imshow(mpimg.imread(s))
            pdf.savefig(fig, facecolor=BG); plt.close(fig)
    print("[pdf]", pdf_path)


main()
