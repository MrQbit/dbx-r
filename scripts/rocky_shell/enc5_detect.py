import numpy as np, trimesh, json
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
BP="/home/mrqbit/Downloads/dbx-r/docs/build_plan"
def L(p):
    m=trimesh.load(p,process=False)
    if isinstance(m,trimesh.Scene): m=m.dump(concatenate=True)
    return m
A=L(SP+"/leg5_aligned_5A.stl"); B=L(SP+"/leg5_aligned_5B.stl")
frame=L(BP+"/leg_chassis_neutral_frame.stl")
servo=L(BP+"/leg_chassis_neutral_servos.stl")
hand =L(BP+"/leg_chassis_neutral_hand.stl")
shell=trimesh.util.concatenate([A,B])

# shell centerline: fit per-x centroid of y,z (leg roughly along X). Use robust median.
SP_s,_=trimesh.sample.sample_surface(shell,300000,seed=7)
# center offset (constant) in y,z from median over the femur/tibia span
mid=(SP_s[:,0]>40)&(SP_s[:,0]<330)
cy,cz=np.median(SP_s[mid,1]),np.median(SP_s[mid,2])
print("shell centerline offset cy,cz=",round(cy,2),round(cz,2))

def cyl(P):
    y=P[:,1]-cy; z=P[:,2]-cz
    return P[:,0], np.hypot(y,z), np.arctan2(z,y)

# Build shell OUTER radius lookup r_out(xbin,tbin) = max radius (outer crag)
NX=int(330/3)+2; NT=48
def binidx(x,th):
    xb=np.clip((x/3).astype(int),0,NX-1)
    tb=np.clip(((th+np.pi)/(2*np.pi)*NT).astype(int),0,NT-1)
    return xb,tb
sx,sr,sth=cyl(SP_s)
xb,tb=binidx(sx,sth)
r_out=np.zeros((NX,NT));
np.maximum.at(r_out,(xb,tb),sr)
# also a smoothed/min version for honest 'inside' test: use max but require neighbor support
# fill empty bins by nearest theta
for i in range(NX):
    row=r_out[i]
    if (row>0).any():
        idx=np.where(row>0)[0]
        for j in range(NT):
            if row[j]==0:
                k=idx[np.argmin(np.minimum(np.abs(idx-j),NT-np.abs(idx-j)))]
                row[j]=r_out[i,k]

def shell_r_at(x,th):
    xb,tb=binidx(x,th)
    return r_out[xb,tb]

# detect protrusion for a chassis mesh over region
def detect(m,name,xlo,xhi,n=150000):
    P,_=trimesh.sample.sample_surface(m,n,seed=2)
    sel=(P[:,0]>=xlo)&(P[:,0]<xhi)
    P=P[sel]
    x,r,th=cyl(P)
    rs=shell_r_at(x,th)
    prot=r-rs           # >0 => chassis outside shell outer surface
    return P,x,r,th,prot

print("\n=== PROTRUSION MAP (chassis beyond shell outer surface) ===")
regions=[("COXA-link",0,60),("FEMUR-link",60,158),("TIBIA-link",158,328),("FOOT/toe",328,345)]
report={}
for src_name,m in [("frame",frame),("servos",servo),("hand",hand)]:
    for rn,xlo,xhi in regions:
        P,x,r,th,prot=detect(m,rn,xlo,xhi)
        if len(prot)<20: continue
        proud=prot>1.0
        npr=int(proud.sum()); frac=npr/len(prot)
        mx=float(prot.max()) if len(prot) else 0
        if npr>0:
            # where (x range of proud)
            pxs=x[proud]
            print(f"{src_name:6s} {rn:11s} pts={len(prot):6d} proud(>1mm)={npr:6d} ({frac*100:4.1f}%) "
                  f"max_prot={mx:5.1f}mm  proud_x[{pxs.min():5.1f},{pxs.max():5.1f}]")
            report[f"{src_name}:{rn}"]={"pts":len(prot),"proud":npr,"frac":round(frac,3),
                 "max_prot_mm":round(mx,1),"proud_x":[round(float(pxs.min()),1),round(float(pxs.max()),1)]}
        else:
            print(f"{src_name:6s} {rn:11s} pts={len(prot):6d} ENCLOSED (max_prot={mx:5.1f}mm)")
json.dump({"centerline":[round(cy,3),round(cz,3)],"report":report},open(SP+"/_enc5_report.json","w"),indent=1)
np.save(SP+"/_shell5_rout.npy",{"r_out":r_out,"cy":cy,"cz":cz,"NX":NX,"NT":NT})
print("\nsaved _enc5_report.json + _shell5_rout.npy")
