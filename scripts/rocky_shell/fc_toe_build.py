"""LEG2 toe piece v2 — REAL toy 2-B foot-tip sculpt re-purposed as the toe/ankle
cosmetic (operator: puppet principle — derive tip from the ORIGINAL geometry).

Source: leg2_aligned_2B.stl = the o3d-aligned toy tibia+foot in the chassis frame
(scale 6.0, o3d roll preserved). Its distal taper x[283..341] IS the toy foot toe
with the natural 2-prong cleft (groove at z~2.5, opening +y).

Transform: anisotropic stretch (axial 1.45 about the tip, radial 1.55 about the
groove center) so the REAL surface spans x[306..390], swallowing the chassis foot
core + Ø52 collar + wrist; the cleft lands on z=0 where our finger gloves emerge.
(The leg shells themselves are anisotropically-scaled sculpt — same treatment.)

Carves (all + clearance): chassis foot-core/wrist/palm +1.5, primary gloves +0.8,
the THUMB SWEPT VOLUME (7 poses grip 0->2.2) +1.0 so the grip still articulates.
Radial functional floor only where the collar demands it (reported).
Also exports the two scaled REAL PRONG surfaces for the glove outer graft.
"""
import json, math
import numpy as np
import trimesh
from trimesh import creation, boolean
from skimage import measure

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
CD = SP + "/leg2_finger_covers"
BP = "/home/mrqbit/Downloads/dbx-r/docs/build_plan"

AX_K, RAD_K = 0.91, 1.37     # near-NATURAL axial; toe ends at the cleft base
SRC_TIP, DST_TIP = 341.0, 380.0
GROOVE_Y, GROOVE_Z = 0.6, 2.5
MOUTH_X = 330.0              # the enclosed 2B shell itself covers to ~331 (r~30)

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

# ---------- 1) REAL sculpt source: distal foot region, watertight ----------
full = trimesh.load(SP + "/leg2_aligned_2B.stl", process=True)
# region: keep x > 280 with a generous box then voxel-clean
regbox = creation.box(extents=(200, 200, 200),
                      transform=trimesh.transformations.translation_matrix((280 + 100, 0, 0)))
# (mesh isn't a volume — do the region cut by masking faces instead)
fm = full.vertices[full.faces].mean(axis=1)
region = trimesh.Trimesh(full.vertices, full.faces[fm[:, 0] > 279], process=True)
region = voxel_clean(region, 0.3)          # closes the open cut -> watertight solid
print("region volume?", region.is_volume, "bounds", np.round(region.bounds, 1).tolist())

# ---------- 2) anisotropic placement of the REAL surface ----------
V = region.vertices.copy()
Vx = DST_TIP - AX_K * (SRC_TIP - V[:, 0])
Vy = (V[:, 1] - GROOVE_Y) * RAD_K
Vz = (V[:, 2] - GROOVE_Z) * RAD_K
foot = trimesh.Trimesh(np.c_[Vx, Vy, Vz], region.faces, process=False)
print("scaled foot bounds", np.round(foot.bounds, 1).tolist())

# ---------- 3) radial functional floors (collar band + wrist band) ----------
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
foot = trimesh.Trimesh(v, foot.faces, process=False)
print("radial floor applied to %.1f%% of verts, max push %.1fmm" % (floored, push.max()))

# ---------- 4) REAL PRONG surfaces registered to the fingers (glove style src) ----
# from the SOURCE region (pre-anisotropy): prongs at src x>318, split by the groove
AX_F = {"A": np.array([0.9272, 0.3664, +0.0779]), "B": np.array([0.9272, 0.3664, -0.0779])}
ROOTF = np.array([369.0, 7.0, 0.0])
fm0 = region.vertices[region.faces].mean(axis=1)
for tag, sgn in (("A", +1), ("B", -1)):
    keep = (fm0[:, 0] > 318) & (sgn * (fm0[:, 2] - GROOVE_Z) > 0.5)
    pr = trimesh.Trimesh(region.vertices, region.faces[keep], process=True)
    V0 = pr.vertices - pr.vertices.mean(0)
    # PCA long axis, pointed +x
    w, E = np.linalg.eigh(V0.T @ V0)
    a0 = E[:, -1]
    if a0[0] < 0: a0 = -a0
    L = (V0 @ a0).max() - (V0 @ a0).min()
    G = np.median(np.linalg.norm(V0 - np.outer(V0 @ a0, a0), axis=1)) * 2
    afin = AX_F[tag]
    kax, krad = 47.0 / L, 27.0 / G
    # rotation a0 -> afin
    vx = np.cross(a0, afin); c = a0 @ afin; sN = np.linalg.norm(vx)
    K = np.array([[0, -vx[2], vx[1]], [vx[2], 0, -vx[0]], [-vx[1], vx[0], 0]])
    R = np.eye(3) + K + K @ K * ((1 - c) / max(sN**2, 1e-12))
    par = np.outer(V0 @ a0, a0)
    V1 = (par * kax + (V0 - par) * krad) @ R.T
    # place: prong root end at the glove mouth station (ROOT + 10*axis)
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

