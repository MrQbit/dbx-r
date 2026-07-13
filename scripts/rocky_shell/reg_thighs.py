"""Re-register the 5 thighs (N-A) harder: finer voxel + many restarts, keep all
distinct pose clusters. For each cluster report centroid, radius & angle around
the torso axis, fit, rmse, and overlap with the (fixed, well-placed) same-leg
distal piece. Lets us pick the true inner-thigh pose bridging torso->foot."""
import numpy as np, json, sys, time
from scipy.spatial import cKDTree
from reglib import *

VOX = 1.2
N = 40
t0 = time.time()
cands0 = json.load(open("reg_candidates.json"))

st = tm_to_pcd(load_trimesh("statue"), 240000, seed=1)
st_d, st_f = preprocess(st, VOX)
tgt = np.asarray(st_d.points); tgt_n = np.asarray(st_d.normals)
print(f"statue {len(tgt)} {time.time()-t0:.1f}s"); sys.stdout.flush()

TORSO_C = np.array([-7.1, 7.1])  # torso centroid XY in statue frame
# fixed distal pieces (best cand #0), for overlap/direction reference
distal = {"1-A": "1-C", "2-A": "2-B", "3-A": "3-B", "4-A": "4-B", "5-A": "5-B"}
dist_tree = {}; dist_dir = {}
for a, b in distal.items():
    Tb = np.array(cands0[b][0]["T"])
    Pb = trimesh.sample.sample_surface(load_trimesh(b), 8000, seed=3)[0]
    Pb = (Pb @ Tb[:3, :3].T) + Tb[:3, 3]
    dist_tree[a] = cKDTree(Pb)
    v = Pb.mean(0)[:2] - TORSO_C
    dist_dir[a] = np.degrees(np.arctan2(v[1], v[0])) % 360

out = {}
for a in LEG_A:
    pc = tm_to_pcd(load_trimesh(a), 90000, seed=1)
    sd, sf = preprocess(pc, VOX)
    src = np.asarray(sd.points)
    Pfull = trimesh.sample.sample_surface(load_trimesh(a), 8000, seed=3)[0]
    cl = []  # clusters: [transl_centroid, best dict]
    for seed in range(N):
        g = global_ransac(sd, sf, st_d, st_f, VOX, seed=seed)
        T, fit, rmse = icp_manual(src, tgt, tgt_n, g.transformation, VOX, p2plane=True)
        cen = ((Pfull @ T[:3, :3].T) + T[:3, 3]).mean(0)
        d = {"T": T, "fit": fit, "rmse": rmse, "cen": cen}
        for c in cl:
            if np.linalg.norm(c[0] - cen) < 6:
                if fit > c[1]["fit"]:
                    c[1] = d
                break
        else:
            cl.append([cen, d])
    rows = []
    for _, d in sorted(cl, key=lambda x: -x[1]["fit"]):
        cen = d["cen"]; v = cen[:2] - TORSO_C
        r = np.linalg.norm(v); ang = np.degrees(np.arctan2(v[1], v[0])) % 360
        dd, _ = dist_tree[a].query((Pfull @ d["T"][:3, :3].T) + d["T"][:3, 3])
        ov = (dd < 1.0).mean()
        rows.append({"T": d["T"].tolist(), "fit": d["fit"], "rmse": d["rmse"],
                     "cen": cen.tolist(), "r": float(r), "ang": float(ang), "ov_distal": float(ov)})
    out[a] = rows
    print(f"\n{a}: distal '{distal[a]}' dir={dist_dir[a]:.0f}deg  ({len(rows)} clusters)")
    for k, rw in enumerate(rows):
        print(f"  #{k} fit={rw['fit']:.3f} rmse={rw['rmse']:.3f} r={rw['r']:4.1f} "
              f"ang={rw['ang']:5.0f} ov_distal={rw['ov_distal']*100:4.0f}% cen={np.round(rw['cen'],1)}")
    sys.stdout.flush()

json.dump(out, open("thigh_candidates.json", "w"))
print(f"\nwrote thigh_candidates.json {time.time()-t0:.1f}s")
