#!/usr/bin/env python3
"""PROFILE the OFFICIAL Rocky sculpt and LOCATE the 3-finger manipulator hands.

STEP 1 of the refine job (per operator hard-requirement #1): before ANY cutting,
import the master sculpt, detect the 5 radial limbs, find each limb's distal tip,
and detect finger-like protrusions there (thin, separated lobes). Render overview
shots + a close-up of every limb tip so we can VISUALLY confirm the fingers and
report exactly which limb tips carry them and at what size.

NO cutting of the deliverable happens here. Read-only analysis + renders.

Run:  blender --background --python scripts/blender_rocky_profile.py
Out:  docs/media/rocky_hands_before.png  (+ per-limb tip close-ups)
      rocky/cad/stl_derived/rocky_profile_report.json
"""
import sys, os, math, json
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
MASTER = os.path.join(ROOT, "reference/self_print_rocky/rocky-statue-figure-files/"
                            "statue_unsupported/statue_unsupported.stl")
MEDIA = os.path.join(ROOT, "docs/media")
STL_OUT = os.path.join(ROOT, "rocky/cad/stl_derived")
os.makedirs(MEDIA, exist_ok=True); os.makedirs(STL_OUT, exist_ok=True)
N_LEGS = 5

report = {"master": os.path.relpath(MASTER, ROOT), "units": "raw master mm (unscaled)"}


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for b in list(c):
            try: c.remove(b)
            except Exception: pass


def imp(p):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=p)
    else: bpy.ops.import_mesh.stl(filepath=p)
    return bpy.context.selected_objects[0]


def act(o):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active = o


# -------- load + center (no scaling: report true sculpt mm) -------------------
clear()
raw = imp(MASTER)
act(raw); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.02); bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
V = [v.co.copy() for v in raw.data.vertices]
zmin = min(p.z for p in V); zmax = max(p.z for p in V)
cx0 = sum(p.x for p in V)/len(V); cy0 = sum(p.y for p in V)/len(V)
rad0 = [math.hypot(p.x-cx0, p.y-cy0) for p in V]; rmax0 = max(rad0)
core = [p for p, r in zip(V, rad0) if r < 0.35*rmax0]
AXx = sum(p.x for p in core)/len(core); AXy = sum(p.y for p in core)/len(core)
raw.data.transform(Matrix.Translation(Vector((-AXx, -AXy, -zmin)))); raw.data.update()
V = [v.co.copy() for v in raw.data.vertices]
rad = [math.hypot(p.x, p.y) for p in V]; rmax = max(rad); zmax = max(p.z for p in V)
report["figure_dims_mm"] = [round(2*rmax, 1), round(2*rmax, 1), round(zmax, 1)]
report["vert_count"] = len(V)
print(f"[prof] verts={len(V)} rmax={rmax:.1f} zmax={zmax:.1f}")

# -------- detect 5 limb azimuths from outer-vertex histogram -----------------
az = [math.degrees(math.atan2(p.y, p.x)) for p, r in zip(V, rad) if r > 0.55*rmax]
BINS = 72; hist = [0]*BINS
for a in az: hist[int((a+180) % 360/(360/BINS))] += 1
sm = [sum(hist[(i+k) % BINS] for k in range(-2, 3)) for i in range(BINS)]
cand = sorted(range(BINS), key=lambda i: -sm[i]); peaks = []
for i in cand:
    a = i*(360/BINS)-180
    if all(abs((a-p+180) % 360-180) > 36 for p in peaks): peaks.append(a)
    if len(peaks) == N_LEGS: break
peaks.sort()
report["limb_azimuths_deg"] = [round(p) for p in peaks]
print(f"[prof] limb azimuths = {[round(p) for p in peaks]}")

# -------- per limb: find the distal TIP cluster + detect fingers -------------
# Fingers are thin, separated protrusions at the extreme tip of a limb. Detect by
# taking the vertices in the distal shell of each limb sector, projecting onto the
# plane perpendicular to the limb's local reach direction, clustering them, and
# counting well-separated lobes (candidate digits) with their thickness.

def limb_sector(a):
    lo, hi = a-36, a+36
    idx = [i for i, (p, r) in enumerate(zip(V, rad))
           if r > 0.30*rmax and (abs(((math.degrees(math.atan2(p.y, p.x))-a+180) % 360)-180) < 36)]
    return idx

