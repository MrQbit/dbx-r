import json, numpy as np, trimesh, os

SD = "rocky/cad/stl_derived/trimmed_o3d"
T = json.load(open("/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad/toy_assembled_o3d.json"))

pieces = ["torso","1-A","1-C","2-A","2-B","3-A","3-B","4-A","4-B","5-A","5-B"]

# verify transforms orthonormal / scale
for k,M in T.items():
    M=np.array(M); R=M[:3,:3]
    s=np.linalg.norm(R,axis=0)
    print(f"{k:6s} colnorms={s.round(4)} det={np.linalg.det(R):.4f}")

print("\n=== per-piece raw + statue ===")
info={}
for p in pieces:
    m=trimesh.load(os.path.join(SD,f"{p}_trimmed.stl"),process=False)
    ext=m.extents
    M=np.array(T[p])
    ms=m.copy(); ms.apply_transform(M)
    c=ms.centroid
    info[p]=dict(raw_ext=ext, raw_centroid=m.centroid, stat_centroid=c, stat_bounds=ms.bounds, mesh=ms)
    print(f"{p:5s} raw_ext={ext.round(1)} raw_cen={m.centroid.round(1)} stat_cen={c.round(1)} verts={len(m.vertices)} wt={m.is_watertight}")
