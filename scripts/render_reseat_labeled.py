#!/usr/bin/env python3
"""Load the reseated canonical (toy_assembled_real.json) transforms onto the native pieces,
color per leg, add a floating leg-number label, render front+top. Identifies each leg
unambiguously so we can pin the 'orange leg foot' issue.
Run: blender --background --python scripts/render_reseat_labeled.py
"""
import bpy, os, math, json, mathutils

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
NAT = os.path.join(SP, "dejoint_work/native_stl")
JSON = os.path.join(SP, "toy_assembled_real.json")
OUT = "/home/mrqbit/Downloads/dbx-r/docs/build_plan/reseat_labeled"

COL = {"1": (0.90, 0.50, 0.10, 1), "2": (0.80, 0.20, 0.20, 1), "3": (0.20, 0.65, 0.30, 1),
       "4": (0.25, 0.45, 0.85, 1), "5": (0.62, 0.35, 0.75, 1), "t": (0.55, 0.55, 0.57, 1)}
LEGNAME = {"1": "1 (orange/manip)", "2": "2 (red)", "3": "3 (green)", "4": "4 (blue)", "5": "5 (purple)"}


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for x in list(c): c.remove(x)


def imp(path):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=path)
    else: bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


clear()
data = json.load(open(JSON))
# find the per-piece transforms (support a couple of shapes)
pieces = data.get("pieces") or data.get("transforms") or data
objs = []
label_pts = {}
for name in ["torso", "1-A", "1-C", "2-A", "2-B", "3-A", "3-B", "4-A", "4-B", "5-A", "5-B"]:
    p = os.path.join(NAT, name + ".stl")
    if not os.path.exists(p):
        continue
    o = imp(p); o.name = name
    ent = pieces.get(name) if isinstance(pieces, dict) else None
    M = None
    if isinstance(ent, dict):
        M = ent.get("world") or ent.get("matrix") or ent.get("world_matrix") or ent.get("M")
    elif isinstance(ent, list):
        M = ent
    if M:
        o.matrix_world = mathutils.Matrix([[M[r][c] for c in range(4)] for r in range(4)]) if isinstance(M[0], list) else mathutils.Matrix([M[i*4:i*4+4] for i in range(4)])
    key = "t" if name.startswith("t") else name[0]
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = COL[key]
    o.data.materials.append(m)
    objs.append(o)
    if not name.startswith("t") and name.endswith("B") or name == "1-C":
        label_pts[name[0]] = o  # distal piece = where the foot/hand is

# bounds
mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        wc = o.matrix_world @ mathutils.Vector(c)
        for i in range(3): mn[i] = min(mn[i], wc[i]); mx[i] = max(mx[i], wc[i])
ctr = (mn + mx) / 2; ext = max((mx - mn)[i] for i in range(3)) * 1.25

# leg-number text labels at each distal piece
for leg, o in label_pts.items():
    cur = bpy.data.curves.new("t"+leg, "FONT"); cur.body = LEGNAME[leg]; cur.size = ext*0.05
    t = bpy.data.objects.new("lbl"+leg, cur); bpy.context.collection.objects.link(t)
    t.location = o.matrix_world.translation + mathutils.Vector((0, 0, ext*0.06))
    tm = bpy.data.materials.new("tl"+leg); tm.use_nodes = True
    tm.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1,1,1,1)
    tm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3
    cur.materials.append(tm)

w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.04, 0.05, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); bpy.context.collection.objects.link(sun)
sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1500; sc.render.resolution_y = 1500
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
sc.camera = cam; cam.data.type = "ORTHO"; cam.data.ortho_scale = ext; cam.data.clip_start = 1; cam.data.clip_end = ext*8
D = ext*2
for suf, loc, rot in [("_top", (ctr.x, ctr.y, ctr.z+D), (0, 0, 0)),
                      ("_front", (ctr.x, ctr.y-D, ctr.z), (math.radians(90), 0, 0))]:
    cam.location = loc; cam.rotation_euler = rot
    sc.render.filepath = OUT + suf + ".png"; bpy.ops.render.render(write_still=True)
    print("[lbl] wrote", sc.render.filepath)
