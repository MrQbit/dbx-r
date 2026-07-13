"""STEP 2 shell process: place o3d-oriented toy pieces over the chassis leg,
hollow to a ~4mm shell, add M2.5 anchors, clamshell-split, validate.
Voxel (EDT-morphology) pipeline — robust to the non-watertight craggy skins."""
import json, os, sys, numpy as np, trimesh
import scipy.ndimage as ndi
from scipy.spatial import cKDTree
from skimage import measure as skm
np.set_printoptions(suppress=True)

ROOT="/home/mrqbit/Downloads/dbx-r"
SD=f"{ROOT}/rocky/cad/stl_derived/trimmed_o3d"
OUT=f"{ROOT}/rocky/cad/stl_derived/shells_final"
os.makedirs(OUT,exist_ok=True)
T=json.load(open("/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad/toy_assembled_o3d.json"))
DISTAL={1:"1-C",2:"2-B",3:"3-B",4:"4-B",5:"5-B"}

# chassis stations (leg_geom / D-043)
HIP,P1,KNEE,TIP = 0.0,60.0,158.0,328.0
SEGS={"coxa":(0.0,60.0),"femur":(60.0,158.0),"tibia":(158.0,336.0)}  # tibia extends past tip for toe cover
ANCHORS={"coxa":(24.0,48.0),"femur":(76.0,140.0),"tibia":(180.0,282.0)}
PITCH=1.5
WALL=4.0
CLR=1.0            # chassis clearance in cavity
FAT_MARGIN=15.0   # cap local fatten to stone_R + this (D-045 local thin-axis, no hip balloon)
TOE_OVER=10.0     # scale tibia so toe lands ~this past chassis TIP (foot-spike cover)

def load(p):
    m=trimesh.load(os.path.join(SD,f"{p}_trimmed.stl"),process=False)
    m.apply_transform(np.array(T[p])); return m
def samp(v,n=6000):
    idx=np.random.default_rng(0).choice(len(v),min(n,len(v)),replace=False); return v[idx]

# chassis neutral solid (frame+servos+hand) in leg frame
BP=f"{ROOT}/docs/build_plan"
CHASSIS=trimesh.util.concatenate([trimesh.load(f"{BP}/leg_chassis_neutral_{g}.stl",process=False)
                                  for g in ("frame","servos","hand")])

def piece_frame(pts_prox_piece, pts_dist_piece, proximal_is_A):
    """Return (proximal_pt, axis_unit, dorsal_unit, lateral_unit) for ONE piece,
    using the junction (knee) shared with the other piece to orient."""
    pass

def endpoints(va,vb):
    tr=cKDTree(vb); d,i=tr.query(va); k=int(np.argmin(d)); knee=(va[k]+vb[i[k]])/2
    return knee

def axis_ends(v):
    c=v.mean(0); _,_,Vt=np.linalg.svd(v-c); u=Vt[0]; p=v@u
    lo=v[np.argsort(p)[:40]].mean(0); hi=v[np.argsort(p)[-40:]].mean(0)
    return lo,hi

def place_transform(prox, dist, seg_start, seg_len_chassis, scale):
    """Build fn mapping statue pts -> leg frame: prox->x=seg_start, along +X, dorsal->+Z."""
    a=(dist-prox); a/=np.linalg.norm(a)
    up=np.array([0,0,1.0]); d0=up-np.dot(up,a)*a
    if np.linalg.norm(d0)<1e-2: d0=np.array([0,1.,0])-np.dot(np.array([0,1.,0]),a)*a
    d=d0/np.linalg.norm(d0); l=np.cross(d,a)
    R=np.array([a,l,d])
    def f(P):
        return (R@((P-prox).T)).T*scale + np.array([seg_start,0,0])
    return f,R

def rasterize(mesh, origin, dims, pitch):
    """Solid boolean array on shared grid via surface voxels + per-X-slice fill."""
    vox=mesh.voxelized(pitch)
    pts=vox.points
    idx=np.round((pts-origin)/pitch).astype(int)
    m=(idx>=0).all(1)&(idx[:,0]<dims[0])&(idx[:,1]<dims[1])&(idx[:,2]<dims[2])
    idx=idx[m]
    surf=np.zeros(dims,bool); surf[idx[:,0],idx[:,1],idx[:,2]]=True
    surf=ndi.binary_closing(surf,ndi.generate_binary_structure(3,1),iterations=1)
    sol=np.zeros(dims,bool)
    for xi in range(dims[0]):
        if surf[xi].any(): sol[xi]=ndi.binary_fill_holes(surf[xi])
    sol|=surf
    return sol

