import trimesh, numpy as np, json, os
from scipy.spatial import cKDTree
SRC="/home/mrqbit/Downloads/dbx-r/reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS"
D=os.path.dirname(__file__)
INV=json.load(open("/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad/dejoint_work/joint_inventory.json"))
REG=json.load(open(D+"/reg3.json"))
PROT=json.load(open(D+"/protrude.json"))
NAMES=['torso','1-A','1-C','2-A','2-B','3-A','3-B','4-A','4-B','5-A','5-B']
def load(n):
    m=trimesh.load(f"{SRC}/{n}.stl",process=True)
    if isinstance(m,trimesh.Scene): m=m.dump(concatenate=True)
    return m
def roughness(m):
    fn=m.vertex_normals; E=m.edges_unique
    ang=np.arccos(np.clip((fn[E[:,0]]*fn[E[:,1]]).sum(1),-1,1))
    N=len(m.vertices); s=np.zeros(N); c=np.zeros(N)
    np.add.at(s,E[:,0],ang); np.add.at(s,E[:,1],ang); np.add.at(c,E[:,0],1); np.add.at(c,E[:,1],1); c[c==0]=1
    return s/c
def seeds_for(n):
    S=[]
    T=np.array(REG[n]['T']); R=T[:3,:3]; tt=T[:3,3]
    for e in INV:
        if e['piece']!=n: continue
        J=R@np.array(e['J'])+tt; u=R@np.array(e['u']); u/=np.linalg.norm(u)
        S.append((J,u,e['end']))
    for b in PROT.get(n,[]):
        S.append((np.array(b['tip']),np.array(b['axis']),'prot'))
    return S
def measure(V,rough,sm,p,u):
    u=u/np.linalg.norm(u)
    # tip = farthest smooth vert outward within 11mm of p
    tree=cKDTree(V[sm])
    idx=tree.query_ball_point(p,11)
    if len(idx)<20: return None
    Ps=V[sm][idx]
    T=Ps[np.argmax((Ps-p)@u)]
    # refine axis via smooth verts near tip
    rel=V-T; s=-(rel@u); perp=np.linalg.norm(rel-np.outer(rel@u,u),axis=1)
    seln=(s>=-1)&(s<9)&(perp<6)&sm
    if seln.sum()>25:
        P=V[seln]; c=P.mean(0); uu,ss,vt=np.linalg.svd(P-c,full_matrices=False); a=vt[0]
        if a@u<0: a=-a
        u=a/np.linalg.norm(a)
        rel=V-T; s=-(rel@u); perp=np.linalg.norm(rel-np.outer(rel@u,u),axis=1)
    # radial profile with rcap=6.5 (isolate stud)
    rad=[]; rgh=[]
    for i in range(16):
        selb=(s>=i)&(s<i+1)&(perp<6.5)
        if selb.sum()>=5: rad.append(float(np.percentile(perp[selb],75))); rgh.append(float(np.median(rough[selb])))
        else: rad.append(np.nan); rgh.append(np.nan)
    rad=np.array(rad); rgh=np.array(rgh)
    if np.all(np.isnan(rad[:3])): return None
    stud_r=np.nanmedian(rad[0:3])
    if not (1.2<stud_r<7.5): return None
    base=None
    for i in range(2,16):
        if not np.isnan(rad[i]) and rad[i]>stud_r+2.5: base=i; break
    if base is None or base<3 or base>14: return None
    studrough=np.nanmedian(rgh[:base])
    # protrusion check: tip must be outboard of body ring
    return dict(tip=[round(float(x),3) for x in T],axis=[round(float(x),4) for x in u],
                stud_r=round(float(stud_r),2),base_depth=int(base),stud_rough=round(float(studrough),3))
out={}
for n in NAMES:
    m=load(n); V=m.vertices; rough=roughness(m); sm=rough<0.16
    got=[]
    for p,u,lbl in seeds_for(n):
        r=measure(V,rough,sm,np.array(p,float),np.array(u,float))
        if r is None: continue
        if any(np.linalg.norm(np.array(r['tip'])-np.array(q['tip']))<6 for q in got): continue
        r['seed']=lbl; got.append(r)
    out[n]=got
    print(f"{n}: {len(got)} studs -> "+", ".join(f"{q['seed']}(r{q['stud_r']},b{q['base_depth']},rg{q['stud_rough']})" for q in got))
json.dump(out,open(D+"/pegs_to_cut_raw.json","w"),indent=1)
print("total",sum(len(v) for v in out.values()))
