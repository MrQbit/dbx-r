"""Ray-cast height maps of the toe tips. Leg2 from +y (groove known: valley at
z~2.5 running to the tip) calibrates the picture; leg4 from +z shows its groove
in (x,y); leg4 from +y for cross-check."""
import numpy as np, trimesh
SP="/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"

def hmap(path, tag, axis, span_u, span_v, ulab, vlab):
    m=trimesh.load(path, process=True)
    tip=float(m.bounds[1][0])
    us=np.arange(span_u[0],span_u[1],1.5)   # x stations rel tip
    vs=np.arange(span_v[0],span_v[1],1.5)
    U,Vv=np.meshgrid(us,vs,indexing='ij')
    n=U.size
    if axis=="z":   # cast from z=+50 downward; grid over (x, y)
        O=np.c_[(tip+U).ravel(), Vv.ravel(), np.full(n,50.0)]; D=np.tile([0,0,-1.0],(n,1))
    else:           # cast from y=+50 toward -y; grid over (x, z)
        O=np.c_[(tip+U).ravel(), np.full(n,50.0), Vv.ravel()]; D=np.tile([0,-1.0,0],(n,1))
    loc,ray,_=m.ray.intersects_location(O,D,multiple_hits=False)
    H=np.full(n,np.nan)
    H[ray]= loc[:,2] if axis=="z" else loc[:,1]
    H=H.reshape(U.shape)
    print(f"\n== {tag}: first-hit height casting -{axis}  rows=x(tip{span_u[0]:+.0f}..{span_u[1]:+.0f}) cols={vlab} {span_v[0]:.0f}..{span_v[1]:.0f} (tip_x={tip:.1f}) ==")
    # legend: height quantized to letters a(low)..z(high), '.'=miss
    valid=H[~np.isnan(H)]
    lo,hi=np.percentile(valid,2),np.percentile(valid,98)
    print("   height range shown: %.1f (a) .. %.1f (z)"%(lo,hi))
    hdr="        "+"".join(f"{v:5.0f}"[-1] if abs(v%5)<0.75 else " " for v in vs)
    print(hdr+f"   ({vlab} axis, ticks every 5)")
    for i,u in enumerate(us):
        row=""
        for j in range(len(vs)):
            h=H[i,j]
            row+="." if np.isnan(h) else chr(ord('a')+int(np.clip((h-lo)/(hi-lo+1e-9)*25,0,25)))
        print(f" x=t{u:+5.1f} {row}")

hmap(SP+"/leg2_aligned_2B.stl","LEG2 2-B cast -y (groove z~2.5 KNOWN)", "y", (-26,0.1), (-14,14), "x","z")
hmap(SP+"/leg4_aligned_4B.stl","LEG4 4-B cast -z (suspected opening +z)","z", (-26,0.1), (-16,16), "x","y")
hmap(SP+"/leg4_aligned_4B.stl","LEG4 4-B cast -y (cross-check)","y", (-26,0.1), (-16,20), "x","z")
