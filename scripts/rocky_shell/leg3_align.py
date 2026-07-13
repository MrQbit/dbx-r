"""LEG3 ALIGN — recipe step 1 (mirrors leg2's build_align.py exactly, pieces 3-A/3-B).
Assembled o3d leg (RAW pieces WITH pegs), knee EXTENDED straight, aligned to the
D-043 chassis skeleton: HIP->0, KNEE->158, TOE->328 along +X. Per-piece similarity
(shortest-arc long-axis->+X preserves each piece's o3d roll), uniform scale, translate.
"""
import json, numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
AF="/home/mrqbit/Downloads/dbx-r/reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS"
T={n:np.array(v) for n,v in json.load(open(SP+"/toy_assembled_o3d.json")).items()}
def load(n): return trimesh.load(f"{AF}/{n}.stl", process=False)
def to_st_mesh(n):
    m=load(n).copy(); R=T[n][:3,:3]; t=T[n][:3,3]
    m.vertices=(m.vertices@R.T)+t; return m

# ---- robust joint centers from assembled (o3d) point clouds ----
def axis_and_caps(pts, frac=0.12):
    c=pts.mean(0); u=np.linalg.svd(pts-c,full_matrices=False)[2][0]
    s=(pts-c)@u
    lo=pts[s< s.min()+frac*(s.max()-s.min())].mean(0)
    hi=pts[s> s.max()-frac*(s.max()-s.min())].mean(0)
    return lo,hi,u

mA=to_st_mesh("3-A"); mB=to_st_mesh("3-B")
PA,_=trimesh.sample.sample_surface(mA,80000,seed=3)
PB,_=trimesh.sample.sample_surface(mB,80000,seed=3)
a_lo,a_hi,ua=axis_and_caps(PA)
b_lo,b_hi,ub=axis_and_caps(PB)
# assign by proximity: HIP end of 3-A is the one FAR from 3-B; KNEE end near 3-B
d_lo=min(np.linalg.norm(a_lo-b_lo),np.linalg.norm(a_lo-b_hi))
d_hi=min(np.linalg.norm(a_hi-b_lo),np.linalg.norm(a_hi-b_hi))
if d_lo<d_hi: kneeA,hip = a_lo,a_hi
else:         kneeA,hip = a_hi,a_lo
# 3-B: knee end near kneeA; toe end far
if np.linalg.norm(b_lo-kneeA)<np.linalg.norm(b_hi-kneeA): kneeB,toe=b_lo,b_hi
else: kneeB,toe=b_hi,b_lo
print("HIP  =",np.round(hip,2))
print("kneeA=",np.round(kneeA,2),"  kneeB=",np.round(kneeB,2),"  gap=",round(float(np.linalg.norm(kneeA-kneeB)),2))
print("TOE  =",np.round(toe,2))

# ---- shortest-arc rotation mapping vector a_hat -> +X ----
def short_arc(a):
    a=a/np.linalg.norm(a); x=np.array([1.,0,0])
    v=np.cross(a,x); c=float(a@x); s=np.linalg.norm(v)
    if s<1e-9:
        return np.eye(3) if c>0 else np.diag([ -1,-1,1.])
    vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+vx+vx@vx*((1-c)/(s*s))

# 3-A: hip->0 , kneeA->158
axA=kneeA-hip; LA=float(np.linalg.norm(axA)); sA=158.0/LA; RA=short_arc(axA)
tA=np.array([0.,0,0])-sA*(RA@hip)
# 3-B: kneeB->158 , toe->328
axB=toe-kneeB; LB=float(np.linalg.norm(axB)); sB=170.0/LB; RB=short_arc(axB)
tB=np.array([158.,0,0])-sB*(RB@kneeB)

