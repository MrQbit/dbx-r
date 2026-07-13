import numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
BP="/home/mrqbit/Downloads/dbx-r/docs/build_plan"
def L(p):
    m=trimesh.load(p,process=False); return m.dump(concatenate=True) if isinstance(m,trimesh.Scene) else m
CY,CZ=1.56,4.20; NT=48; DX=3.0; X0=0.0; NX=int((345.0-0.0)/DX)+2
A=L(SP+"/leg3_enclosed_3A.stl"); B=L(SP+"/leg3_enclosed_3B.stl"); toe=L(SP+"/leg3_enclosed_toecover.stl")
frame=L(BP+"/leg_chassis_neutral_frame.stl"); servo=L(BP+"/leg_chassis_neutral_servos.stl")
shell=trimesh.util.concatenate([A,B,toe])
Ps,_=trimesh.sample.sample_surface(shell,500000,seed=1)
def cyl(P):
    y=P[:,1]-CY; z=P[:,2]-CZ; return P[:,0],np.hypot(y,z),np.arctan2(z,y)
def binxt(x,th):
    xb=np.clip(((x-X0)/DX).astype(int),0,NX-1); tb=np.clip(((th+np.pi)/(2*np.pi)*NT).astype(int),0,NT-1); return xb,tb
sx,sr,sth=cyl(Ps); sxb,stb=binxt(sx,sth)
g=np.full((NX,NT),-1e9); c=np.zeros((NX,NT),int)
np.maximum.at(g,(sxb,stb),sr); np.add.at(c,(sxb,stb),1); g[c==0]=np.nan
fv=frame.vertices; fx=fv[:,0]; m=(fx>=60)&(fx<158)
cx,cr,cth=cyl(fv[m]); xb,tb=binxt(cx,cth)
gm=g[xb,tb]; prot=cr-np.where(np.isnan(gm),-999,gm); proud=(prot>0.5)&~np.isnan(gm)
print("FEMUR frame verts proud=%d/%d"%(proud.sum(),m.sum()))
o=np.argsort(-prot[proud])[:20]
xx=cx[proud][o]; rr=cr[proud][o]; th=np.degrees(cth[proud][o]); pr=prot[proud][o]
for i in range(len(o)):
    print(f"  x={xx[i]:6.1f} r={rr[i]:5.1f} th={th[i]:6.0f}deg prot={pr[i]:5.1f}")
for x0 in range(56,160,8):
    s=proud&(cx>=x0)&(cx<x0+8); t=(cx>=x0)&(cx<x0+8)
    if t.sum()>3: print(f"  x[{x0}-{x0+8}] frame={t.sum():5d} proud={s.sum():5d} maxprot={prot[t].max():6.1f}")
