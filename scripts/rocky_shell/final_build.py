"""Consolidated final deliverable:
 - raw-piece joint primitives (sphere pegs / cylinder bores) -> radii
 - knee seating in statue frame (ball-center-to-socket-axis, seat depth)
 - per-piece coverage to statue + non-adjacent interpenetration check
 - composite render docs/build_plan/o3d_assembly.png (assembled front/top vs statue vs image1)
 - prints verification table; writes verify.json"""
import numpy as np, json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.spatial import cKDTree
from pyransac3d import Sphere, Cylinder
from reglib import *

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
T = {n: np.array(v) for n, v in json.load(open(SP + "/toy_assembled_o3d.json")).items()}
info = json.load(open("final_info.json"))

def statue_pts(k): return trimesh.sample.sample_surface(load_trimesh("statue"), k, seed=2)[0]
def piece_cloud(n, k):
    P = trimesh.sample.sample_surface(load_trimesh(n), k, seed=5)[0]
    return (P @ T[n][:3, :3].T) + T[n][:3, 3]
def to_st(n, p): return (np.atleast_2d(p) @ T[n][:3, :3].T) + T[n][:3, 3]

# ---------- raw joint primitives ----------
def endcaps(pts):
    c = pts.mean(0); X = pts - c
    ax = np.linalg.svd(X, full_matrices=False)[2][0]; t = X @ ax
    L = t.max() - t.min()
    return pts[t < t.min() + 0.22 * L], pts[t > t.max() - 0.22 * L]
def fit_s(p):
    c, r, i = Sphere().fit(p.astype(float), thresh=0.3, maxIteration=1200); return c, float(r), len(i)
def fit_c(p):
    c, a, r, i = Cylinder().fit(p.astype(float), thresh=0.3, maxIteration=1200); return c, a, float(r), len(i)

joint_prims = {}   # piece:end -> dict
plan = {"1-A": ("socket", "socket"), "2-A": ("socket", "ball"), "3-A": ("socket", "ball"),
        "4-A": ("socket", "ball"), "5-A": ("socket", "ball"),
        "2-B": ("socket", "socket"), "3-B": ("socket", "socket"),
        "4-B": ("socket", "socket"), "5-B": ("socket", "socket"), "1-C": ("peg", None)}
for n, (pk, dk) in plan.items():
    P = trimesh.sample.sample_surface(load_trimesh(n), 45000, seed=5)[0]
    prox, dist = endcaps(P)
    for cap, kind, pts in [("prox", pk, prox), ("dist", dk, dist)]:
        if kind is None: continue
        sc, sr, si = fit_s(pts); cc, ca, cr, ci = fit_c(pts)
        if kind in ("ball", "peg") and 1 < sr < 7:
            joint_prims[f"{n}:{cap}"] = {"kind": kind, "prim": "sphere", "r": sr,
                "center_st": to_st(n, sc)[0]}
        elif 1 < cr < 7:
            joint_prims[f"{n}:{cap}"] = {"kind": kind, "prim": "cylinder", "r": cr,
                "center_st": to_st(n, cc)[0], "axis_st": to_st(n, cc + ca)[0] - to_st(n, cc)[0]}

# knee seating: thigh dist ball vs foot prox socket axis (leg1: 1-C peg vs 1-A dist socket)
knee_rows = []
for L, (a, b) in {2: ("2-A", "2-B"), 3: ("3-A", "3-B"), 4: ("4-A", "4-B"), 5: ("5-A", "5-B")}.items():
    ball = joint_prims.get(f"{a}:dist"); sock = joint_prims.get(f"{b}:prox")
    if ball and sock and "axis_st" in sock:
        c = np.array(ball["center_st"]); p0 = np.array(sock["center_st"])
        ax = np.array(sock["axis_st"]); ax = ax / (np.linalg.norm(ax) + 1e-9)
        d = float(np.linalg.norm((c - p0) - np.dot(c - p0, ax) * ax))
        seat = float(np.dot(c - p0, ax))
        knee_rows.append((f"knee{L}", a, b, ball["r"], sock["r"], round(d, 2), round(seat, 2)))
# leg1: 1-C peg (ball) vs 1-A dist socket
b1 = joint_prims.get("1-C:prox"); s1 = joint_prims.get("1-A:dist")
if b1 and s1 and "axis_st" in s1:
    c = np.array(b1["center_st"]); p0 = np.array(s1["center_st"]); ax = np.array(s1["axis_st"])
    ax = ax / (np.linalg.norm(ax) + 1e-9)
    d = float(np.linalg.norm((c - p0) - np.dot(c - p0, ax) * ax))
    knee_rows.insert(0, ("wrist1", "1-C", "1-A", b1["r"], s1["r"], round(d, 2),
                         round(float(np.dot(c - p0, ax)), 2)))

