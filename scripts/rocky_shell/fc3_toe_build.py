"""LEG3 toe boot — REAL toy 3-B foot-tip sculpt re-purposed as the toe/ankle
cosmetic (operator: puppet principle — derive tip from the ORIGINAL geometry).
Mirrors leg2's fc_toe_build.py; leg3-specific adaptations are flagged [LEG3].

Source: leg3_aligned_3B.stl = the o3d-aligned toy tibia+foot in the chassis frame.
[LEG3] 3-B is the FORKED foot: two prongs with an OPEN cleft window (aligned
x~222..305) that converge into a single merged toe tip (x~305..340). The boot is
built from the merged-tip region (x>291, incl. the convergence crease); the open
fork window itself stays visible on the enclosed 3B shell (fork preserved there).
[LEG3] the cleft separation direction sits at ~+30 deg from +Y in this leg's o3d
roll, so the boot SOURCE region is rolled +60 deg about X to register the
convergence crease onto the glove seam plane (leg2's cleft landed there natively).
The shell itself keeps its o3d roll — only the boot piece is re-registered.

Transform: anisotropic stretch (axial 1.10 about the tip, radial 1.45 about the
toe axis) so the REAL surface spans x[~327..380], swallowing the chassis foot
core + collar + wrist; the crease lands on the +y face where the fingers emerge.

Carves (all + clearance): chassis foot-core/wrist/palm +1.5, primary gloves +0.8,
the THUMB SWEPT VOLUME (13 poses grip 0->2.2) +1.2 so the grip still articulates.
Radial functional floor only where the collar demands it (reported).
Also exports the two REAL FORK-BRANCH surfaces for the glove outer graft
([LEG3] grafts come from the true fork branches x[245..303], not just tip lips).
"""
import json, math
import numpy as np
import trimesh
from trimesh import creation, boolean
from skimage import measure

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
CD = SP + "/leg3_finger_covers"
BP = "/home/mrqbit/Downloads/dbx-r/docs/build_plan"

AX_K, RAD_K = 1.10, 1.45     # [LEG3] merged tip is shorter/slimmer than 2-B's taper
SRC_TIP, DST_TIP = 340.2, 380.0
ROLL_DEG = 60.0              # [LEG3] cleft-to-seam registration (see header)
MOUTH_X = 324.0              # [LEG3] shell tapers off by ~336 (slim fork tip): mouth pulled proximal so the boot laps over it — no exposed collar ring (leg2 used 330)

def voxel_clean(m, pitch=0.35, keep=None):
    vg = m.voxelized(pitch).fill()
    mat = np.pad(vg.matrix.astype(np.uint8), 2)
    v, f, _, _ = measure.marching_cubes(mat.astype(float), 0.5)
    v = v - 2.0
    vw = (np.c_[v, np.ones(len(v))] @ vg.transform.T)[:, :3]
    out = trimesh.Trimesh(vw, f[:, ::-1], process=True)
    trimesh.smoothing.filter_taubin(out, lamb=0.5, nu=-0.53, iterations=10)
    if not out.is_volume:
        out = max(out.split(only_watertight=False), key=lambda q: abs(q.volume))
    return out

def dilated(m, d, its=0):
    mm = m
    for _ in range(its): mm = mm.subdivide()
    n = mm.vertex_normals
    return trimesh.Trimesh(mm.vertices + n * d, mm.faces, process=False)

def stl_jitter_export(m, path):
    import manifold3d as m3d
    mesh = m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                    tri_verts=np.asarray(m.faces, np.uint32))
    man = m3d.Manifold(mesh).simplify(0.01)
    mm3 = man.to_mesh()
    mm = trimesh.Trimesh(np.asarray(mm3.vert_properties[:, :3], np.float64),
                         np.asarray(mm3.tri_verts), process=False)
    idx = np.arange(len(mm.vertices), dtype=np.uint64)
    j = np.stack([(idx * k % 9973) / 9973.0 - 0.5
                  for k in (2654435761, 40503, 2246822519)], axis=1) * 0.004
    mm = trimesh.Trimesh(mm.vertices + j, mm.faces, process=False)
    mm.export(path)
    print(f"    export {path.split('/')[-1]}: wt={mm.is_watertight} faces={len(mm.faces)}")
    return mm

