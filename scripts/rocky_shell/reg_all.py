"""Register all 11 pieces onto the statue. FPFH global (Open3D) + manual ICP.
Keep, per piece, several DISTINCT candidate poses (clustered by translation) so a
later assignment step can disambiguate the 5 near-identical legs.
Idempotent: writes scratchpad/o3d/reg_candidates.json."""
import numpy as np, open3d as o3d, json, time, sys
from reglib import *

VOX = 1.5
N_SEED = 14
t0 = time.time()

st_tm = load_trimesh("statue")
st_pcd = tm_to_pcd(st_tm, 220000, seed=1)
st_d, st_f = preprocess(st_pcd, VOX)
tgt = np.asarray(st_d.points); tgt_n = np.asarray(st_d.normals)
print(f"statue down={len(tgt)} {time.time()-t0:.1f}s"); sys.stdout.flush()

results = {}
for name in PIECES:
    pc = tm_to_pcd(load_trimesh(name), 70000, seed=1)
    sd, sf = preprocess(pc, VOX)
    src = np.asarray(sd.points)
    cands = []  # list of dict(T, fit, rmse, gfit)
    for seed in range(N_SEED):
        g = global_ransac(sd, sf, st_d, st_f, VOX, seed=seed)
        T, fit, rmse = icp_manual(src, tgt, tgt_n, g.transformation, VOX, p2plane=True)
        cands.append({"T": T, "fit": fit, "rmse": rmse, "gfit": g.fitness})
    # cluster candidates by translation (distinct docking sites), keep best per cluster
    clusters = []  # (center_transl, best_cand)
    for c in sorted(cands, key=lambda x: (-x["fit"], x["rmse"])):
        tr = c["T"][:3, 3]
        placed = False
        for cl in clusters:
            if np.linalg.norm(tr - cl[0]) < 6.0:
                placed = True; break
        if not placed:
            clusters.append((tr, c))
    clusters = clusters[:4]
    results[name] = [{"T": cl[1]["T"].tolist(), "fit": cl[1]["fit"],
                      "rmse": cl[1]["rmse"], "gfit": cl[1]["gfit"],
                      "transl": cl[1]["T"][:3, 3].tolist()} for cl in clusters]
    b = results[name][0]
    print(f"{name:6s} best fit={b['fit']:.3f} rmse={b['rmse']:.3f} "
          f"transl={np.round(b['transl'],1)} ncluster={len(clusters)} {time.time()-t0:.1f}s")
    sys.stdout.flush()

with open("reg_candidates.json", "w") as f:
    json.dump(results, f)
print("wrote reg_candidates.json")
