"""ASCII yz occupancy slices of the aligned N-B distal tip: shows the cleft void
directly. Calibrate on leg2 (groove z~2.5 opening +y), then read leg4."""
import numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"

def slices(path, tag, xs):
    m=trimesh.load(path, process=False)
    if isinstance(m,trimesh.Scene): m=m.dump(concatenate=True)
    tip=float(m.bounds[1][0])
    print(f"\n===== {tag} tip_x={tip:.1f} =====")
    for dx in xs:
        x0=tip-dx
        try:
            sec=m.section(plane_origin=[x0,0,0],plane_normal=[1,0,0])
            if sec is None: print(f"[x={x0:.1f}] no section"); continue
            pts=sec.vertices[:,1:]
        except Exception as e:
            print("section fail",e); continue
        # fill: rasterize the section polygons via containment on a grid
        p2,_= sec.to_planar()
        ylo,zlo=pts.min(0)-2; yhi,zhi=pts.max(0)+2
        ny=int((yhi-ylo)/1.2)+1; nz=int((zhi-zlo)/1.2)+1
        gy=np.linspace(ylo,yhi,ny); gz=np.linspace(zlo,zhi,nz)
        G=np.stack(np.meshgrid(gy,gz,indexing='ij'),-1).reshape(-1,2)
        # to_planar frame: X=world -Y? -> safer: use trimesh Path3D->Path2D mapping
        T=p2[1] if isinstance(p2,tuple) else None
        try:
            path2d = sec.to_planar()[0]
            inside = path2d.contains(( (np.c_[G,np.zeros(len(G))] ) @ np.eye(3)[:, :2]))
        except Exception:
            inside=None
        # fallback: crude point-cloud occupancy from surface samples near the slice
        print(f"[x=tip-{dx:.0f}={x0:.1f}]  (rows=z {zhi:.0f}->{zlo:.0f}, cols=y {ylo:.0f}->{yhi:.0f}) 1 col=1.2mm")
        P,_=trimesh.sample.sample_surface(m,400000,seed=1)
        Q=P[np.abs(P[:,0]-x0)<0.9][:,1:]
        occ=np.zeros((nz,ny),bool)
        if len(Q):
            iy=np.clip(((Q[:,0]-ylo)/1.2).astype(int),0,ny-1)
            iz=np.clip(((Q[:,1]-zlo)/1.2).astype(int),0,nz-1)
            occ[iz,iy]=True
        for k in range(nz-1,-1,-1):
            z=zlo+k*1.2
            print(f"  z{z:6.1f} |"+"".join("#" if occ[k,j] else "." for j in range(ny)))
        print("  y-axis:  "+"".join("|" if abs((ylo+j*1.2))<0.6 else " " for j in range(ny))+"   (| = y=0)")

slices(SP+"/leg2_aligned_2B.stl","LEG2 2-B (calibration)",[3,8,14])
slices(SP+"/leg4_aligned_4B.stl","LEG4 4-B",[3,8,14])
