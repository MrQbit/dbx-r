"""LEG1 (THE MANIPULATOR) align-only — adapted from build_align.py (leg2 recipe).
Assembled o3d leg = 1-A (upper) + 1-C (the flat OPEN-HAND blade with the wrist peg),
RAW with pegs. Extend straight and align to the D-043 chassis skeleton:
HIP->0, KNEE(wrist-junction, the 1-A/1-C joint)->158, TIP(hand fingertips)->328.
Per-piece similarity: shortest-arc long-axis->+X (preserves o3d roll), uniform scale,
translate to station. NOTHING trimmed/hollowed/anchored."""
import json, numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
AF="/home/mrqbit/Downloads/dbx-r/reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS"
T={n:np.array(v) for n,v in json.load(open(SP+"/toy_assembled_o3d.json")).items()}
def load(n): return trimesh.load(f"{AF}/{n}.stl", process=False)
def to_st_mesh(n):
    m=load(n).copy(); R=T[n][:3,:3]; t=T[n][:3,3]
    m.vertices=(m.vertices@R.T)+t; return m

def axis_and_caps(pts, frac=0.12):
    c=pts.mean(0); u=np.linalg.svd(pts-c,full_matrices=False)[2][0]
    s=(pts-c)@u
    lo=pts[s< s.min()+frac*(s.max()-s.min())].mean(0)
    hi=pts[s> s.max()-frac*(s.max()-s.min())].mean(0)
    return lo,hi,u

mA=to_st_mesh("1-A"); mC=to_st_mesh("1-C")
PA,_=trimesh.sample.sample_surface(mA,80000,seed=3)
PC,_=trimesh.sample.sample_surface(mC,80000,seed=3)
a_lo,a_hi,ua=axis_and_caps(PA)
c_lo,c_hi,uc=axis_and_caps(PC)
# HIP end of 1-A is the one FAR from 1-C; KNEE(wrist-junction) end near 1-C
d_lo=min(np.linalg.norm(a_lo-c_lo),np.linalg.norm(a_lo-c_hi))
d_hi=min(np.linalg.norm(a_hi-c_lo),np.linalg.norm(a_hi-c_hi))
if d_lo<d_hi: kneeA,hip = a_lo,a_hi
else:         kneeA,hip = a_hi,a_lo
# 1-C: knee end near kneeA; hand TIP far
if np.linalg.norm(c_lo-kneeA)<np.linalg.norm(c_hi-kneeA): kneeC,tip=c_lo,c_hi
else: kneeC,tip=c_hi,c_lo
print("HIP  =",np.round(hip,2))
print("kneeA=",np.round(kneeA,2),"  kneeC=",np.round(kneeC,2),"  gap=",round(float(np.linalg.norm(kneeA-kneeC)),2))
print("TIP  =",np.round(tip,2))

def short_arc(a):
    a=a/np.linalg.norm(a); x=np.array([1.,0,0])
    v=np.cross(a,x); c=float(a@x); s=np.linalg.norm(v)
    if s<1e-9:
        return np.eye(3) if c>0 else np.diag([ -1,-1,1.])
    vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+vx+vx@vx*((1-c)/(s*s))

# 1-A: hip->0 , kneeA->158
axA=kneeA-hip; LA=float(np.linalg.norm(axA)); sA=158.0/LA; RA=short_arc(axA)
tA=np.array([0.,0,0])-sA*(RA@hip)
# 1-C: kneeC->158 , tip->328 (span 170, same as leg2 knee->toe)
axC=tip-kneeC; LC=float(np.linalg.norm(axC)); sC=170.0/LC; RC=short_arc(axC)
tC=np.array([158.,0,0])-sC*(RC@kneeC)

