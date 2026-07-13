"""Probe the distal foot-tip cleft of an aligned N-B piece: prong split axis,
groove center, tip station. Calibrated against leg2 (known: groove ~(0.6,2.5),
prongs split +/-z, SRC_TIP=341)."""
import numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"

def probe(path, tag):
    m=trimesh.load(path, process=False)
    if isinstance(m,trimesh.Scene): m=m.dump(concatenate=True)
    tip=float(m.bounds[1][0])
    P,_=trimesh.sample.sample_surface(m,300000,seed=5)
    print(f"\n== {tag}  tip_x={tip:.1f} ==")
    # tip band: last 8mm
    B=P[P[:,0]>tip-8.0][:,1:]
    # 2-means in yz
    c=np.array([B.mean(0)+[0,3],B.mean(0)-[0,3]])
    for _ in range(30):
        d=((B[:,None,:]-c[None])**2).sum(2); lab=d.argmin(1)
        c=np.array([B[lab==k].mean(0) for k in (0,1)])
    sep=c[0]-c[1]; L=np.linalg.norm(sep)
    ang=np.degrees(np.arctan2(sep[0],sep[1]))  # angle of split axis from +z (in yz: sep=[dy,dz])
    mid=(c[0]+c[1])/2
    print(f" tipband n={len(B)} prong centroids yz {np.round(c[0],2)} | {np.round(c[1],2)}  sep={L:.1f}mm")
    print(f" split-axis angle from z-axis = {ang:.1f} deg   groove midpoint yz = {np.round(mid,2)}")
    # groove trace: for x slices over last 25mm, the radius minimum between prongs
    # opening direction: centroid of the tip band relative to the whole distal section centroid
    D=P[(P[:,0]>tip-25)&(P[:,0]<tip-8)][:,1:]
    print(f" distal section centroid yz={np.round(D.mean(0),2)}  tipband centroid yz={np.round(B.mean(0),2)}")
    # per-slice gap check: fraction of tipband points within 1.5mm of the split plane
    n=sep/L
    s=(B-mid)@n
    frac=np.mean(np.abs(s)<1.0)
    print(f" cleft void check: {frac*100:.1f}% of tipband pts within 1mm of split plane (low = clean cleft)")
    return {"tip":tip,"c":c,"mid":mid,"ang":ang}

r2=probe(SP+"/leg2_aligned_2B.stl","LEG2 2-B (calibration)")
r4=probe(SP+"/leg4_aligned_4B.stl","LEG4 4-B")
