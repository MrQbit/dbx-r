"""RANSAC joint primitives from the RAW pieces (features external before assembly).
Per piece we isolate the mating end-cap(s) along the PCA principal axis and fit
Sphere (ball peg) and Cylinder (socket bore); keep the primitive the data supports
(sensible radius 1-6mm, high inliers). Centers reported in LOCAL and STATUE frame."""
import numpy as np, json
from pyransac3d import Sphere, Cylinder
from reglib import *

T = {n: np.array(v) for n, v in json.load(open(
    "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/"
    "scratchpad/toy_assembled_o3d.json")).items()}

def to_statue(n, p):
    return (np.atleast_2d(p) @ T[n][:3, :3].T) + T[n][:3, 3]

def endcaps(pts, frac=0.22):
    c = pts.mean(0); X = pts - c
    axis = np.linalg.svd(X, full_matrices=False)[2][0]
    t = X @ axis
    lo, hi = t.min(), t.max(); L = hi - lo
    prox = pts[t < lo + frac * L]   # end nearer axis-min
    dist = pts[t > hi - frac * L]
    return prox, dist, axis

def best_sphere(pts):
    if len(pts) < 40: return None
    c, r, inl = Sphere().fit(pts.astype(float), thresh=0.3, maxIteration=3000)
    return {"center": c, "r": float(r), "inl": len(inl), "n": len(pts)}

def best_cyl(pts):
    if len(pts) < 40: return None
    c, ax, r, inl = Cylinder().fit(pts.astype(float), thresh=0.3, maxIteration=3000)
    return {"center": c, "axis": ax, "r": float(r), "inl": len(inl), "n": len(pts)}

# which end of each piece holds what (per docref). prox=nearer torso for thighs.
plan = {
    "1-A": [("prox", "socket", "hip"), ("dist", "socket", "wrist")],  # leg1: hand has peg
    "2-A": [("prox", "socket", "hip"), ("dist", "ball", "knee")],
    "3-A": [("prox", "socket", "hip"), ("dist", "ball", "knee")],
    "4-A": [("prox", "socket", "hip"), ("dist", "ball", "knee")],
    "5-A": [("prox", "socket", "hip"), ("dist", "ball", "knee")],
    "1-C": [("prox", "peg", "wrist")],
    "2-B": [("prox", "socket", "knee"), ("dist", "socket", "knee")],
    "3-B": [("prox", "socket", "knee"), ("dist", "socket", "knee")],
    "4-B": [("prox", "socket", "knee"), ("dist", "socket", "knee")],
    "5-B": [("prox", "socket", "knee"), ("dist", "socket", "knee")],
}
res = {}
print(f"{'piece/end':14s} {'kind':7s} {'sphere r/inl':16s} {'cyl r/inl':16s}  pick")
for n, ends in plan.items():
    P = trimesh.sample.sample_surface(load_trimesh(n), 120000, seed=5)[0]
    prox, dist, axis = endcaps(P)
    caps = {"prox": prox, "dist": dist}
    for endname, kind, lab in ends:
        pts = caps[endname]
        sph = best_sphere(pts); cyl = best_cyl(pts)
        # choose by expected kind + sensible radius
        pick = None
        if kind in ("ball", "peg") and sph and 1.0 < sph["r"] < 7.0:
            pick = ("sphere", sph)
        elif kind == "socket" and cyl and 1.0 < cyl["r"] < 7.0:
            pick = ("cylinder", cyl)
        elif cyl and 1.0 < cyl["r"] < 7.0:
            pick = ("cylinder", cyl)
        elif sph and 1.0 < sph["r"] < 7.0:
            pick = ("sphere", sph)
        entry = {"kind": kind, "label": lab, "end": endname}
        if pick:
            typ, d = pick
            cen_local = d["center"]; cen_st = to_statue(n, cen_local)[0]
            entry.update({"prim": typ, "r": round(d["r"], 2), "inl": d["inl"], "n": d["n"],
                          "center_local": np.round(cen_local, 2).tolist(),
                          "center_statue": np.round(cen_st, 2).tolist()})
            if typ == "cylinder":
                entry["axis_statue"] = np.round(to_statue(n, cen_local + d["axis"])[0] - cen_st, 3).tolist()
        res[f"{n}:{endname}:{lab}"] = entry
        sr = f"r={sph['r']:.2f}/{sph['inl']}" if sph else "-"
        cr = f"r={cyl['r']:.2f}/{cyl['inl']}" if cyl else "-"
        pk = entry.get("prim", "NONE")
        print(f"{n+':'+endname:14s} {kind:7s} {sr:16s} {cr:16s}  {pk} r={entry.get('r','-')}")

json.dump({k: {kk: vv for kk, vv in v.items()} for k, v in res.items()},
          open("joints_raw.json", "w"), indent=1, default=str)
print("\nwrote joints_raw.json")
