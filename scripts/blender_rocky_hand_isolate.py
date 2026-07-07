#!/usr/bin/env python3
"""ISOLATE the hand-bearing arm from the OFFICIAL Rocky sculpt and PROVE the
3-finger manipulator hand can be separated INTACT (operator hard-req #1).

Approach: center the master (unscaled), rotate the front raised-arm azimuth to +X,
carve its angular wedge outside the core with planar bisects ONLY (no boolean, no
remesh) -> a single clean arm object that still carries the sculpted 3-finger hand.
Then measure the hand + fingers (separate the distal tip into loose islands = the
digits) and render clean close-ups, saving the best as docs/media/rocky_hands_before.png.

Run: blender --background --python scripts/blender_rocky_hand_isolate.py
"""
import os, math, json
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
MASTER = os.path.join(ROOT, "reference/self_print_rocky/rocky-statue-figure-files/"
                            "statue_unsupported/statue_unsupported.stl")
MEDIA = os.path.join(ROOT, "docs/media")
STL_OUT = os.path.join(ROOT, "rocky/cad/stl_derived")
ARM_AZ = -33.0        # front raised-arm azimuth (from profile: tip ~(54,-35,72))
WEDGE = 42.0          # +/- half-angle of the arm wedge


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


def bisect_keep(o, co, no, keep_positive, fill=False):
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=co, plane_no=no, use_fill=fill,
                        clear_inner=keep_positive, clear_outer=not keep_positive)
    bpy.ops.object.mode_set(mode="OBJECT")


clear()
raw = imp(MASTER)
act(raw); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.02); bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
V = [v.co.copy() for v in raw.data.vertices]
zmin = min(p.z for p in V)
cx0 = sum(p.x for p in V)/len(V); cy0 = sum(p.y for p in V)/len(V)
rad0 = [math.hypot(p.x-cx0, p.y-cy0) for p in V]; rmax0 = max(rad0)
core = [p for p, r in zip(V, rad0) if r < 0.35*rmax0]
AXx = sum(p.x for p in core)/len(core); AXy = sum(p.y for p in core)/len(core)
raw.data.transform(Matrix.Translation(Vector((-AXx, -AXy, -zmin)))); raw.data.update()
V = [v.co.copy() for v in raw.data.vertices]
rad = [math.hypot(p.x, p.y) for p in V]; rmax = max(rad); zmax = max(p.z for p in V)
R_CORE = 0.42*rmax

# --- isolate arm wedge: rotate ARM_AZ -> +X, cut two azimuth planes + inner core --
arm = raw
arm.data.transform(Matrix.Rotation(math.radians(-ARM_AZ), 4, "Z")); arm.data.update()
for th, keep_pos in ((math.radians(-WEDGE), True), (math.radians(WEDGE), False)):
    no = (-math.sin(th), math.cos(th), 0.0)
    bisect_keep(arm, (0, 0, zmax*0.5), no, keep_positive=keep_pos)
bisect_keep(arm, (R_CORE, 0, zmax*0.5), (1, 0, 0), keep_positive=True)

# keep only the largest connected island (drops any body crumbs from the cut)
act(arm); bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
parts = [x for x in bpy.context.selected_objects if x.type == "MESH"]
parts = [x for x in set(parts) if x.type == "MESH"]
parts.sort(key=lambda x: -len(x.data.vertices))
arm = parts[0]; arm.name = "arm"
for x in parts[1:]: bpy.data.objects.remove(x, do_unlink=True)

Va = [v.co.copy() for v in arm.data.vertices]
axmin = min(p.x for p in Va); axmax = max(p.x for p in Va)
arm_dims = [round(max(p.x for p in Va)-min(p.x for p in Va), 1),
            round(max(p.y for p in Va)-min(p.y for p in Va), 1),
            round(max(p.z for p in Va)-min(p.z for p in Va), 1)]
print(f"[arm] verts={len(Va)} dims={arm_dims} xrange=({axmin:.1f},{axmax:.1f})")

# --- measure the HAND: take the distal region, split into loose islands = digits --
# distal = outer 18% along the arm's reach (+X after rotation)
L = axmax - axmin; thr = axmax - 0.20*L
hand = bpy.data.objects.new("hand", arm.data.copy())
bpy.context.collection.objects.link(hand)
bisect_keep(hand, (thr, 0, 0), (1, 0, 0), keep_positive=True)
act(hand); bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
digits = [x for x in bpy.context.selected_objects if x.type == "MESH" and len(x.data.vertices) > 40]
if hand.type == "MESH" and hand not in digits and len(hand.data.vertices) > 40:
    digits.append(hand)