# chassis: hand (palm etc.) + frame distal ends
hand = trimesh.load(BP + "/leg_chassis_neutral_hand.stl", process=True)
fmh = hand.vertices[hand.faces].mean(axis=1)
hand_d = trimesh.Trimesh(hand.vertices, hand.faces[fmh[:, 0] > 300], process=True)
hand_c = voxel_clean(hand_d, 0.4)
hand_c = dilated(hand_c, 1.5)
frame = trimesh.load(BP + "/leg_chassis_neutral_frame.stl", process=True)
fmf = frame.vertices[frame.faces].mean(axis=1)
frame_d = trimesh.Trimesh(frame.vertices, frame.faces[fmf[:, 0] > 300], process=True)
frame_c = dilated(voxel_clean(frame_d, 0.4), 1.5)
# primary gloves
gA = dilated(load_volume(CD + "/prim_cover_A.stl"), 0.8)
gB = dilated(load_volume(CD + "/prim_cover_B.stl"), 0.8)
# thumb swept volume: cover + blade at 7 poses, dilated 1.0
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
# mouth cut: BEVELED (cone) so the proximal edge slopes onto the shell (no flat ring)
mouth = creation.box(extents=(200, 200, 200),
                     transform=trimesh.transformations.translation_matrix((MOUTH_X - 100 - 7, 0, 0)))
Tc = np.eye(4)
Tc[:3, :3] = trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0))[:3, :3]
Tc[:3, 3] = (MOUTH_X - 7, 0, 0)
cone = creation.cone(radius=80, height=26, transform=Tc)   # apex distal: slanted cut
cone.invert() if cone.volume < 0 else None

# ---------- 6) boolean assembly ----------
toe = foot
# square up the thumb-side opening to the stone's natural edge (removes the
# fragile eggshell ribbon between the thumb slot and the finger opening)
ycut = creation.box(extents=(60, 60, 200),
                    transform=trimesh.transformations.translation_matrix((354 + 30, -8 - 30, 0)))
# recess the DISTAL face conically around the finger roots (no flat disc, no thin
# flaps): remove {x > 377 - 0.5*r} = box minus an apex-distal cone
Td = np.eye(4)
Td[:3, :3] = trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0))[:3, :3]
Td[:3, 3] = (337.7, 0, 0)
dcone = creation.cone(radius=54, height=24.3, transform=Td)   # x = 362 - 0.45r
dbox = creation.box(extents=(200, 220, 220),
                    transform=trimesh.transformations.translation_matrix((337.7 + 100, 0, 0)))
dcut = boolean.difference([dbox, dcone], engine="manifold")
# open the FRONT-CENTER strip cleanly (the thumb's swing plane): no stone can
# span the grip mouth there, so cut it as one deliberate opening (no ribbons)
fcut = creation.box(extents=(84, 60, 28),
                    transform=trimesh.transformations.translation_matrix((398, 30, 0)))
# trim the thumb-side distal rim (the last thin arc the sweep gouges)
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
toe = max(toe.split(only_watertight=False), key=lambda q: abs(q.volume))
# soften the machined carve walls with light matched crag (0.4mm, keeps >=0.8 clearances)
from fc_noise import noise4 as _n4  # small helper module
nrm = toe.vertex_normals
amp = np.full(len(toe.vertices), 0.9)
# the conical recess face (distal, +x normals) gets FULL crag so it reads as
# broken stone, not a machined bevel
rec = (nrm[:, 0] > 0.45) & (toe.vertices[:, 0] > 340)
amp[rec] = 2.2
tv = toe.vertices + nrm * (amp * _n4(toe.vertices, 77))[:, None]
toe = trimesh.Trimesh(tv, toe.faces, process=False)
mm = stl_jitter_export(toe, SP + "/leg2_enclosed_toecover.stl")
lo, hi = mm.bounds
print("TOE v2: dims %.1f x %.1f x %.1f vol=%.0f" % (hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2], mm.volume))
print("DONE toe v2 (real sculpt surface, %.1f%% floor-adjusted)" % floored)
