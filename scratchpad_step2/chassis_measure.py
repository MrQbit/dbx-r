import numpy as np, trimesh
np.set_printoptions(suppress=True)
BP="docs/build_plan"
parts=[trimesh.load(f"{BP}/leg_chassis_neutral_{g}.stl",process=False) for g in ("frame","servos","hand")]
ch=trimesh.util.concatenate(parts)
print("chassis leg bounds",ch.bounds.round(1))
print("extents",ch.extents.round(1))
# cross-section radius (max dist from X axis, i.e. from y=z=0) in x-bins
v=ch.vertices
x=v[:,0]
for name,(x0,x1) in dict(coxa=(0,60),femur=(60,158),tibia=(158,328)).items():
    m=(x>=x0)&(x<x1)
    if m.sum()==0: print(name,"no verts");continue
    yz=v[m,1:]
    rad=np.sqrt((yz**2).sum(1))
    # bounding in y,z
    print(f"{name:6s} x[{x0},{x1}) verts={m.sum():6d} maxRfromXaxis={rad.max():.1f} y[{v[m,1].min():.1f},{v[m,1].max():.1f}] z[{v[m,2].min():.1f},{v[m,2].max():.1f}]")
# per 20mm bin max radius from axis
print("x-bin  maxR  ycen zcen")
for xb in range(0,340,20):
    m=(x>=xb)&(x<xb+20)
    if m.sum()<5: continue
    yz=v[m,1:]; rad=np.sqrt((yz**2).sum(1))
    print(f"{xb:3d} {rad.max():6.1f}  y{v[m,1].mean():+5.1f} z{v[m,2].mean():+5.1f}")
