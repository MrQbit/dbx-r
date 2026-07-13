"""LEG5 STEP 1 — ALIGN (mirror of leg2 build_align.py, operator-approved recipe).
Assembled o3d leg (5-A + 5-B RAW with pegs), extended straight, mapped to
D-043 chassis stations HIP=0 / KNEE=158 / TOE=328 by per-piece similarity
(shortest-arc long-axis->+X preserves o3d roll). NOTE: 5-B is the LONG BLADE
foot — its knee->toe span sets a leg5-specific scale (reported vs leg2)."""
import json, numpy as np, trimesh
from scipy.spatial import cKDTree
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

mA=to_st_mesh("5-A"); mB=to_st_mesh("5-B")
PA,_=trimesh.sample.sample_surface(mA,80000,seed=3)
PB,_=trimesh.sample.sample_surface(mB,80000,seed=3)
a_lo,a_hi,ua=axis_and_caps(PA)
b_lo,b_hi,ub=axis_and_caps(PB)
# assign by proximity: HIP end of 5-A is the one FAR from 5-B; KNEE end near 5-B
d_lo=min(np.linalg.norm(a_lo-b_lo),np.linalg.norm(a_lo-b_hi))
d_hi=min(np.linalg.norm(a_hi-b_lo),np.linalg.norm(a_hi-b_hi))
if d_lo<d_hi: kneeA,hip = a_lo,a_hi
else:         kneeA,hip = a_hi,a_lo
# 5-B: knee end near kneeA; toe end far
if np.linalg.norm(b_lo-kneeA)<np.linalg.norm(b_hi-kneeA): kneeB,toe=b_lo,b_hi
else: kneeB,toe=b_hi,b_lo
print("HIP  =",np.round(hip,2))
print("kneeA=",np.round(kneeA,2),"  kneeB=",np.round(kneeB,2),"  gap=",round(float(np.linalg.norm(kneeA-kneeB)),2))
print("TOE  =",np.round(toe,2))

# cross-checks (leg2 an2-style): knee junction overlap + classified joints
tb=cKDTree(PB); dA,_=tb.query(PA)
junc=PA[dA<3.0]
if len(junc): print("knee-junction overlap pts=%d  mean=%s  min gap=%.2f"%(
    len(junc),np.round(junc.mean(0),2),float(dA.min())))
jc=json.load(open(SP+"/o3d/joints_classified.json"))
def to_st(n,P): return (np.atleast_2d(P)@T[n][:3,:3].T)+T[n][:3,3]
hipJ=to_st("5-A",np.array(jc["5-A"][0]["J"]))[0]
kneeJA=to_st("5-A",np.array(jc["5-A"][1]["J"]))[0]
kneeJB=to_st("5-B",np.array(jc["5-B"][0]["J"]))[0]
print("classified: HIP(5A prox)=%s  knee(5A dist)=%s  knee(5B prox)=%s"%(
    np.round(hipJ,2),np.round(kneeJA,2),np.round(kneeJB,2)))
print("cap-vs-classified dist: HIP %.2f  kneeA %.2f  kneeB %.2f"%(
    np.linalg.norm(hip-hipJ),np.linalg.norm(kneeA-kneeJA),np.linalg.norm(kneeB-kneeJB)))

# ---- shortest-arc rotation mapping vector a_hat -> +X ----
def short_arc(a):
    a=a/np.linalg.norm(a); x=np.array([1.,0,0])
    v=np.cross(a,x); c=float(a@x); s=np.linalg.norm(v)
    if s<1e-9:
        return np.eye(3) if c>0 else np.diag([ -1,-1,1.])
    vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+vx+vx@vx*((1-c)/(s*s))

# 5-A: hip->0 , kneeA->158
axA=kneeA-hip; LA=float(np.linalg.norm(axA)); sA=158.0/LA; RA=short_arc(axA)
tA=np.array([0.,0,0])-sA*(RA@hip)
# 5-B: kneeB->158 , toe->328
axB=toe-kneeB; LB=float(np.linalg.norm(axB)); sB=170.0/LB; RB=short_arc(axB)
tB=np.array([158.,0,0])-sB*(RB@kneeB)

