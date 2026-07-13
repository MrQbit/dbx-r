"""Verify the v2 snap-fit gloves: fit gap, detent interference, tip wall,
seam gap, palm collision, articulation sweep, grip aperture."""
import json, math
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CD = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad/leg3_finger_covers"
ROOT = np.array([369.0, 7.0, 0.0])
AX = {"A": np.array([0.9272, 0.3664, +0.0779]), "B": np.array([0.9272, 0.3664, -0.0779])}
W4 = np.eye(4); W4[:3, :3] = [[0, 0, 1], [-1, 0, 0], [0, -1, 0]]; W4[:3, 3] = [329, 0, 0]

def L(p):
    m = trimesh.load(CD + "/" + p, process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)
    return m

cA, cB = L("prim_cover_A.stl"), L("prim_cover_B.stl")
cT = L("_thumb_cover_canonical.stl")
fA, fB = L("_finger_primA.stl"), L("_finger_primB.stl")
bT = L("_thumb_blade_canonical.stl")
pose = json.load(open(CD + "/_thumb_pose.json"))
M_open, M_closed = np.array(pose["M_open"]), np.array(pose["M_closed"])

print("== 1) WATERTIGHT + DIMS ==")
for nm, m in [("prim_cover_A", cA), ("prim_cover_B", cB), ("thumb_cover", cT)]:
    mm = trimesh.load(CD + f"/{nm}.stl" if "thumb" not in nm else CD + "/_thumb_cover_canonical.stl")
    lo, hi = m.bounds
    print(f"  {nm:14s} wt={m.is_watertight} dims={hi[0]-lo[0]:.1f} x {hi[1]-lo[1]:.1f} x {hi[2]-lo[2]:.1f} mm vol={m.volume:.0f} mm3")

print("== 2) SNAP FIT: cavity gap + detent (signed dist of finger surface into cover; -=gap) ==")
def fit_report(name, cover, finger, scoord, mouth, band, tipend):
    pts, _ = trimesh.sample.sample_surface(finger, 30000, seed=7)
    s = scoord(pts)
    sd = trimesh.proximity.signed_distance(cover, pts)
    nom = ((s > mouth + 2.5) & (s < band[0] - 1.0)) | ((s > band[1] + 1.0) & (s < tipend))
    det = (s > band[0] + 0.6) & (s < band[1] - 0.6)
    g = -sd[nom]      # gap (positive = clearance)
    d = sd[det]       # + = interference
    print(f"  {name}: slide gap med={np.median(g):.2f} p5={np.percentile(g,5):.2f} mm | "
          f"detent interference med={np.median(d):.2f} max={d.max():.2f} mm (n={det.sum()})")
fit_report("prim A", cA, fA, lambda P: (P - ROOT) @ AX["A"], 8, (38, 41), 44)
fit_report("prim B", cB, fB, lambda P: (P - ROOT) @ AX["B"], 8, (38, 41), 44)
fit_report("thumb ", cT, bT, lambda P: P[:, 2], 15, (17, 20), 44)

print("== 3) WALK-BEARING TIP WALL (cover outer surface in cap region -> finger dist - FIT) ==")
def tipwall(name, cover, finger, scoord, capfrom):
    pts, _ = trimesh.sample.sample_surface(cover, 40000, seed=9)
    s = scoord(pts)
    cap = s > capfrom
    fp, _ = trimesh.sample.sample_surface(finger, 40000, seed=11)
    d = cKDTree(fp).query(pts[cap])[0]
    print(f"  {name}: cap wall min={d.min()-0.2:.2f} med={np.median(d)-0.2:.2f} mm (n={cap.sum()})")
tipwall("prim A", cA, fA, lambda P: (P - ROOT) @ AX["A"], 46.0)
tipwall("prim B", cB, fB, lambda P: (P - ROOT) @ AX["B"], 46.0)
tipwall("thumb ", cT, bT, lambda P: P[:, 2], 46.5)

