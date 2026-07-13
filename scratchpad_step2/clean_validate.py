import trimesh,glob,os,json,numpy as np
SF="rocky/cad/stl_derived/shells_final"
rep=json.load(open("scratchpad_step2/shells_report.json"))
V={}
for f in sorted(glob.glob(f"{SF}/*.stl")):
    m=trimesh.load(f,process=True); m.merge_vertices()
    comps=m.split(only_watertight=False)
    if len(comps)>1:
        keep=[c for c in comps if abs(c.volume)/1000>=0.5]
        # always keep the single largest even if all tiny
        if not keep: keep=[max(comps,key=lambda c:abs(c.volume))]
        removed=len(comps)-len(keep)
        if removed>0:
            m=trimesh.util.concatenate(keep); m.merge_vertices()
            m.export(f)
    m=trimesh.load(f,process=True)
    if m.volume<0: m.invert(); m.export(f)
    name=os.path.basename(f)[:-4]
    deg=int((m.area_faces<1e-9).sum())
    V[name]={"watertight":bool(m.is_watertight),"bodies":int(m.body_count),
             "degenerate_faces":deg,"volume_cm3":round(m.volume/1000,1),
             "positive_vol":bool(m.volume>0),
             "bbox_mm":[round(float(x),1) for x in m.extents],
             "max_dim_mm":round(float(m.extents.max()),1)}
rep["_validation"]=V
json.dump(rep,open("scratchpad_step2/shells_report.json","w"),indent=1)
# summary
print("total",len(V))
print("all wt",all(v["watertight"] for v in V.values()),
      "| posVol",all(v["positive_vol"] for v in V.values()),
      "| 0deg",all(v["degenerate_faces"]==0 for v in V.values()),
      "| <=250",all(v["max_dim_mm"]<=250 for v in V.values()),
      "| multibody",[k for k,v in V.items() if v["bodies"]>1])