def apply(R,s,t,P): return (np.atleast_2d(P)@ (s*R).T)+t
print("\n-- chassis-frame mapped joints (residual to station) --")
for nm,P,tgt in [("HIP",apply(RA,sA,tA,hip),[0,0,0]),
                 ("KNEE(1A)",apply(RA,sA,tA,kneeA),[158,0,0]),
                 ("KNEE(1C)",apply(RC,sC,tC,kneeC),[158,0,0]),
                 ("TIP",apply(RC,sC,tC,tip),[328,0,0])]:
    P=P[0]; print(f"{nm:9s} -> {np.round(P,2)}  target {tgt}  resid {np.round(P-np.array(tgt),3)}")
print(f"\nscale 1-A sA={sA:.3f}  (hip->knee {LA:.2f} -> 158)")
print(f"scale 1-C sC={sC:.3f}  (knee->tip {LC:.2f} -> 170)")
v1=hip-kneeA; v2=tip-kneeC
ang=np.degrees(np.arccos(np.clip((v1@v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)),-1,1)))
print(f"o3d interior knee(wrist-junction) angle = {ang:.1f} deg ; extended by {180-ang:.1f} deg to straight")

zA=RA@np.array([0,0,1.]); zC=RC@np.array([0,0,1.])
def roll_of(z):
    zp=z-z[0]*np.array([1,0,0]); return np.degrees(np.arctan2(zp[2],zp[1]))
print(f"roll-frame (atan2 of mapped o3d-Z about X): 1-A={roll_of(zA):.1f} deg, 1-C={roll_of(zC):.1f} deg, A-C offset={roll_of(zA)-roll_of(zC):.1f} deg")

mA2=mA.copy(); mA2.vertices=apply(RA,sA,tA,mA.vertices); mA2.export(SP+"/leg1_aligned_1A.stl")
mC2=mC.copy(); mC2.vertices=apply(RC,sC,tC,mC.vertices); mC2.export(SP+"/leg1_aligned_1C.stl")
print("\nexported leg1_aligned_1A.stl / _1C.stl  bboxA",np.round(mA2.bounds,1).tolist(),"bboxC",np.round(mC2.bounds,1).tolist())

def M(R,s,t):
    m=np.eye(4); m[:3,:3]=s*R; m[:3,3]=t; return m.tolist()
out={
 "description":"LEG1 (MANIPULATOR) align-only: assembled o3d leg (1-A+1-C open-hand blade, pegs kept), extended+aligned to D-043 chassis skeleton (HIP=0,KNEE(wrist-junction)=158,TIP=328 along +X).",
 "method":"per-piece similarity: shortest-arc rotate long axis->+X (preserves o3d roll), uniform scale to span, translate to station.",
 "frame":"chassis leg frame (X=reach, Z=up, Y=pitch axis); o3d source = toy statue frame.",
 "chassis_stations_mm":{"HIP":0,"KNEE":158,"TIP":328},
 "o3d_joints_statue_mm":{"HIP":hip.tolist(),"KNEE_1A":kneeA.tolist(),"KNEE_1C":kneeC.tolist(),"TIP":tip.tolist(),
                         "knee_ball_socket_gap_mm":float(np.linalg.norm(kneeA-kneeC))},
 "scale":{"1-A":sA,"1-C":sC},
 "source_span_mm":{"1-A_hip_knee":LA,"1-C_knee_tip":LC},
 "knee_extension_deg":float(180-ang),
 "o3d_interior_knee_angle_deg":float(ang),
 "transforms_o3dstatue_to_chassis_4x4":{"1-A":M(RA,sA,tA),"1-C":M(RC,sC,tC)},
 "note":"NOTHING trimmed/hollowed/anchored. Pegs kept. 1-C is the flat OPEN-HAND blade (manipulator distal)."
}
json.dump(out,open(SP+"/leg1_aligned.json","w"),indent=1)
np.save(SP+"/_leg1_final_joints.npy",{"hip":hip,"kneeA":kneeA,"kneeC":kneeC,"tip":tip,
      "RA":RA,"sA":sA,"tA":tA,"RC":RC,"sC":sC,"tC":tC},allow_pickle=True)
print("wrote leg1_aligned.json")