def apply(R,s,t,P): return (np.atleast_2d(P)@ (s*R).T)+t
# verify
print("\n-- chassis-frame mapped joints (residual to station) --")
for nm,P,tgt in [("HIP",apply(RA,sA,tA,hip),[0,0,0]),
                 ("KNEE(5A)",apply(RA,sA,tA,kneeA),[158,0,0]),
                 ("KNEE(5B)",apply(RB,sB,tB,kneeB),[158,0,0]),
                 ("TOE",apply(RB,sB,tB,toe),[328,0,0])]:
    P=P[0]; print(f"{nm:9s} -> {np.round(P,2)}  target {tgt}  resid {np.round(P-np.array(tgt),3)}")
print(f"\nscale 5-A sA={sA:.3f}  (hip->knee {LA:.2f} -> 158)")
print(f"scale 5-B sB={sB:.3f}  (knee->toe {LB:.2f} -> 170)")
print("LEG2 reference: sA=4.813 (span 32.83), sB=6.002 (span 28.32)  <- leg5 delta = blade length")
# knee bend / extension
v1=hip-kneeA; v2=toe-kneeB
ang=np.degrees(np.arccos(np.clip((v1@v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)),-1,1)))
print(f"o3d interior knee angle (hip-knee-toe) = {ang:.1f} deg ; extended by {180-ang:.1f} deg to straight")

# roll diagnostic: where does o3d +Z(dorsal-ish) go for each piece after rotation
zA=RA@np.array([0,0,1.]); zB=RB@np.array([0,0,1.])
def roll_of(z):
    zp=z-z[0]*np.array([1,0,0]); return np.degrees(np.arctan2(zp[2],zp[1]))
print(f"roll-frame (atan2 of mapped o3d-Z about X): 5-A={roll_of(zA):.1f} deg, 5-B={roll_of(zB):.1f} deg, A-B offset={roll_of(zA)-roll_of(zB):.1f} deg")

# ---- export aligned meshes (chassis frame) ----
mA2=mA.copy(); mA2.vertices=apply(RA,sA,tA,mA.vertices); mA2.export(SP+"/leg5_aligned_5A.stl")
mB2=mB.copy(); mB2.vertices=apply(RB,sB,tB,mB.vertices); mB2.export(SP+"/leg5_aligned_5B.stl")
print("\nexported leg5_aligned_5A.stl / _5B.stl  bboxA",np.round(mA2.bounds,1).tolist(),"bboxB",np.round(mB2.bounds,1).tolist())

def M(R,s,t):
    m=np.eye(4); m[:3,:3]=s*R; m[:3,3]=t; return m.tolist()
out={
 "description":"LEG5 align-only: assembled o3d leg (5-A+5-B, pegs kept), extended+aligned to D-043 chassis skeleton (HIP=0,KNEE=158,TOE=328 along +X).",
 "method":"per-piece similarity: shortest-arc rotate long axis->+X (preserves o3d roll), uniform scale to span, translate to station.",
 "frame":"chassis leg frame (X=reach, Z=up, Y=pitch axis); o3d source = toy statue frame.",
 "chassis_stations_mm":{"HIP":0,"KNEE":158,"TOE":328},
 "o3d_joints_statue_mm":{"HIP":hip.tolist(),"KNEE_5A":kneeA.tolist(),"KNEE_5B":kneeB.tolist(),"TOE":toe.tolist(),
                         "knee_ball_socket_gap_mm":float(np.linalg.norm(kneeA-kneeB))},
 "scale":{"5-A":sA,"5-B":sB},
 "source_span_mm":{"5-A_hip_knee":LA,"5-B_knee_toe":LB},
 "leg2_reference_scale":{"2-A":4.812921381431387,"2-B":6.002230681606543},
 "knee_extension_deg":float(180-ang),
 "o3d_interior_knee_angle_deg":float(ang),
 "transforms_o3dstatue_to_chassis_4x4":{"5-A":M(RA,sA,tA),"5-B":M(RB,sB,tB)},
 "note":"NOTHING trimmed/hollowed/anchored. Pegs kept. Align+show only, for operator confirmation."
}
json.dump(out,open(SP+"/leg5_aligned.json","w"),indent=1)
np.save(SP+"/_leg5_final_joints.npy",{"hip":hip,"kneeA":kneeA,"kneeB":kneeB,"toe":toe,
      "RA":RA,"sA":sA,"tA":tA,"RB":RB,"sB":sB,"tB":tB},allow_pickle=True)
print("wrote leg5_aligned.json")