def edt(mask): return ndi.distance_transform_edt(mask)*PITCH
def dilate(mask,d): return edt(~mask)<=d
def erode(mask,d):  return edt(mask)>d

def vol_to_mesh(vol, origin, pitch):
    pad=np.pad(vol.astype(np.float32),2)
    verts,faces,_,_=skm.marching_cubes(pad,level=0.5,spacing=(pitch,pitch,pitch))
    verts=verts+(origin-2*pitch)
    m=trimesh.Trimesh(verts,faces,process=True)
    m.fix_normals()
    if m.volume<0: m.invert()
    return m

def voxel_wallstats(solid_fat,interior,dims):
    """wall (mm) distribution over the shell outer surface, ignoring x-end rims."""
    dcav=edt(~interior)
    outer=solid_fat&~ndi.binary_erosion(solid_fat,iterations=1)
    x0=int(dims[0]*0.1); x1=int(dims[0]*0.9)
    band=np.zeros(dims,bool); band[x0:x1]=True
    sel=outer&band&(dcav>0)
    if not sel.any(): return dict(min=float('nan'),p5=float('nan'),p50=float('nan'))
    w=dcav[sel]
    return dict(min=round(float(w.min()),1),p5=round(float(np.percentile(w,5)),1),
                p50=round(float(np.percentile(w,50)),1))

def build_leg(leg, report):
    A=load(f"{leg}-A"); B=load(DISTAL[leg])
    va=samp(A.vertices); vb=samp(B.vertices)
    knee=endpoints(va,vb)
    aLo,aHi=axis_ends(va); bLo,bHi=axis_ends(vb)
    aHip,aKnee=(aHi,aLo) if np.linalg.norm(aLo-knee)<np.linalg.norm(aHi-knee) else (aLo,aHi)
    bToe,bKnee=(bHi,bLo) if np.linalg.norm(bLo-knee)<np.linalg.norm(bHi-knee) else (bLo,bHi)
    aL=np.linalg.norm(aKnee-aHip); bL=np.linalg.norm(bToe-bKnee)
    scaleA=(KNEE-HIP)/aL; scaleB=(TIP-KNEE+TOE_OVER)/bL
    fA,RA=place_transform(aHip,aKnee,HIP,KNEE,scaleA)
    fB,RB=place_transform(bKnee,bToe,KNEE,(TIP-KNEE),scaleB)
    Ap=A.copy(); Ap.vertices=fA(Ap.vertices)
    Bp=B.copy(); Bp.vertices=fB(Bp.vertices)
    report[leg]={"scaleA":round(scaleA,2),"scaleB":round(scaleB,2),
                 "knee_frac_measured":round(aL/(aL+bL),3),"segments":{}}
    # piece->segment source
    for seg,(x0,x1) in SEGS.items():
        src = Ap if seg in ("coxa","femur") else Bp
        do_segment(leg,seg,x0,x1,src,report)

