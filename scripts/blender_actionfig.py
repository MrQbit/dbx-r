#!/usr/bin/env python3
"""Render the OFFICIAL action-figure limb pieces (the 11 limb STLs + torso) laid out
in a grid — the correct, complete, ready-to-print source for the ROCKY-5 shells.
Run: blender --background --python scripts/blender_actionfig.py
"""
import bpy, os, math, glob

ROOT = "/home/mrqbit/Downloads/dbx-r"
SRC = os.path.join(ROOT, "reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS")
OUT = os.path.join(ROOT, "docs/media/rocky_actionfig_pieces")


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for b in (bpy.data.meshes, bpy.data.materials):
        for x in list(b): b.remove(x)


def imp(path):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=path)
    else: bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


def stone():
    m = bpy.data.materials.new("s"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.34, 0.30, 0.26, 1)
    b.inputs["Roughness"].default_value = 0.82
    return m


clear()
files = sorted(glob.glob(os.path.join(SRC, "*.stl")))
print(f"[actionfig] {len(files)} pieces:", [os.path.basename(f) for f in files])
mat = stone()
cols = 4
pitch = 120.0
objs = []
for i, f in enumerate(files):
    o = imp(f)
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    d = max(o.dimensions) or 1.0
    o.scale = (90.0 / d,) * 3
    bpy.ops.object.transform_apply(scale=True)
    r, c = divmod(i, cols)
    o.location = (c * pitch, -r * pitch, 0)
    o.data.materials.append(mat)
    o.name = os.path.basename(f).replace(".stl", "")
    objs.append(o)

w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
bpy.context.collection.objects.link(sun); sun.data.energy = 3.5
sun.rotation_euler = (math.radians(55), 0, math.radians(35))

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1400; sc.render.resolution_y = 1000
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
sc.camera = cam; cam.data.type = "ORTHO"
allv = [o.location for o in objs]
cx = sum(v[0] for v in allv) / len(allv); cy = sum(v[1] for v in allv) / len(allv)
cam.data.ortho_scale = pitch * cols * 1.05
cam.location = (cx, cy, 600); cam.rotation_euler = (0, 0, 0)
sc.render.filepath = OUT + "_top.png"
bpy.ops.render.render(write_still=True)
print("[actionfig] wrote", sc.render.filepath)
