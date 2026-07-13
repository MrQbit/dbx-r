import numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
def L(p): 
    m=trimesh.load(p,process=False); return m.dump(concatenate=True) if isinstance(m,trimesh.Scene) else m
CY,CZ=3.21,1.80
def crag(m,xlo,xhi,label):
    P,fi=trimesh.sample.sample_surface(m,200000,seed=4)
    x=P[:,0]; y=P[:,1]-CY; z=P[:,2]-CZ; r=np.hypot(y,z); th=np.arctan2(z,y)
    sel=(x>=xlo)&(x<xhi)
    x,r,th=x[sel],r[sel],th[sel]
    xb=(x/6).astype(int); tb=((th+np.pi)/(2*np.pi)*72).astype(int); key=xb*100+tb
    stds=[]
    for k in np.unique(key):
        mm=key==k
        if mm.sum()>=6: stds.append(r[mm].std())
    # face normal variation: std of face normal z-component in region
    nrm=m.face_normals; fc=m.triangles_center
    fs=(fc[:,0]>=xlo)&(fc[:,0]<xhi)
    nv=nrm[fs].std(0).mean()
    print(f"{label:22s} local-patch radial std: med={np.median(stds):.2f} p75={np.percentile(stds,75):.2f}  facenormal-std={nv:.3f}")
print("TIBIA region x[180,300] (heavily stretched):")
crag(L(SP+"/leg4_aligned_4B.stl"),180,300,"  ORIGINAL 4B")
crag(L(SP+"/leg4_enclosed_4B.stl"),180,300,"  ENCLOSED 4B")
print("FEMUR region x[70,150]:")
crag(L(SP+"/leg4_aligned_4A.stl"),70,150,"  ORIGINAL 4A")
crag(L(SP+"/leg4_enclosed_4A.stl"),70,150,"  ENCLOSED 4A")
