"""Probe aligned leg1 pieces vs chassis: projections + per-x slice stats for 1-C."""
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
BP="/home/mrqbit/Downloads/dbx-r/docs/build_plan"
def L(p):
    m=trimesh.load(p,process=False)
    if isinstance(m,trimesh.Scene): m=m.dump(concatenate=True)
    return m
A=L(SP+"/leg1_aligned_1A.stl"); C=L(SP+"/leg1_aligned_1C.stl")
frame=L(BP+"/leg_chassis_neutral_frame.stl"); servo=L(BP+"/leg_chassis_neutral_servos.stl")
hand=L(BP+"/leg_chassis_neutral_hand.stl")
PA,_=trimesh.sample.sample_surface(A,60000,seed=1)
PC,_=trimesh.sample.sample_surface(C,60000,seed=1)
PF,_=trimesh.sample.sample_surface(frame,40000,seed=1)
PS,_=trimesh.sample.sample_surface(servo,40000,seed=1)
PH,_=trimesh.sample.sample_surface(hand,40000,seed=1)
fig,axs=plt.subplots(2,2,figsize=(20,12))
for ax,(i,j,lab) in zip(axs.flat,[(0,1,"XY (top)"),(0,2,"XZ (side)")]+[(1,2,"YZ tip x>340"),(1,2,"YZ palm 300<x<340")]):
    if lab.startswith("YZ tip"):
        sel=lambda P:P[P[:,0]>340]
    elif lab.startswith("YZ palm"):
        sel=lambda P:P[(P[:,0]>300)&(P[:,0]<340)]
    else:
        sel=lambda P:P
    ax.scatter(*sel(PA)[:, [i,j]].T,s=.5,c="silver",label="1-A")
    ax.scatter(*sel(PC)[:, [i,j]].T,s=.5,c="tan",label="1-C")
    ax.scatter(*sel(PF)[:, [i,j]].T,s=.5,c="royalblue",label="frame")
    ax.scatter(*sel(PS)[:, [i,j]].T,s=.5,c="orangered",label="servos")
    ax.scatter(*sel(PH)[:, [i,j]].T,s=.5,c="green",label="hand")
    ax.set_title(lab); ax.set_aspect("equal"); ax.legend(markerscale=20)
plt.tight_layout(); plt.savefig(SP+"/_leg1_probe.png",dpi=70)
print("saved _leg1_probe.png")
# per-x slice stats of 1-C
print("\n1-C slices: x  ny_lo ny_hi  nz_lo nz_hi  thickness(minor)  n")
for x0 in range(150,345,10):
    s=PC[(PC[:,0]>=x0)&(PC[:,0]<x0+10)]
    if len(s)<50: continue
    # minor thickness via PCA of yz
    yz=s[:,1:]-s[:,1:].mean(0)
    w=np.linalg.eigvalsh(yz.T@yz/len(yz))
    print(f"x{x0:3d}-{x0+10:3d}: y[{s[:,1].min():6.1f},{s[:,1].max():6.1f}] z[{s[:,2].min():6.1f},{s[:,2].max():6.1f}] minor_sd={np.sqrt(w[0]):5.1f} major_sd={np.sqrt(w[1]):5.1f} n={len(s)}")
# chassis hand extent
print("\nchassis hand bounds:",np.round(hand.bounds,1).tolist())
print("chassis fingers (hand x>340) yz extent:", )
hh=PH[PH[:,0]>340]
print(f"  x[{hh[:,0].min():.1f},{hh[:,0].max():.1f}] y[{hh[:,1].min():.1f},{hh[:,1].max():.1f}] z[{hh[:,2].min():.1f},{hh[:,2].max():.1f}]")
