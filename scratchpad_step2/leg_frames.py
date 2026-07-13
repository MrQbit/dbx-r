import json, numpy as np, trimesh, os
np.set_printoptions(suppress=True)
SD="rocky/cad/stl_derived/trimmed_o3d"
T=json.load(open("/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad/toy_assembled_o3d.json"))

def load(p):
    m=trimesh.load(os.path.join(SD,f"{p}_trimmed.stl"),process=False)
    m.apply_transform(np.array(T[p]))
    return m

torso=load("torso"); torso_c=torso.centroid
def samp(m,n=4000):
    v=m.vertices
    idx=np.random.default_rng(0).choice(len(v),min(n,len(v)),replace=False)
    return v[idx]

CHASSIS=dict(hip=0,p1=60,knee=158,roll=302,tip=328)
DISTAL={1:"1-C",2:"2-B",3:"3-B",4:"4-B",5:"5-B"}
out={}
for leg in range(1,6):
    A=load(f"{leg}-A"); B=load(DISTAL[leg])
    va=samp(A); vb=samp(B); comb=np.vstack([va,vb])
    c=comb.mean(0)
    # principal axis
    U,S,Vt=np.linalg.svd(comb-c)
    u0=Vt[0]
    # orient hip->toe: hip near torso. project A and B centroids
    if np.dot(B.centroid-A.centroid,u0)<0: u0=-u0
    # ensure hip(A) side is negative param
    proj=comb@u0
    # knee = A/B junction: closest points
    from scipy.spatial import cKDTree
    tr=cKDTree(vb); d,i=tr.query(va); k=np.argmin(d)
    knee=(va[k]+vb[i[k]])/2
    # hip/toe endpoints via percentiles along axis
    pa=va@u0; pb=vb@u0
    hip=va[np.argmin(pa)]; toe=vb[np.argmax(pb)]
    # refine: use median of extreme 30 verts
    hip=va[np.argsort(pa)[:30]].mean(0); toe=vb[np.argsort(pb)[-30:]].mean(0)
    L=np.linalg.norm(toe-hip)
    u=(toe-hip)/L
    knee_frac=np.dot(knee-hip,u)/L
    # dorsal ref = statue +Z
    up=np.array([0,0,1.0])
    d0=up-np.dot(up,u)*u
    if np.linalg.norm(d0)<1e-3: d0=np.array([0,1.0,0])-np.dot(np.array([0,1.,0]),u)*u
    d=d0/np.linalg.norm(d0)
    l=np.cross(d,u)
    scale=CHASSIS['tip']/L
    out[leg]=dict(hip=hip,toe=toe,knee=knee,u=u,d=d,l=l,L=float(L),knee_frac=float(knee_frac),scale=float(scale))
    print(f"leg{leg}: L={L:.1f} scale(tip/L)={scale:.2f} knee_frac={knee_frac:.3f} (chassis knee frac={158/328:.3f})")
    print(f"   hip={hip.round(1)} toe={toe.round(1)} u={u.round(2)} dorsal={d.round(2)}")
# torso center for reference
print("torso_c",torso_c.round(1))
json.dump({k:{kk:(vv.tolist() if isinstance(vv,np.ndarray) else vv) for kk,vv in v.items()} for k,v in out.items()},open("scratchpad_step2/leg_frames.json","w"),indent=1)