def do_segment(leg,seg,x0,x1,src_placed,report):
    # clip chassis + shell to x-range (+margin) and rasterize on shared grid
    xmarg=6.0
    lo=np.array([x0-xmarg,-70,-70.]); hi=np.array([x1+xmarg,70,70.])
    # shell mesh bounds within seg
    sv=src_placed.vertices
    inb=(sv[:,0]>=x0-xmarg)&(sv[:,0]<=x1+xmarg)
    if inb.sum()<50:
        report[leg]["segments"][seg]={"error":"no shell verts in range"}; return
    smin=sv[inb].min(0)-3; smax=sv[inb].max(0)+3
    cmin=CHASSIS.vertices.min(0); cmax=CHASSIS.vertices.max(0)
    # grid spans shell region (don't chase far chassis); include chassis within shell xy-ish
    gmin=np.minimum(smin,[x0-xmarg,smin[1],smin[2]])
    gmin=np.array([x0-xmarg, min(smin[1],-46), min(smin[2],-46)])
    gmax=np.array([x1+xmarg, max(smax[1],46), max(smax[2],46)])
    origin=gmin.copy()
    dims=np.ceil((gmax-gmin)/PITCH).astype(int)+1
    dims=tuple(int(d) for d in dims)
    # rasterize shell + chassis onto the shared grid (grid x-bounds limit the range)
    solid=rasterize(src_placed,origin,dims,PITCH)
    chassis=rasterize(CHASSIS,origin,dims,PITCH)
    # restrict chassis to the segment x-span (avoid pulling neighbour-link mass)
    xi0=max(0,int(np.floor((x0-origin[0])/PITCH))); xi1=int(np.ceil((x1-origin[0])/PITCH))
    ch_seg=np.zeros(dims,bool); ch_seg[xi0:xi1+1]=chassis[xi0:xi1+1]; chassis=ch_seg
    # axis radius field (about leg X axis y=z=0)
    yy=(np.arange(dims[1])*PITCH+origin[1])
    zz=(np.arange(dims[2])*PITCH+origin[2])
    Y,Z=np.meshgrid(yy,zz,indexing='ij')
    rax=np.sqrt(Y**2+Z**2)  # (dims1,dims2)
    # stone local radius per x-slice (max r where solid)
    stoneR=np.zeros(dims[0])
    for xi in range(dims[0]):
        if solid[xi].any(): stoneR[xi]=rax[solid[xi]].max()
    # proud (natural stone): chassis voxels outside stone
    proud_mask=chassis&~solid
    proud_mm=0.0
    if proud_mask.any():
        proud_mm=float(edt(~solid)[proud_mask].max())
    # fatten: need chassis+WALL+CLR enclosed, capped to stoneR+FAT_MARGIN
    needed=dilate(chassis,WALL+CLR) if chassis.any() else np.zeros(dims,bool)
    Rcap=(stoneR+FAT_MARGIN)[:,None,None]
    within_cap=rax[None,:,:]<=Rcap
    fatten=needed&~solid&within_cap
    solid_fat=solid|fatten
    # residual proud AFTER fatten (chassis still outside capped stone -> expected hip cluster)
    resid_mask=chassis&~solid_fat
    resid_mm=float(edt(~solid_fat)[resid_mask].max()) if resid_mask.any() else 0.0
    enclosed = not resid_mask.any()
    proud_x=None
    if resid_mask.any():
        xs=np.where(resid_mask.any((1,2)))[0]; proud_x=[round(float(xs.min()*PITCH+origin[0]),0),
                                                          round(float(xs.max()*PITCH+origin[0]),0)]
    # cavity: erode wall, force chassis+clr hollow (but stay inside solid_fat)
    interior=erode(solid_fat,WALL)
    if chassis.any():
        interior=interior|(dilate(chassis,CLR)&erode(solid_fat,0.5))
    hollow=solid_fat&~interior
    # anchors (2, +Z top) — voxel bosses bored M2.5
    for xa in ANCHORS[seg]:
        add_anchor(hollow,solid_fat,interior,chassis,origin,dims,xa)
    # meshes
    m_solid=vol_to_mesh(solid_fat,origin,PITCH)
    m_hollow=vol_to_mesh(hollow,origin,PITCH)
    # clamshell split at y=0 (voxel space -> capped watertight halves)
    yi_cut=int(round((0-origin[1])/PITCH))
    Lvol=hollow.copy(); Lvol[:,:yi_cut,:]=False
    Rvol=hollow.copy(); Rvol[:,yi_cut:,:]=False
    Lh=vol_to_mesh(Lvol,origin,PITCH) if Lvol.any() else None
    Rh=vol_to_mesh(Rvol,origin,PITCH) if Rvol.any() else None
    # export
    base=f"{OUT}/leg{leg}_{seg}"
    m_solid.export(f"{base}_solid.stl"); m_hollow.export(f"{base}_hollow.stl")
    if Lh is not None: Lh.export(f"{base}_Lhalf.stl")
    if Rh is not None: Rh.export(f"{base}_Rhalf.stl")
    # wall stats via voxel EDT (cavity-to-outer) over the body
    ws=voxel_wallstats(solid_fat,interior,dims)
    report[leg]["segments"][seg]={
        "scale_src": "A" if seg!="tibia" else "B",
        "stoneR_mm": round(float(stoneR.max()),1),
        "shaft_enclosed": bool(enclosed),
        "proud_natural_mm": round(proud_mm,1),
        "proud_residual_mm": round(resid_mm,1),
        "proud_x_span": proud_x,
        "wall_min_mm": ws["min"], "wall_p5_mm": ws["p5"], "wall_p50_mm": ws["p50"],
        "solid_vol_cm3": round(m_solid.volume/1000,1),
        "hollow_vol_cm3": round(m_hollow.volume/1000,1),
    }
    for tag,mm in [("solid",m_solid),("hollow",m_hollow),("Lhalf",Lh),("Rhalf",Rh)]:
        validate(f"leg{leg}_{seg}_{tag}", mm, report)