def apply(R,s,t,P): return (np.atleast_2d(P)@ (s*R).T)+t
# verify
print("\n-- chassis-frame mapped joints (residual to station) --")
for nm,P,tgt in [("HIP",apply(RA,sA,tA,hip),[0,0,0]),
                 ("KNEE(3A)",apply(RA,sA,tA,kneeA),[158,0,0]),
                 ("KNEE(3B)",apply(RB,sB,tB,kneeB),[158,0,0]),
                 ("TOE",apply(RB,sB,tB,toe),[328,0,0])]:
    P=P[0]; print(f"{nm:9s} -> {np.round(P,2)}  target {tgt}  resid {np.round(P-np.array(tgt),3)}")
print(f"\nscale 3-A sA={sA:.3f}  (hip->knee {LA:.2f} -> 158)")
print(f"scale 3-B sB={sB:.3f}  (knee->toe {LB:.2f} -> 170)")
# knee bend / extension
v1=hip-kneeA; v2=toe-kneeB
ang=np.degrees(np.arccos(np.clip((v1@v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)),-1,1)))
print(f"o3d interior knee angle (hip-knee-toe) = {ang:.1f} deg ; extended by {180-ang:.1f} deg to straight")

# roll diagnostic: where does o3d +Z(dorsal-ish) go for each piece after rotation
zA=RA@np.array([0,0,1.]); zB=RB@np.array([0,0,1.])
def roll_of(z):
    zp=z-z[0]*np.array([1,0,0]); return np.degrees(np.arctan2(zp[2],zp[1]))
print(f"roll-frame (atan2 of mapped o3d-Z about X): 3-A={roll_of(zA):.1f} deg, 3-B={roll_of(zB):.1f} deg, A-B offset={roll_of(zA)-roll_of(zB):.1f} deg")

# ---- export aligned meshes (chassis frame) ----
mA2=mA.copy(); mA2.vertices=apply(RA,sA,tA,mA.vertices); mA2.export(SP+"/leg3_aligned_3A.stl")
mB2=mB.copy(); mB2.vertices=apply(RB,sB,tB,mB.vertices); mB2.export(SP+"/leg3_aligned_3B.stl")
print("\nexported leg3_aligned_3A.stl / _3B.stl  bboxA",np.round(mA2.bounds,1).tolist(),"bboxB",np.round(mB2.bounds,1).tolist())

def M(R,s,t):
    m=np.eye(4); m[:3,:3]=s*R; m[:3,3]=t; return m.tolist()
out={
 "description":"LEG3 align-only: assembled o3d leg (3-A+3-B, pegs kept), extended+aligned to D-043 chassis skeleton (HIP=0,KNEE=158,TOE=328 along +X).",
 "method":"per-piece similarity: shortest-arc rotate long axis->+X (preserves o3d roll), uniform scale to span, translate to station.",
 "frame":"chassis leg frame (X=reach, Z=up, Y=pitch axis); o3d source = toy statue frame.",
 "chassis_stations_mm":{"HIP":0,"KNEE":158,"TOE":328},
 "o3d_joints_statue_mm":{"HIP":hip.tolist(),"KNEE_3A":kneeA.tolist(),"KNEE_3B":kneeB.tolist(),"TOE":toe.tolist(),
                         "knee_ball_socket_gap_mm":float(np.linalg.norm(kneeA-kneeB))},
 "scale":{"3-A":sA,"3-B":sB},
 "source_span_mm":{"3-A_hip_knee":LA,"3-B_knee_toe":LB},
 "knee_extension_deg":float(180-ang),
 "o3d_interior_knee_angle_deg":float(ang),
 "transforms_o3dstatue_to_chassis_4x4":{"3-A":M(RA,sA,tA),"3-B":M(RB,sB,tB)},
 "note":"NOTHING trimmed/hollowed/anchored. Pegs kept. Align+show only, for operator confirmation."
}
json.dump(out,open(SP+"/leg3_aligned.json","w"),indent=1)
np.save(SP+"/_leg3_final_joints.npy",{"hip":hip,"kneeA":kneeA,"kneeB":kneeB,"toe":toe,
      "RA":RA,"sA":sA,"tA":tA,"RB":RB,"sB":sB,"tB":tB},allow_pickle=True)
print("wrote leg3_aligned.json")
