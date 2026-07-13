"""Silhouette of aligned 1-C hand blade viewed along the palm normal (Y)."""
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
C=trimesh.load(SP+"/leg1_aligned_1C.stl",process=False)
P,_=trimesh.sample.sample_surface(C,300000,seed=1)
fig,axs=plt.subplots(1,3,figsize=(22,8))
sel=P[P[:,0]>280]
sc=axs[0].scatter(sel[:,0],sel[:,2],s=.4,c=sel[:,1],cmap="coolwarm")
axs[0].set_title("XZ (view along -Y palm normal), x>280, colour=y"); plt.colorbar(sc,ax=axs[0])
sel2=P[P[:,0]>295]
sc2=axs[1].scatter(sel2[:,1],sel2[:,2],s=.4,c=sel2[:,0],cmap="viridis")
axs[1].set_title("YZ end-on x>295, colour=x"); plt.colorbar(sc2,ax=axs[1])
# thickness profile of the blade region: for each (x,z) cell, y-extent
sel3=P[(P[:,0]>300)]
from collections import defaultdict
axs[2].scatter(sel3[:,0],sel3[:,2],s=.4,c="lightgray")
# find distal edge per z: max x
zb=np.linspace(-20,20,41)
for lo,hi in zip(zb[:-1],zb[1:]):
    s=sel3[(sel3[:,2]>=lo)&(sel3[:,2]<hi)]
    if len(s)>5:
        axs[2].plot(s[:,0].max(),(lo+hi)/2,"r.")
axs[2].set_title("distal edge per z (red)")
for a in axs: a.set_aspect("equal")
plt.tight_layout(); plt.savefig(SP+"/_leg1_blade.png",dpi=75)
print("saved")
# numeric: distal edge x as function of z
print("z-bin  max_x  (blade distal silhouette)")
for lo,hi in zip(zb[:-1],zb[1:]):
    s=sel3[(sel3[:,2]>=lo)&(sel3[:,2]<hi)]
    if len(s)>5: print(f"z[{lo:6.1f},{hi:6.1f}]  max_x={s[:,0].max():6.1f}  ymid={np.median(s[:,1]):5.1f} thick_y={s[:,1].max()-s[:,1].min():5.1f}")