print("== 4) SEAM GAP + PALM COLLISION ==")
def mind(a, b, n=50000):
    pa, _ = trimesh.sample.sample_surface(a, n, seed=1)
    pb, _ = trimesh.sample.sample_surface(b, n, seed=2)
    return min(cKDTree(pb).query(pa)[0].min(), cKDTree(pa).query(pb)[0].min())
print(f"  seam gap prim_cover_A <-> prim_cover_B: {mind(cA, cB):.2f} mm")
palm = trimesh.load("/home/mrqbit/Downloads/dbx-r/rocky/cad/parts/grip_palm.stl", process=True)
palm.apply_transform(W4)
to = cT.copy(); to.apply_transform(M_open)
tc = cT.copy(); tc.apply_transform(M_closed)
for nm, cov in [("prim A", cA), ("prim B", cB), ("thumb OPEN", to), ("thumb CLOSED", tc)]:
    pts, _ = trimesh.sample.sample_surface(cov, 12000, seed=3)
    ins = palm.contains(pts)
    pen = 0.0
    if ins.sum():
        pen = float(trimesh.proximity.signed_distance(palm, pts[ins]).max())
    tag = "(detent by design)" if pen <= 0.30 and ins.sum() else ""
    print(f"  {nm:12s} vs palm(+fused primaries): pts inside={ins.mean()*100:.2f}% max_pen={pen:.2f} mm {tag}")

print("== 5) ARTICULATION SWEEP (thumb cover vs primary covers) ==")
prim = trimesh.util.concatenate([cA, cB])
PIV = pose["piv_local"]; od, cd = pose["open_deg"], pose["closed_deg"]
def T4(p):
    M = np.eye(4); M[:3, 3] = p; return M
def Ry4(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    M = np.eye(4); M[0, 0] = c; M[0, 2] = s; M[2, 0] = -s; M[2, 2] = c; return M
first = None
for gr in [0.0, 0.5, 1.0, 1.4, 1.7, 1.9, 2.0, 2.05, 2.1, 2.15, 2.2]:
    ang = od + (gr / 2.2) * (cd - od)
    m = cT.copy(); m.apply_transform(W4 @ T4(PIV) @ Ry4(ang))
    pts, _ = trimesh.sample.sample_surface(m, 5000, seed=5)
    ins = prim.contains(pts)
    pen = float(trimesh.proximity.signed_distance(prim, pts[ins]).max()) if ins.sum() else 0.0
    gap = ""
    if not ins.sum():
        pp, _ = trimesh.sample.sample_surface(prim, 20000, seed=6)
        gap = f" clearance={cKDTree(pp).query(pts)[0].min():.2f}mm"
    if ins.sum() and first is None: first = gr
    print(f"  grip={gr:4.2f} overlap={ins.mean()*100:5.2f}% max_pen={pen:.2f}mm{gap}")
print(f"  FIRST cover-cover contact at grip ~{first} rad")

print("== 6) GRIP APERTURE with covers ==")
mo = cT.copy(); mo.apply_transform(M_open)
tp_t, _ = trimesh.sample.sample_surface(mo, 30000, seed=8)
tp_p, _ = trimesh.sample.sample_surface(prim, 30000, seed=9)
sel_t = (mo.bounds[0] + mo.bounds[1]) / 2  # noqa
# pinch surfaces: thumb cover distal region vs primary covers distal region
zt = cT.copy(); zc = trimesh.sample.sample_surface(cT, 30000, seed=8)[0]
tip_mask_can = zc[:, 2] > 36
tip_t = (np.c_[zc[tip_mask_can], np.ones(tip_mask_can.sum())] @ M_open.T)[:, :3]
sP = (tp_p - ROOT) @ np.array([0.9272, 0.3664, 0.0])
tip_p = tp_p[sP > 36]
ap_open = cKDTree(tip_p).query(tip_t)[0].min()
print(f"  OPEN pinch aperture (thumb-cover tip <-> primary-cover tips): {ap_open:.1f} mm")
allmin = cKDTree(tp_p).query(trimesh.sample.sample_surface(mo, 30000, seed=10)[0])[0].min()
print(f"  OPEN overall min clearance thumb-cover <-> primary covers: {allmin:.2f} mm")
print("DONE verify")