def rollX(V, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    W = V.copy()
    W[:, 1] = c * V[:, 1] - s * V[:, 2]
    W[:, 2] = s * V[:, 1] + c * V[:, 2]
    return W

# ---------- 1) REAL sculpt source: distal foot region, watertight ----------
full = trimesh.load(SP + "/leg3_aligned_3B.stl", process=True)
fm = full.vertices[full.faces].mean(axis=1)
region = trimesh.Trimesh(full.vertices, full.faces[fm[:, 0] > 291], process=True)
region = voxel_clean(region, 0.3)          # closes the open cut -> watertight solid
print("region volume?", region.is_volume, "bounds", np.round(region.bounds, 1).tolist())

# [LEG3] roll the boot source so the convergence crease sits on the glove seam
Vr = rollX(region.vertices, ROLL_DEG)
region = trimesh.Trimesh(Vr, region.faces, process=False)
# [LEG3] drop the up-branch STUB: the mouth plane truncates the rolled short
# branch into a detached-looking shard above the shell line (z>21 rolled, x<312).
# The shell keeps the real fork; the boot keeps only the merged tip + crease.
fmr = region.vertices[region.faces].mean(axis=1)
keepf = ~((fmr[:, 2] > 21.0) & (fmr[:, 0] < 312.0))
region = trimesh.Trimesh(region.vertices, region.faces[keepf], process=True)
region = voxel_clean(region, 0.3)
print("stub-trimmed region bounds", np.round(region.bounds, 1).tolist())
# groove/toe-axis center: median of the merged tip (x>312) in the rolled frame
tipm = region.vertices[region.vertices[:, 0] > 312]
GROOVE_Y, GROOVE_Z = float(np.median(tipm[:, 1])), float(np.median(tipm[:, 2]))
print("rolled toe-axis center (GROOVE_Y,GROOVE_Z)=(%.2f,%.2f)" % (GROOVE_Y, GROOVE_Z))

# ---------- 2) anisotropic placement of the REAL surface ----------
V = region.vertices.copy()
Vx = DST_TIP - AX_K * (SRC_TIP - V[:, 0])
Vy = (V[:, 1] - GROOVE_Y) * RAD_K
Vz = (V[:, 2] - GROOVE_Z) * RAD_K
foot = trimesh.Trimesh(np.c_[Vx, Vy, Vz], region.faces, process=False)
print("scaled foot bounds", np.round(foot.bounds, 1).tolist())
foot_real = foot.copy()      # [LEG3] snapshot for the %-real-sculpt metric

# ---------- 3) radial functional floors (collar band) ----------
v = foot.vertices.copy()
r = np.hypot(v[:, 1], v[:, 2])
band1 = np.clip((v[:, 0] - 330) / 4, 0, 1) * np.clip((348 - v[:, 0]) / 4, 0, 1)
push = np.clip(28.8 - r, 0, None) * band1
outward = np.zeros_like(v)
safe = r > 1e-3
outward[safe, 1] = v[safe, 1] / r[safe]
outward[safe, 2] = v[safe, 2] / r[safe]
v += outward * push[:, None]
floored = float((push > 0.05).sum()) / len(v) * 100
# [LEG3] the floor engages heavily (slim fork tip vs Ø57.6 collar) and would
# leave a machined cylinder: re-crag the floored band with the matched stone
# noise family (chassis clearance is guaranteed later by the +1.5mm carves).
from fc_noise import noise4 as _n4f
pushed = push > 0.05
v[pushed] += outward[pushed] * (1.5 * _n4f(v[pushed], 55))[:, None]
foot = trimesh.Trimesh(v, foot.faces, process=False)
print("radial floor applied to %.1f%% of verts, max push %.1fmm" % (floored, push.max()))
# [LEG3] the deep fork crease + collar floor self-intersects (crease walls pushed
# through the outer skin) -> re-canonicalize through voxels before carving, else
# the manifold booleans fragment the boot (leg2's shallow groove never crossed).
foot = voxel_clean(foot, 0.33)
print("voxel re-canonicalized:", foot.is_volume, "bounds", np.round(foot.bounds, 1).tolist())

# ---------- 4) REAL FORK-BRANCH surfaces registered to the fingers ----------
# [LEG3] the glove outers graft from the TRUE fork branches (x 245..303), the
# leg's signature feature; split by z sign in the rolled frame about the crease.
AX_F = {"A": np.array([0.9272, 0.3664, +0.0779]), "B": np.array([0.9272, 0.3664, -0.0779])}
ROOTF = np.array([369.0, 7.0, 0.0])
region2 = trimesh.Trimesh(full.vertices, full.faces[(fm[:, 0] > 245) & (fm[:, 0] < 303)],
                          process=True)
region2 = voxel_clean(region2, 0.35)
region2 = trimesh.Trimesh(rollX(region2.vertices, ROLL_DEG), region2.faces, process=False)
# crease z-center: midpoint of the two branch z-centroids
zz = region2.vertices[:, 2]
zc0 = float(np.median(zz))
up = zz > zc0
zc = 0.5 * (zz[up].mean() + zz[~up].mean())
print("branch split: crease z-center=%.1f (up n=%d dn n=%d)" % (zc, up.sum(), (~up).sum()))
fm0 = region2.vertices[region2.faces].mean(axis=1)
for tag, sgn in (("A", +1), ("B", -1)):
    keep = sgn * (fm0[:, 2] - zc) > 1.5
    pr = trimesh.Trimesh(region2.vertices, region2.faces[keep], process=True)
    V0 = pr.vertices - pr.vertices.mean(0)
    w, E = np.linalg.eigh(V0.T @ V0)
    a0 = E[:, -1]
    if a0[0] < 0: a0 = -a0
    L = (V0 @ a0).max() - (V0 @ a0).min()
    G = np.median(np.linalg.norm(V0 - np.outer(V0 @ a0, a0), axis=1)) * 2
    afin = AX_F[tag]
    kax, krad = 47.0 / L, 27.0 / G
    vx = np.cross(a0, afin); c = a0 @ afin; sN = np.linalg.norm(vx)
    K = np.array([[0, -vx[2], vx[1]], [vx[2], 0, -vx[0]], [-vx[1], vx[0], 0]])
    R = np.eye(3) + K + K @ K * ((1 - c) / max(sN**2, 1e-12))
    par = np.outer(V0 @ a0, a0)
    V1 = (par * kax + (V0 - par) * krad) @ R.T
    smin = (V1 @ afin).min()
    V1 = V1 + (ROOTF + afin * (9.0 - smin))
    out = trimesh.Trimesh(V1, pr.faces, process=False)
    out.export(CD + f"/_prong_{tag}.stl")
    print(f"prong {tag}: srcL={L:.1f} girth={G:.1f} kax={kax:.2f} krad={krad:.2f} faces={len(pr.faces)}")

# ---------- 5) carve tools ----------
def load_volume(p):
    m = trimesh.load(p, process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)
    return m

hand = trimesh.load(BP + "/leg_chassis_neutral_hand.stl", process=True)
fmh = hand.vertices[hand.faces].mean(axis=1)
hand_d = trimesh.Trimesh(hand.vertices, hand.faces[fmh[:, 0] > 300], process=True)
hand_c = voxel_clean(hand_d, 0.4)
hand_c = dilated(hand_c, 1.5)
frame = trimesh.load(BP + "/leg_chassis_neutral_frame.stl", process=True)
fmf = frame.vertices[frame.faces].mean(axis=1)
frame_d = trimesh.Trimesh(frame.vertices, frame.faces[fmf[:, 0] > 300], process=True)
frame_c = dilated(voxel_clean(frame_d, 0.4), 1.5)
gA = dilated(load_volume(CD + "/prim_cover_A.stl"), 0.8)
gB = dilated(load_volume(CD + "/prim_cover_B.stl"), 0.8)
pose = json.load(open(CD + "/_thumb_pose.json"))
od, cd_ = pose["open_deg"], pose["closed_deg"]; PIV = pose["piv_local"]
W4 = np.eye(4); W4[:3, :3] = [[0, 0, 1], [-1, 0, 0], [0, -1, 0]]; W4[:3, 3] = [329, 0, 0]
def T4(p):
    M = np.eye(4); M[:3, 3] = p; return M
def Ry4(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    M = np.eye(4); M[0, 0] = c; M[0, 2] = s; M[2, 0] = -s; M[2, 2] = c; return M
thumbc = load_volume(CD + "/_thumb_cover_canonical.stl")
blade = trimesh.load(CD + "/_thumb_canonical.stl", process=True)
blade = voxel_clean(blade, 0.35)
sweep = []
for gr in np.linspace(0, 2.2, 13):
    ang = od + (gr / 2.2) * (cd_ - od)
    M = W4 @ T4(PIV) @ Ry4(ang)
    for src in (thumbc, blade):
        mm = dilated(src, 1.2)
        mm.apply_transform(M)
        sweep.append(mm)
mouth = creation.box(extents=(200, 200, 200),
                     transform=trimesh.transformations.translation_matrix((MOUTH_X - 100 - 7, 0, 0)))
Tc = np.eye(4)
Tc[:3, :3] = trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0))[:3, :3]
Tc[:3, 3] = (MOUTH_X - 7, 0, 0)
cone = creation.cone(radius=80, height=26, transform=Tc)   # apex distal: slanted cut
cone.invert() if cone.volume < 0 else None