limbs = []
tip_targets = []
for li, a in enumerate(peaks):
    idx = limb_sector(a)
    if not idx:
        limbs.append({"az": round(a), "note": "empty sector"}); continue
    pts = [V[i] for i in idx]
    ar = math.radians(a); ux, uy = math.cos(ar), math.sin(ar)
    # reach coordinate: how far out along the limb azimuth (in-plane) each vert is
    reach = [p.x*ux + p.y*uy for p in pts]
    rmn, rmx = min(reach), max(reach)
    # distal shell = outer 12% of the reach span
    thr = rmx - 0.12*(rmx-rmn)
    tipv = [p for p, rc in zip(pts, reach) if rc >= thr]
    if len(tipv) < 8:
        tipv = sorted(pts, key=lambda p: -(p.x*ux+p.y*uy))[:max(8, len(pts)//20)]
    tc = Vector((sum(p.x for p in tipv)/len(tipv), sum(p.y for p in tipv)/len(tipv),
                 sum(p.z for p in tipv)/len(tipv)))
    # tip bbox
    txs = [p.x for p in tipv]; tys = [p.y for p in tipv]; tzs = [p.z for p in tipv]
    tip_dims = [round(max(txs)-min(txs), 1), round(max(tys)-min(tys), 1), round(max(tzs)-min(tzs), 1)]
    # cluster tip verts in the plane perpendicular to the limb azimuth (Y' = tangential,
    # Z = vertical). Fingers separate in that cross-plane.
    proj = []  # (tangential, z)
    for p in tipv:
        tang = -p.x*uy + p.y*ux
        proj.append((tang, p.z))
    # simple grid clustering to count separated lobes
    if proj:
        t0 = min(q[0] for q in proj); t1 = max(q[0] for q in proj)
        z0 = min(q[1] for q in proj); z1 = max(q[1] for q in proj)
        GT = max(1, int((t1-t0)/2.2)+1); GZ = max(1, int((z1-z0)/2.2)+1)
        occ = set()
        for (t, z) in proj:
            gi = int((t-t0)/2.2) if t1 > t0 else 0
            gj = int((z-z0)/2.2) if z1 > z0 else 0
            occ.add((gi, gj))
        # connected components on the occupancy grid (8-neighbourhood)
        seen = set(); comps = 0; comp_sizes = []
        for cell in occ:
            if cell in seen: continue
            comps += 1; stack = [cell]; seen.add(cell); sz = 0
            while stack:
                c = stack.pop(); sz += 1
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nb = (c[0]+dx, c[1]+dy)
                        if nb in occ and nb not in seen:
                            seen.add(nb); stack.append(nb)
            comp_sizes.append(sz)
        lobes = comps
        cross_span = [round(t1-t0, 1), round(z1-z0, 1)]
    else:
        lobes = 0; cross_span = [0, 0]
    info = {"az": round(a), "reach_span_mm": round(rmx-rmn, 1),
            "tip_center_xyz": [round(tc.x, 1), round(tc.y, 1), round(tc.z, 1)],
            "tip_bbox_mm": tip_dims, "tip_cross_span_TxZ_mm": cross_span,
            "distal_lobes_detected": lobes, "tip_vert_samples": len(tipv)}
    limbs.append(info)
    tip_targets.append((li, a, tc, tip_dims))
    print(f"[prof] limb az={round(a):4d} tip@({tc.x:.0f},{tc.y:.0f},{tc.z:.0f}) "
          f"bbox={tip_dims} lobes={lobes}")

report["limbs"] = limbs

# ============================ RENDER =========================================
mat = bpy.data.materials.new("clay"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.62, 0.60, 0.57, 1.0)
b.inputs["Roughness"].default_value = 0.75
if len(raw.data.materials) == 0: raw.data.materials.append(mat)
act(raw); bpy.ops.object.shade_flat()

world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.20, 0.21, 0.23, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8


def add_light(kind, name, energy, loc, rot, size=400):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; return o

add_light("SUN", "key", 3.0, (0, 0, 1500), (math.radians(45), math.radians(15), math.radians(30)))
add_light("AREA", "fill", 30000, (-2*rmax, -2*rmax, 2*rmax), (math.radians(55), 0, math.radians(-40)))
add_light("AREA", "rim", 22000, (2*rmax, 2*rmax, 2*rmax), (math.radians(60), 0, math.radians(150)))

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 1000; sc.render.resolution_y = 1000
try: sc.eevee.use_gtao = True
except Exception: pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt)
con = cam.constraints.new("TRACK_TO"); con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"


def shoot(path, cam_loc, tgt_loc, lens=52):
    cam.data.lens = lens; cam.location = cam_loc; tgt.location = tgt_loc
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    print("[render]", path)

# overview shots
D = rmax*2.7; zc = zmax*0.5
shoot(os.path.join(MEDIA, "rocky_profile_iso.png"), (D*0.62, -D*0.62, D*0.55), (0, 0, zc))
shoot(os.path.join(MEDIA, "rocky_profile_front.png"), (0, -D, zc+rmax*0.2), (0, 0, zc))
shoot(os.path.join(MEDIA, "rocky_profile_top.png"), (0.01, 0, D*1.25), (0, 0, zc))
shoot(os.path.join(MEDIA, "rocky_profile_back.png"), (0, D, zc+rmax*0.2), (0, 0, zc))

# per-limb tip close-ups (two angles each) -> contact-sheet style filenames
tip_shots = []
for (li, a, tc, dims) in tip_targets:
    ar = math.radians(a)
    # camera sits out beyond the tip along the limb azimuth, slightly above
    dd = 55.0
    for suff, off in (("a", (math.cos(ar)*dd, math.sin(ar)*dd, dd*0.5)),
                      ("b", (math.cos(ar+1.1)*dd, math.sin(ar+1.1)*dd, dd*0.35))):
        p = os.path.join(MEDIA, f"rocky_tip_limb{li}_{round(a)}_{suff}.png")
        shoot(p, (tc.x+off[0], tc.y+off[1], tc.z+off[2]), (tc.x, tc.y, tc.z), lens=85)
        tip_shots.append(p)

# ---- build a contact sheet 'rocky_hands_before.png' from the tip close-ups ---
# Use Blender's compositor image nodes to tile the per-limb 'a' shots into one grid.
report["tip_closeups"] = [os.path.relpath(p, ROOT) for p in tip_shots]
report["overview_renders"] = [
    "docs/media/rocky_profile_iso.png", "docs/media/rocky_profile_front.png",
    "docs/media/rocky_profile_top.png", "docs/media/rocky_profile_back.png"]

with open(os.path.join(STL_OUT, "rocky_profile_report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("[done] profile report ->", os.path.join(STL_OUT, "rocky_profile_report.json"))
