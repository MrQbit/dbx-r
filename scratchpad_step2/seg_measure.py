import json, numpy as np, trimesh, os
from scipy.spatial import cKDTree
np.set_printoptions(suppress=True)
SD="rocky/cad/stl_derived/trimmed_o3d"
T=json.load(open("/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad/toy_assembled_o3d.json"))
def load(p):
    m=trimesh.load(os.path.join(SD,f"{p}_trimmed.stl"),process=False); m.apply_transform(np.array(T[p])); return m
def samp(m,n=6000):
    v=m.vertices; idx=np.random.default_rng(0).choice(len(v),min(n,len(v)),replace=False); return v[idx]
DIST={1:"1-C",2:"2-B",3:"3-B",4:"4-B",5:"5-B"}
def axis_len(v):
    c=v.mean(0); U,S,Vt=np.linalg.svd(v-c); u=Vt[0]; p=v@u
    lo=v[np.argsort(p)[:40]].mean(0); hi=v[np.argsort(p)[-40:]].mean(0)
    return lo,hi,np.linalg.norm(hi-lo),u
for leg in range(1,6):
    A=load(f"{leg}-A"); B=load(DIST[leg])
    va=samp(A); vb=samp(B)
    # knee junction
    tr=cKDTree(vb); d,i=tr.query(va); k=np.argmin(d); knee=(va[k]+vb[i[k]])/2
    aLo,aHi,aL,aU=axis_len(va); bLo,bHi,bL,bU=axis_len(vb)
    # orient A: hip=far from knee, knee end near knee
    if np.linalg.norm(aLo-knee)<np.linalg.norm(aHi-knee): aHip,aKnee=aHi,aLo
    else: aHip,aKnee=aLo,aHi
    if np.linalg.norm(bLo-knee)<np.linalg.norm(bHi-knee): bToe,bKnee=bHi,bLo
    else: bToe,bKnee=bLo,bHi
    Aaxis=(aKnee-aHip); Aaxis/=np.linalg.norm(Aaxis)
    Baxis=(bToe-bKnee); Baxis/=np.linalg.norm(Baxis)
    bend=np.degrees(np.arccos(np.clip(np.dot(Aaxis,Baxis),-1,1)))
    print(f"leg{leg}: A_len(hip->knee)={np.linalg.norm(aKnee-aHip):.1f} scaleA={158/np.linalg.norm(aKnee-aHip):.2f} | B_len(knee->toe)={np.linalg.norm(bToe-bKnee):.1f} scaleB={170/np.linalg.norm(bToe-bKnee):.2f} | knee_bend={bend:.0f}deg")
