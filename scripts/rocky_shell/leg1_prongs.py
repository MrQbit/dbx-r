"""LEG1: watertight distal-region solid from the REAL aligned 1-C open-hand blade
+ the two REAL PRONG surfaces (the sculpt's own flat-blade fingers, forked in z)
registered to the functional primary fingers for the glove outer graft.
Adapted from fc_toe_build.py sections 1+4 (leg2 recipe).
1-C fork: cleft/groove at z=-1.5 (edge dips to x~325.6), prong +z tip x~340.8,
prong -z tip x~341.7. Sculpt thumb nub on -y at x~300-318 (stays on the boot)."""
import numpy as np, trimesh
from trimesh import creation
from skimage import measure

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
CD = SP + "/leg1_finger_covers"

GROOVE_Y, GROOVE_Z = -3.5, -1.5     # 1-C blade cleft centre (probe: leg1_blade_probe)
SRC_TIP = 341.7

def voxel_clean(m, pitch=0.35):
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

full = trimesh.load(SP + "/leg1_aligned_1C.stl", process=True)
fm = full.vertices[full.faces].mean(axis=1)
region = trimesh.Trimesh(full.vertices, full.faces[fm[:, 0] > 279], process=True)
region = voxel_clean(region, 0.3)
region.export(SP + "/_leg1_region_raw.stl")
print("region volume?", region.is_volume, "bounds", np.round(region.bounds, 1).tolist())

# ---- REAL PRONG surfaces registered to the fingers (same targets as leg2) ----
AX_F = {"A": np.array([0.9272, 0.3664, +0.0779]), "B": np.array([0.9272, 0.3664, -0.0779])}
ROOTF = np.array([369.0, 7.0, 0.0])
fm0 = region.vertices[region.faces].mean(axis=1)
for tag, sgn in (("A", +1), ("B", -1)):
    keep = (fm0[:, 0] > 322) & (sgn * (fm0[:, 2] - GROOVE_Z) > 0.5)
    pr = trimesh.Trimesh(region.vertices, region.faces[keep], process=True)
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
    print(f"prong {tag}: srcL={L:.1f} girth={G:.1f} kax={kax:.2f} krad={krad:.2f} "
          f"faces={len(pr.faces)} placed_bounds={np.round(out.bounds,1).tolist()}")
print("DONE prongs")