# ---------- 6) boolean assembly ----------
toe = foot
Td = np.eye(4)
Td[:3, :3] = trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0))[:3, :3]
Td[:3, 3] = (337.7, 0, 0)
dcone = creation.cone(radius=54, height=24.3, transform=Td)   # x = 362 - 0.45r
dbox = creation.box(extents=(200, 220, 220),
                    transform=trimesh.transformations.translation_matrix((337.7 + 100, 0, 0)))
dcut = boolean.difference([dbox, dcone], engine="manifold")
ytrim = creation.box(extents=(80, 80, 240),
                     transform=trimesh.transformations.translation_matrix((346 + 40, -40, 0)))
cutters = [mouth, cone, hand_c, frame_c, gA, gB, dcut, ytrim] + sweep
for i, c in enumerate(cutters):
    try:
        toe = boolean.difference([toe, c], engine="manifold")
    except Exception as e:
        cc = voxel_clean(c, 0.5)
        toe = boolean.difference([toe, cc], engine="manifold")
        print(f"  cutter {i}: voxel fallback")
parts = toe.split(only_watertight=False)
for q in sorted(parts, key=lambda q: -abs(q.volume))[:6]:
    print("  component vol=%.0f bounds=%s" % (q.volume, np.round(q.bounds, 1).tolist()))
