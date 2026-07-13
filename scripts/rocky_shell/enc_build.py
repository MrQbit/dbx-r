import bpy, bmesh, numpy as np, json, math
from mathutils import noise as mnoise, Vector
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
BP="/home/mrqbit/Downloads/dbx-r/docs/build_plan"

CY,CZ=0.59,-0.21          # shell centerline offset (from detection)
CLR=4.0                    # clearance beyond chassis (mm)
NT=48                      # theta bins
DX=3.0                     # x bin width
X0,X1=0.0,345.0
NX=int((X1-X0)/DX)+2

bpy.ops.wm.read_factory_settings(use_empty=True)
def imp(path):
    before=set(bpy.data.objects); bpy.ops.wm.stl_import(filepath=path)
    return list(set(bpy.data.objects)-before)[0]
def verts_np(o):
    m=o.data; n=len(m.vertices); a=np.empty(n*3); m.vertices.foreach_get("co",a)
    v=a.reshape(-1,3).copy()
    M=np.array(o.matrix_world)
    v=(v@M[:3,:3].T)+M[:3,3]
    return v

A=imp(SP+"/leg2_aligned_2A.stl"); A.name="shellA"
B=imp(SP+"/leg2_aligned_2B.stl"); B.name="shellB"
frame=imp(BP+"/leg_chassis_neutral_frame.stl")
servo=imp(BP+"/leg_chassis_neutral_servos.stl")
hand =imp(BP+"/leg_chassis_neutral_hand.stl")

def cyl(v):
    y=v[:,1]-CY; z=v[:,2]-CZ
    return v[:,0], np.hypot(y,z), np.arctan2(z,y)

def binxt(x,th):
    xb=np.clip(((x-X0)/DX).astype(int),0,NX-1)
    tb=np.clip(((th+math.pi)/(2*math.pi)*NT).astype(int),0,NT-1)
    return xb,tb

def grid_reduce(v, mask, mode):
    x,r,th=cyl(v);
    if mask is not None: x,r,th=x[mask],r[mask],th[mask]
    xb,tb=binxt(x,th)
    g=np.full((NX,NT),np.nan); cnt=np.zeros((NX,NT),int)
    key=xb*NT+tb
    order=np.argsort(key)
    xb,tb,r,key=xb[order],tb[order],r[order],key[order]
    # group
    uk,start=np.unique(key,return_index=True)
    start=list(start)+[len(key)]
    for i,k in enumerate(uk):
        seg=r[start[i]:start[i+1]]
        xi,ti=k//NT,k%NT
        cnt[xi,ti]=len(seg)
        if mode=="max": g[xi,ti]=seg.max()
        elif mode=="min": g[xi,ti]=seg.min()
        elif mode=="p10": g[xi,ti]=np.percentile(seg,10)
    return g,cnt

# ---- chassis R_need (femur+tibia links + roll servo), EXCLUDE hip cluster ----
fv=verts_np(frame); sv=verts_np(servo); hv=verts_np(hand)
fx=fv[:,0]; sx=sv[:,0]
mask_frame=(fx>=54)&(fx<=332)                 # structural links femur..toe (exclude hip yoke root)
mask_roll =(sx>=235)&(sx<=308)                # inline roll STS only (exclude hip QDD x<200)
chas_v=np.vstack([fv[mask_frame], sv[mask_roll]])
Rneed,_=grid_reduce(chas_v,None,"max")

def fill_theta(g):
    g=g.copy()
    for i in range(NX):
        row=g[i]; idx=np.where(~np.isnan(row))[0]
        if len(idx)==0: continue
        for j in range(NT):
            if np.isnan(row[j]):
                d=np.minimum(np.abs(idx-j),NT-np.abs(idx-j)); row[j]=row[idx[np.argmin(d)]]
    return g
def maxfilter(g,rx,rt):     # grey dilation, theta wraps
    out=g.copy()
    for dx in range(-rx,rx+1):
        for dt in range(-rt,rt+1):
            out=np.fmax(out,np.roll(np.roll(g,dx,0),dt,1))
    return out

Rneed=maxfilter(Rneed,0,1)+CLR      # dilate thin features 1 theta bin + clearance (NO full-ring fill)

# ---- shell current outer (low pct per bin => robust enclosure) ----
av=verts_np(A); bv=verts_np(B)
shell_v=np.vstack([av,bv])
Rsh_min,cnt=grid_reduce(shell_v,None,"p10")
Rsh_max,_=grid_reduce(shell_v,None,"max")
Rsh_min=fill_theta(Rsh_min)         # define shell radius everywhere chassis needs

# ---- raw push (where chassis exists & shell too thin) ----
push=np.zeros((NX,NT))
valid=~np.isnan(Rneed) & ~np.isnan(Rsh_min)
push[valid]=np.clip(Rneed[valid]-Rsh_min[valid],0,None)
push=maxfilter(push,1,1)            # small dilation to bridge sparse bins / thin protrusions

