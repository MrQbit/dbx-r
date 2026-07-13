import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT="/home/mrqbit/Downloads/dbx-r"
SF=f"{ROOT}/rocky/cad/stl_derived/shells_final"
BP=f"{ROOT}/docs/build_plan"

def add(ax,m,color,alpha,shade=True,n=45000):
    f=m.faces
    if len(f)>n:
        idx=np.random.default_rng(0).choice(len(f),n,replace=False); f=f[idx]
    tris=m.vertices[f]
    pc=Poly3DCollection(tris,alpha=alpha)
    if shade:
        fn=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
        fn/=np.linalg.norm(fn,axis=1,keepdims=True)+1e-9
        L=np.array([0.3,0.4,0.85]); sh=np.abs(fn@L)*0.7+0.3
        base=np.array(matplotlib.colors.to_rgb(color))
        cols=np.clip(base[None]*sh[:,None],0,1)
        pc.set_facecolor(cols)
    else:
        pc.set_facecolor(color)
    pc.set_edgecolor("none"); pc.set_linewidth(0)
    ax.add_collection3d(pc)

chassis=trimesh.util.concatenate([trimesh.load(f"{BP}/leg_chassis_neutral_{g}.stl",process=False)
                                  for g in ("frame","servos","hand")])
# clip chassis to x<345 for leg display
cv=chassis.vertices

def setax(ax,el,az,rng=(-60,345,-90,90,-90,90)):
    ax.set_xlim(rng[0],rng[1]); ax.set_ylim(rng[2],rng[3]); ax.set_zlim(rng[4],rng[5])
    ax.set_box_aspect((rng[1]-rng[0],rng[3]-rng[2],rng[5]-rng[4]))
    ax.view_init(elev=el,azim=az); ax.set_axis_off()

fig=plt.figure(figsize=(20,26))
for i,leg in enumerate(range(1,6)):
    shells=[trimesh.load(f"{SF}/leg{leg}_{s}_hollow.stl",process=False) for s in ("coxa","femur","tibia")]
    solids=[trimesh.load(f"{SF}/leg{leg}_{s}_solid.stl",process=False) for s in ("coxa","femur","tibia")]
    shell=trimesh.util.concatenate(shells); solid=trimesh.util.concatenate(solids)
    # col1: shell over ghost chassis (iso, +Z up)
    ax=fig.add_subplot(5,3,3*i+1,projection='3d')
    add(ax,chassis,"#5b8fb0",0.16,shade=False,n=30000)
    add(ax,shell,"#8a8578",0.9,n=45000)
    setax(ax,18,-70); ax.set_title(f"leg{leg}: hollow shell over ghost chassis",fontsize=11)
    # col2: solid stone dorsal (+Z up, side)
    ax=fig.add_subplot(5,3,3*i+2,projection='3d')
    add(ax,solid,"#9a9284",1.0,n=45000)
    setax(ax,8,-90); ax.set_title(f"leg{leg}: solid stone (dorsal +Z up)",fontsize=11)
    # col3: shell cross cut - show cavity (top view -Z)
    ax=fig.add_subplot(5,3,3*i+3,projection='3d')
    add(ax,chassis,"#c0453b",0.28,shade=False,n=30000)
    add(ax,shell,"#8a8578",0.45,n=45000)
    setax(ax,80,-90); ax.set_title(f"leg{leg}: enclosure (chassis red inside shell)",fontsize=11)
    print("leg",leg,"rendered",flush=True)

fig.suptitle("PROJECT DUET — STEP 2 shell process: 5 legs, o3d-oriented craggy shells over the D-043 chassis",fontsize=15,y=0.995)
plt.tight_layout(rect=[0,0,1,0.99])
plt.savefig(f"{BP}/shells_final.png",dpi=95)
print("saved",f"{BP}/shells_final.png")
