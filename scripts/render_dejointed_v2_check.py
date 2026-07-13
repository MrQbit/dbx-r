#!/usr/bin/env python3
"""Load the dejointed_v2 segments AS EXPORTED (world coords, x6) and render labelled
top+side+iso so we can spot any piece flipped vs the canonical toy_assembled orientation.
Run: blender --background --python scripts/render_dejointed_v2_check.py
"""
import bpy, os, math, glob, mathutils

ROOT = "/home/mrqbit/Downloads/dbx-r"
SRC = os.path.join(ROOT, "rocky/cad/stl_derived/dejointed_v2")
OUT = os.path.join(ROOT, "docs/build_plan/dejointed_v2_orient_check")

# per-leg color so each limb is distinguishable
COL = {
    "1": (0.85, 0.55, 0.15, 1), "2": (0.80, 0.20, 0.20, 1), "3": (0.20, 0.65, 0.30, 1),
    "4": (0.25, 0.45, 0.85, 1), "5": (0.65, 0.30, 0.75, 1), "t": (0.6, 0.6, 0.62, 1),
}


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(c): c.remove(x)


def imp(path):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=path)
    else: bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


clear()
objs = []
for f in sorted(glob.glob(os.path.join(SRC, "*.stl"))):
    name = os.path.basename(f).split("_")[0]  # 1-A, torso, ...
    o = imp(f)
    o.name = name
    key = "t" if name.startswith("t") else name[0]
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = COL.get(key, (0.7,)*3+(1,))
    o.data.materials.append(m)
    objs.append((name, o))
print("[dv2] loaded:", [n for n, _ in objs])

w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
bpy.context.collection.objects.link(sun); sun.data.energy = 3.5
sun.rotation_euler = (math.radians(55), 0, math.radians(35))

# center + extent from actual world-space geometry bounds (not object origins)
mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
for _, o in objs:
    for corner in o.bound_box:
        wc = o.matrix_world @ mathutils.Vector(corner)
        for i in range(3):
            mn[i] = min(mn[i], wc[i]); mx[i] = max(mx[i], wc[i])
ctr = (mn + mx) / 2
extent = max((mx - mn)[i] for i in range(3)) * 1.15
print(f"[dv2] bounds min={tuple(round(v) for v in mn)} max={tuple(round(v) for v in mx)} extent={extent:.0f}")

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1400; sc.render.resolution_y = 1400
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
sc.camera = cam; cam.data.type = "ORTHO"; cam.data.ortho_scale = extent
cam.data.clip_start = 1.0; cam.data.clip_end = extent * 8

D = extent * 2
views = {
    "_top": ((ctr.x, ctr.y, ctr.z + D), (0, 0, 0)),
    "_front": ((ctr.x, ctr.y - D, ctr.z), (math.radians(90), 0, 0)),
}
for suf, (loc, rot) in views.items():
    cam.location = loc; cam.rotation_euler = rot
    sc.render.filepath = OUT + suf + ".png"
    bpy.ops.render.render(write_still=True)
    print("[dv2] wrote", sc.render.filepath)