# x taper: 0 for x<56, ramp to 1 by x=70 (femur), hold, ramp to 0 from x=322..332 (toe->cover)
xcent=X0+(np.arange(NX)+0.5)*DX
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
xt=smooth(56,70,xcent)*(1-smooth(330,342,xcent))
push*=xt[:,None]

# blur push over (x,theta), theta wraps
def blur(g,sx=1.4,st=1.4):
    from math import exp
    kx=np.array([exp(-(i*i)/(2*sx*sx)) for i in range(-3,4)]); kx/=kx.sum()
    kt=np.array([exp(-(i*i)/(2*st*st)) for i in range(-3,4)]); kt/=kt.sum()
    out=g.copy()
    tmp=np.zeros_like(g)
    for i,w in enumerate(kx):
        tmp+=w*np.roll(g,i-3,axis=0)
    out2=np.zeros_like(g)
    for i,w in enumerate(kt):
        out2+=w*np.roll(tmp,i-3,axis=1)   # theta wrap via roll
    return out2
pushb=blur(push)

print("PUSH stats: max=%.1f mean(nonzero)=%.2f  bins>0.5mm=%d"%(
      pushb.max(), pushb[pushb>0].mean() if (pushb>0).any() else 0, int((pushb>0.5).sum())))

# ---- apply displacement to shell verts (radial outward, bilinear sample push) ----
def sample_push(x,th):
    fx=(x-X0)/DX-0.5; ft=(th+math.pi)/(2*math.pi)*NT-0.5
    x0=np.floor(fx).astype(int); t0=np.floor(ft).astype(int)
    dx=fx-x0; dt=ft-t0
    def g(xi,ti):
        xi=np.clip(xi,0,NX-1); ti=ti%NT
        return pushb[xi,ti]
    return (g(x0,t0)*(1-dx)*(1-dt)+g(x0+1,t0)*dx*(1-dt)
           +g(x0,t0+1)*(1-dx)*dt+g(x0+1,t0+1)*dx*dt)

def displace(o):
    v=verts_np(o)
    x,r,th=cyl(v)
    p=sample_push(x,th)
    safe=r>1e-3
    ux=np.zeros_like(v);
    ux[:,1]=(v[:,1]-CY); ux[:,2]=(v[:,2]-CZ)
    nrm=np.where(safe,r,1.0)
    ux[:,1]/=nrm; ux[:,2]/=nrm
    v2=v.copy()
    v2[:,1]+=ux[:,1]*p; v2[:,2]+=ux[:,2]*p
    # back to local (identity world since imported at origin, but be safe)
    M=np.array(o.matrix_world); Minv=np.linalg.inv(M)
    vloc=(v2@Minv[:3,:3].T)+Minv[:3,3]
    flat=vloc.reshape(-1).astype(np.float64)
    o.data.vertices.foreach_set("co",flat); o.data.update()
    return p

pA=displace(A); pB=displace(B)
print("shellA moved verts>0.2mm: %d/%d  shellB: %d/%d"%(
      int((pA>0.2).sum()),len(pA),int((pB>0.2).sum()),len(pB)))

# ================= TOE COVER =================
# Compact craggy stone toe closing over the FOOT CORE / ankle flange (r~26) where the
# tibia shell tapers out. The splayed 3-finger grip digits beyond (r->57) are the
# functional foot and are LEFT exposed (flagged), like the hip cluster.
Rhand,cntH=grid_reduce(hv,None,"max")
Rcore=Rhand.copy()
Rcore[Rcore>32]=np.nan          # exclude the splayed fingers -> core envelope only
Rcore=fill_theta(Rcore)         # bridge flange notches over theta (near-convex core)
Rcore=maxfilter(Rcore,1,4)      # dilate so the stone toe wraps OVER the core, not between

def ring_radius(xi):
    base=np.full(NT,np.nan)
    for t in range(NT):
        vals=[]
        if not np.isnan(Rsh_max[xi,t]): vals.append(Rsh_max[xi,t])
        if not np.isnan(Rcore[xi,t]):   vals.append(Rcore[xi,t]+CLR)
        if vals: base[t]=max(vals)
    idx=np.where(~np.isnan(base))[0]
    if len(idx)==0: return None
    for t in range(NT):
        if np.isnan(base[t]):
            d=np.minimum(np.abs(idx-t),NT-np.abs(idx-t)); base[t]=base[idx[np.argmin(d)]]
    return base