toe = max(parts, key=lambda q: abs(q.volume))
from fc_noise import noise4 as _n4
nrm = toe.vertex_normals
amp = np.full(len(toe.vertices), 0.9)
rec = (nrm[:, 0] > 0.45) & (toe.vertices[:, 0] > 340)
amp[rec] = 2.2
toe_presoften = toe.copy()
tv = toe.vertices + nrm * (amp * _n4(toe.vertices, 77))[:, None]
toe = trimesh.Trimesh(tv, toe.faces, process=False)
mm = stl_jitter_export(toe, SP + "/leg3_enclosed_toecover.stl")
lo, hi = mm.bounds
print("TOE leg3: dims %.1f x %.1f x %.1f vol=%.0f" % (hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2], mm.volume))

# ---------- 7) %-REAL-SCULPT metric (definition identical intent to leg2) ----------
# fraction of the FINAL boot surface lying within 1.0 mm of the anisotropically-
# placed REAL 3-B surface (pre-floor, pre-carve); crag softening is +-0.9mm typ.
from scipy.spatial import cKDTree
kd = cKDTree(trimesh.sample.sample_surface(foot_real, 300000, seed=22)[0])
# (a) final exported surface (incl. crag-soften pass +-0.9..2.2mm)
pf, _ = trimesh.sample.sample_surface(mm, 120000, seed=21)
d = kd.query(pf, workers=-1)[0]
# (b) pre-soften OUTER surface (what leg2's "untouched" number describes):
#     radially-outward-facing faces, i.e. the visible stone, before the
#     carve-wall softening pass
pf2, fi2 = trimesh.sample.sample_surface(toe_presoften, 120000, seed=23)
n2 = toe_presoften.face_normals[fi2]
rr = pf2[:, 1:3] / np.maximum(np.linalg.norm(pf2[:, 1:3], axis=1, keepdims=True), 1e-9)
outerm = (n2[:, 1] * rr[:, 0] + n2[:, 2] * rr[:, 1]) > 0.2
d2 = kd.query(pf2[outerm], workers=-1)[0]
print("REAL-SCULPT boot: outer visible surface %.1f%% within 1.0mm of the real "
      "3-B sculpt (pre-soften; n=%d)" % (100 * (d2 < 1.0).mean(), outerm.sum()))
print("  final surface (all faces, post-soften): %.1f%% <1mm, %.1f%% <2mm; "
      "floor-adjusted %.1f%% of verts" % (100 * (d < 1.0).mean(), 100 * (d < 2.0).mean(), floored))
print("DONE toe leg3 (real sculpt surface, fork crease registered to glove seam)")
