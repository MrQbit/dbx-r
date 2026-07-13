"""Measure leg4 4-B cleft groove in the Rx(-90) rotated frame ((y,z)->(z,-y)):
after rotation the cleft should mirror leg2 (prongs +/-z', opening +y').
Outputs GROOVE_Y', GROOVE_Z' (split plane) + a rotated-region STL for visual check."""
import numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
m=trimesh.load(SP+"/leg4_aligned_4B.stl",process=False)
fm=m.vertices[m.faces].mean(axis=1)
region=trimesh.Trimesh(m.vertices,m.faces[fm[:,0]>279],process=True)
V=region.vertices.copy()
Vr=np.c_[V[:,0], V[:,2], -V[:,1]]           # Rx(-90): y'=z, z'=-y
reg_r=trimesh.Trimesh(Vr,region.faces,process=False)
reg_r.export(SP+"/_leg4_footregion_rot.stl")
P,_=trimesh.sample.sample_surface(reg_r,300000,seed=5)
tip=float(Vr[:,0].max())
print("tip x=%.1f  rotated-region bounds"%tip, np.round(reg_r.bounds,1).tolist())
B=P[P[:,0]>tip-8]
D=P[(P[:,0]>tip-25)&(P[:,0]<tip-8)]
print("distal section centroid (y',z') =", np.round(D[:,1:].mean(0),2),
      " tipband centroid =", np.round(B[:,1:].mean(0),2))
# groove plane scan: prongs split +/-z'; groove = z0 with fewest pts, on the +y' (open) side
open_side=B[B[:,1]>B[:,1].mean()]
print("\n z0 :  count(|z'-z0|<0.9, +y' open side)   [tipband n=%d openside n=%d]"%(len(B),len(open_side)))
zs=np.arange(-14,14.01,0.5); cnt=[]
for z0 in zs:
    c=int(np.sum(np.abs(open_side[:,2]-z0)<0.9)); cnt.append(c)
    print(f"  {z0:6.1f} : {'#'*int(c/12)} {c}")
cnt=np.array(cnt)
# groove = min in the interior span between the two prong density peaks
i_pk=cnt.argmax()
# find the two dominant lobes: smooth and find min between outermost peaks
sm=np.convolve(cnt,np.ones(3)/3,mode='same')
pk=[i for i in range(1,len(zs)-1) if sm[i]>=sm[i-1] and sm[i]>=sm[i+1] and sm[i]>0.35*sm.max()]
print("peaks at z0:",[round(zs[i],1) for i in pk])
if len(pk)>=2:
    lo,hi=pk[0],pk[-1]
    imin=lo+int(np.argmin(sm[lo:hi+1]))
    print("GROOVE split plane z' = %.1f  (valley between prong peaks %.1f and %.1f)"
          %(zs[imin],zs[lo],zs[hi]))