XT0,XT1=311.0,356.0
xs=np.arange(XT0,XT1+1e-3,3.0)
rings=[]
for x in xs:
    xi=int(np.clip((x-X0)/DX,0,NX-1))
    rr=ring_radius(xi)
    if rr is None: rr=np.full(NT,12.0)
    # distal convergence to a rounded stone toe tip over the last 8mm (x348->356)
    if x>XT1-8:
        f=1-smooth(XT1-8,XT1,np.array([x]))[0]   # 1->0
        rr=rr*(0.20+0.80*f)+(1-f)*5.0
    rings.append(rr)
rings=np.array(rings)   # (nx, NT)
# smooth rings along x a touch
rings=0.25*np.roll(rings,1,0)+0.5*rings+0.25*np.roll(rings,-1,0)

# build bmesh cylinder along X with craggy noise
bm=bmesh.new()
vgrid=[]
th_arr=(-math.pi)+(np.arange(NT)+0.5)*(2*math.pi/NT)
for i,x in enumerate(xs):
    row=[]
    for t in range(NT):
        r=rings[i,t]
        y=CY+r*math.cos(th_arr[t]); z=CZ+r*math.sin(th_arr[t])
        co=Vector((x,y,z))
        # craggy displacement: 2-octave value noise along surface, amp matches stone
        nfreq=0.09
        nval=mnoise.noise(co*nfreq)+0.5*mnoise.noise(co*nfreq*2.3)
        amp=2.6
        disp=nval*amp
        # push along radial
        rad=Vector((0,math.cos(th_arr[t]),math.sin(th_arr[t])))
        co=co+rad*disp
        row.append(bm.verts.new(co))
    vgrid.append(row)
# side faces
for i in range(len(xs)-1):
    for t in range(NT):
        t2=(t+1)%NT
        bm.faces.new([vgrid[i][t],vgrid[i][t2],vgrid[i+1][t2],vgrid[i+1][t]])
# cap near end (x=308) with a center vertex (blends into shell/tibia)
c0=bm.verts.new(Vector((XT0-2,CY,CZ)))
for t in range(NT):
    t2=(t+1)%NT
    bm.faces.new([c0,vgrid[0][t2],vgrid[0][t]])
# cap far end (toe tip) — blunt rounded stone toe just past the mechanism (x412)
cN=bm.verts.new(Vector((XT1+7,CY,CZ)))
for t in range(NT):
    t2=(t+1)%NT
    bm.faces.new([cN,vgrid[-1][t],vgrid[-1][t2]])
bm.normal_update()
me=bpy.data.meshes.new("toecover"); bm.to_mesh(me); bm.free()
toe=bpy.data.objects.new("toecover",me); bpy.context.collection.objects.link(toe)
print("toe cover verts=%d faces=%d  x[%.0f..%.0f]"%(len(me.vertices),len(me.polygons),XT0,XT1))

# ---- export ----
def export(o,path):
    for x in bpy.data.objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active=o
    try:
        bpy.ops.wm.stl_export(filepath=path,export_selected_objects=True,apply_modifiers=True)
    except Exception:
        bpy.ops.export_mesh.stl(filepath=path,use_selection=True,use_mesh_modifiers=True)
export(A,SP+"/leg2_enclosed_2A.stl")
export(B,SP+"/leg2_enclosed_2B.stl")
export(toe,SP+"/leg2_enclosed_toecover.stl")

# ---- VERIFY enclosure: chassis vs (displaced shell + toe) max-radius grid ----
newshell=np.vstack([verts_np(A),verts_np(B),verts_np(toe)])
Rnew,cntN=grid_reduce(newshell,None,"max")
def check(v,mask,lo,hi,label):
    x,r,th=cyl(v)
    m=mask&(x>=lo)&(x<hi)
    x,r,th=x[m],r[m],th[m]
    xb,tb=binxt(x,th)
    rs=Rnew[xb,tb]
    prot=r-np.where(np.isnan(rs),-1,rs)
    proud=(prot>0.5)&~np.isnan(rs)
    print("  %-12s pts=%6d proud(>0.5mm)=%5d (%.1f%%) max=%.1fmm"%(
          label,len(prot),int(proud.sum()),100*proud.mean() if len(prot) else 0,
          float(prot[~np.isnan(rs)].max()) if len(prot) else 0))
print("VERIFY enclosure (after stretch+toe):")
check(fv,mask_frame,60,158,"FEMUR-link")
check(fv,mask_frame,158,328,"TIBIA-link")
check(sv,mask_roll,235,308,"ROLL-servo")
check(hv,np.ones(len(hv),bool),328,350,"FOOT-core")     # under the toe cover -> enclosed
print("  (flagged, left exposed by design:)")
check(hv,np.ones(len(hv),bool),350,415,"grip-digits")   # functional foot digits, exposed
check(sv,(sx<160),0,160,"HIP-cluster")                  # carapace shroud's job, exposed
print("BUILD_DONE")