# ---------- coverage + clearance ----------
st = statue_pts(120000); st_tree = cKDTree(st)
clouds = {n: piece_cloud(n, 16000) for n in PIECES}
allc = np.vstack(list(clouds.values()))
ds, _ = cKDTree(allc).query(st)
cover_1 = (ds < 1.0).mean() * 100; cover_2 = (ds < 2.0).mean() * 100
adj = {("torso", a) for a in LEG_A} | {(a, b) for a, b in
      [("1-A", "1-C"), ("2-A", "2-B"), ("3-A", "3-B"), ("4-A", "4-B"), ("5-A", "5-B")]}
adj |= {(b, a) for a, b in adj}
trees = {n: cKDTree(clouds[n]) for n in PIECES}
min_clear = []
for i in range(len(PIECES)):
    for j in range(i + 1, len(PIECES)):
        a, b = PIECES[i], PIECES[j]
        if (a, b) in adj: continue
        dd, _ = trees[b].query(clouds[a])
        ov = (dd < 1.0).mean() * 100
        min_clear.append((a, b, round(float(dd.min()), 2), round(ov, 1)))
worst = sorted(min_clear, key=lambda x: x[2])[:6]

# per-piece coverage
piece_cov = {}
for n in PIECES:
    dpc, _ = st_tree.query(clouds[n]); piece_cov[n] = round(float(np.sqrt((dpc**2).mean())), 3)

# ---------- print verification table ----------
print("\n===== PER-PIECE REGISTRATION (piece -> statue) =====")
print(f"{'piece':6s}{'method':20s}{'ICPfit':>8s}{'rmse':>7s}{'ovl%':>7s}{'surf_rmse':>10s}")
for n in PIECES:
    print(f"{n:6s}{info[n]['method']:20s}{info[n]['fit']:8.3f}{info[n]['rmse']:7.3f}"
          f"{info[n]['overlap_pct']:7.1f}{piece_cov[n]:10.3f}")
print("\n===== JOINT PRIMITIVES + SEATING (statue frame) =====")
print(f"{'joint':7s}{'peg':6s}{'socket':7s}{'ball_r':>8s}{'bore_r':>8s}{'ball->axis':>11s}{'seat':>7s}")
for r in knee_rows:
    print(f"{r[0]:7s}{r[1]:6s}{r[2]:7s}{r[3]:8.2f}{r[4]:8.2f}{r[5]:11.2f}{r[6]:7.2f}")
print("hip sockets (thigh proximal bores, r mm): " +
      ", ".join(f"{a}={joint_prims[a+':prox']['r']:.2f}" for a in LEG_A if a+":prox" in joint_prims))
print(f"\nSTATUE COVERAGE: {cover_1:.1f}% within 1.0mm, {cover_2:.1f}% within 2.0mm, "
      f"mean gap={ds.mean():.3f}mm, max gap={ds.max():.2f}mm")
print("NON-ADJACENT MIN CLEARANCE (should be >0; ovl% should be ~0):")
for a, b, mn, ov in worst:
    print(f"  {a}-{b}: min_dist={mn}mm overlap@1mm={ov}%")

json.dump({"piece": info, "piece_surf_rmse": piece_cov, "knees": knee_rows,
           "coverage_1mm": cover_1, "coverage_2mm": cover_2,
           "mean_gap": float(ds.mean()), "max_gap": float(ds.max()),
           "nonadj_clearance_worst": worst}, open("verify.json", "w"), indent=1, default=str)

# ---------- composite render ----------
colors = plt.cm.tab20(np.linspace(0, 1, len(PIECES)))
rc = {n: piece_cloud(n, 9000) for n in PIECES}
fig, ax = plt.subplots(2, 2, figsize=(11, 11))
for col, (ttl, (i, j)) in enumerate([("FRONT (X-Z)", (0, 2)), ("TOP (X-Y)", (0, 1))]):
    a0 = ax[0, col]
    for k, n in enumerate(PIECES):
        Pt = rc[n]; a0.scatter(Pt[:, i], Pt[:, j], s=0.6, color=colors[k], label=n)
    a0.set_title("OPEN3D-ASSEMBLED TOY  " + ttl, fontsize=10); a0.set_aspect("equal"); a0.axis("off")
    if col == 0: a0.legend(markerscale=8, fontsize=6, ncol=2, loc="upper right")
    a1 = ax[1, col]; a1.scatter(st[::4, i], st[::4, j], s=0.6, c="0.45")
    a1.set_title("SCULPTOR STATUE (ground truth)  " + ttl, fontsize=10); a1.set_aspect("equal"); a1.axis("off")
fig.tight_layout(); fig.savefig("panel_lr.png", dpi=120, bbox_inches="tight"); plt.close(fig)

left = Image.open("panel_lr.png").convert("RGB")
ref = Image.open(SP + "/docref/image1.jpg").convert("RGB")
H = left.height
ref = ref.resize((int(ref.width * H / ref.height), H))
comp = Image.new("RGB", (left.width + ref.width + 20, H), "white")
comp.paste(left, (0, 0)); comp.paste(ref, (left.width + 20, 0))
outp = "/home/mrqbit/Downloads/dbx-r/docs/build_plan/o3d_assembly.png"
comp.save(outp)
print(f"\nwrote {outp}  ({comp.width}x{comp.height})")