def add_anchor(hollow,solid_fat,interior,chassis,origin,dims,xa):
    xi=int(round((xa-origin[0])/PITCH))
    if xi<1 or xi>=dims[0]-1: return
    # column at y=0 (+Z top). find chassis top z and cavity ceiling z at that x near y=0
    yi=int(round((0-origin[1])/PITCH))
    r=int(round(4.0/PITCH)); rb=int(round(1.7/PITCH))
    zc=np.arange(dims[2])
    # cavity ceiling = max z of interior at (xi, y~0)
    col_int=interior[xi, max(0,yi-1):yi+2, :].any(0)
    if not col_int.any(): return
    z_ceil=np.where(col_int)[0].max()
    col_ch=chassis[xi, max(0,yi-1):yi+2, :].any(0) if chassis.any() else np.zeros(dims[2],bool)
    z_floor=np.where(col_ch)[0].max()+1 if col_ch.any() else max(0,z_ceil-int(round(10/PITCH)))
    if z_floor>=z_ceil: z_floor=max(0,z_ceil-2)
    for yy in range(max(0,yi-r),min(dims[1],yi+r+1)):
        for xx in range(max(0,xi-r),min(dims[0],xi+r+1)):
            if (xx-xi)**2+(yy-yi)**2>r*r: continue
            hollow[xx,yy,z_floor:z_ceil+1]=True
    # bore
    for yy in range(max(0,yi-rb),min(dims[1],yi+rb+1)):
        for xx in range(max(0,xi-rb),min(dims[0],xi+rb+1)):
            if (xx-xi)**2+(yy-yi)**2>rb*rb: continue
            hollow[xx,yy,z_floor:z_ceil]=False

def measure_minwall(mesh):
    # split into outer/inner by ray from centroid? approximate: nearest-neighbor between
    # the two largest connected surface components.
    try:
        comps=mesh.split(only_watertight=False)
        comps=sorted(comps,key=lambda m:len(m.vertices),reverse=True)
        if len(comps)>=2:
            outer,inner=comps[0],comps[1]
            d,_=cKDTree(outer.vertices).query(inner.vertices)
            return float(np.percentile(d,2))
    except Exception: pass
    # fallback: use thickness sampling via edt not available here
    return float('nan')

def validate(name,mesh,report):
    if mesh is None:
        report.setdefault("_validation",{})[name]={"error":"None"}; return
    deg=int((mesh.area_faces<1e-9).sum())
    report.setdefault("_validation",{})[name]={
        "watertight":bool(mesh.is_watertight),
        "bodies":int(mesh.body_count),
        "degenerate_faces":deg,
        "volume_cm3":round(mesh.volume/1000,1),
        "positive_vol":bool(mesh.volume>0),
        "bbox_mm":[round(float(x),1) for x in mesh.extents],
        "max_dim_mm":round(float(mesh.extents.max()),1),
    }

if __name__=="__main__":
    legs=[int(x) for x in sys.argv[1:]] or list(range(1,6))
    report={}
    for leg in legs:
        print(f"--- leg {leg} ---",flush=True)
        build_leg(leg,report)
        for s,info in report[leg]["segments"].items():
            print(f"  {s}: {info}",flush=True)
    json.dump(report,open(f"{ROOT}/scratchpad_step2/shells_report.json","w"),indent=1)
    print("done")