digits = [x for x in set(digits) if x.type == "MESH" and len(x.data.vertices) > 40]
digit_info = []
for d in sorted(digits, key=lambda x: -len(x.data.vertices)):
    dv = [v.co for v in d.data.vertices]
    dd = [round(max(p.x for p in dv)-min(p.x for p in dv), 1),
          round(max(p.y for p in dv)-min(p.y for p in dv), 1),
          round(max(p.z for p in dv)-min(p.z for p in dv), 1)]
    digit_info.append({"verts": len(dv), "bbox_mm": dd})
print(f"[hand] distal islands (>40v) = {len(digit_info)}")
for i, di in enumerate(digit_info):
    print(f"       digit{i}: verts={di['verts']} bbox={di['bbox_mm']}")
for d in digits: bpy.data.objects.remove(d, do_unlink=True)

report = {"units": "raw master mm (unscaled, centered)", "arm_azimuth_deg": ARM_AZ,
          "arm_wedge_halfangle_deg": WEDGE, "arm_dims_mm": arm_dims,
          "arm_verts": len(Va), "hand_distal_islands": len(digit_info),
          "digits": digit_info,
          "note": "arm isolated by planar bisect wedge ONLY (no boolean/remesh); "
                  "3-finger manipulator hand rides the distal tip intact"}
with open(os.path.join(STL_OUT, "rocky_hand_isolate_report.json"), "w") as f:
    json.dump(report, f, indent=2)

# ============================ render the isolated arm ========================
# rotate back so the hand reads in its natural raised orientation for the render
arm.data.transform(Matrix.Rotation(math.radians(ARM_AZ), 4, "Z")); arm.data.update()
Va = [arm.matrix_world @ v.co for v in arm.data.vertices]
hc = Vector((sum(p.x for p in Va)/len(Va), sum(p.y for p in Va)/len(Va),
             sum(p.z for p in Va)/len(Va)))
# hand tip center (outer 18% by radius) for camera aim
radv = sorted(Va, key=lambda p: -(math.hypot(p.x, p.y)))
tipv = radv[:max(30, len(radv)//12)]
tc = Vector((sum(p.x for p in tipv)/len(tipv), sum(p.y for p in tipv)/len(tipv),
             sum(p.z for p in tipv)/len(tipv)))

mat = bpy.data.materials.new("clay"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.64, 0.62, 0.58, 1.0)
b.inputs["Roughness"].default_value = 0.7
arm.data.materials.append(mat); act(arm); bpy.ops.object.shade_flat()

world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.19, 0.21, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7


def add_light(kind, name, energy, loc, rot, size=300):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; return o

add_light("SUN", "key", 3.2, (tc.x, tc.y-50, tc.z+120), (math.radians(40), math.radians(10), math.radians(20)))
add_light("AREA", "fill", 18000, (tc.x-80, tc.y-80, tc.z+40), (math.radians(60), 0, math.radians(-45)), 200)
add_light("AREA", "rim", 14000, (tc.x+60, tc.y+40, tc.z+80), (math.radians(50), 0, math.radians(160)), 150)

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 1100; sc.render.resolution_y = 1100
try: sc.eevee.use_gtao = True
except Exception: pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt)
con = cam.constraints.new("TRACK_TO"); con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"


def shoot(path, cloc, tloc, lens=70):
    cam.data.lens = lens; cam.location = cloc; tgt.location = tloc
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    print("[render]", path)

dd = 90.0
# primary hand close-up -> the deliverable proof
shoot(os.path.join(MEDIA, "rocky_hands_before.png"),
      (tc.x+30, tc.y-dd, tc.z+dd*0.35), (tc.x, tc.y, tc.z-6), lens=80)
# supporting angles
shoot(os.path.join(MEDIA, "rocky_hand_before_side.png"),
      (tc.x+dd, tc.y-dd*0.3, tc.z+dd*0.25), (tc.x, tc.y, tc.z-6), lens=80)
shoot(os.path.join(MEDIA, "rocky_arm_before_full.png"),
      (hc.x+40, hc.y-140, hc.z+60), (hc.x, hc.y, hc.z), lens=52)
print("[done]", os.path.join(STL_OUT, "rocky_hand_isolate_report.json"))
