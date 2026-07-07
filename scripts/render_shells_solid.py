#!/usr/bin/env python3
"""Solid opaque STONE render of the 5 D-043 uniform-scaled leg shells (coxa+femur+tibia),
so the operator can judge the real aesthetic (the clearance render was semi-transparent).
Run: blender --background --python scripts/render_shells_solid.py
"""
import bpy, os, math, glob

ROOT = "/home/mrqbit/Downloads/dbx-r"
SRC = os.path.join(ROOT, "rocky/cad/stl_derived/af_shells")
OUT = os.path.join(ROOT, "docs/build_plan/legs_shells_solid")


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(coll): coll.remove(x)


def imp(path):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=path)
    else: bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


def stone():
    m = bpy.data.materials.new("stone"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
    b.inputs["Roughness"].default_value = 0.9
    # subtle noise bump for craggy read
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 18
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


clear()
mat = stone()
# each leg = its 3 solid shell segments, already positioned at the chassis stations.
rowpitch = 130.0
legs = []
for li in range(1, 6):
    parts = []
    for seg in ("coxa", "femur", "tibia"):
        f = os.path.join(SRC, f"leg{li}_{seg}_solid.stl")
        if os.path.exists(f):
            o = imp(f); o.data.materials.append(mat); parts.append(o)
    if not parts:
        continue
    # join the 3 segments into one leg object
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    leg = bpy.context.active_object
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    leg.location = (0, -(li - 1) * rowpitch, 0)
    leg.rotation_euler = (0, 0, 0)
    leg.name = f"leg{li}"
    legs.append(leg)
print(f"[solid] assembled {len(legs)} legs")

# lighting + world
w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.05, 0.06, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
key = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
bpy.context.collection.objects.link(key); key.data.energy = 4.0
key.rotation_euler = (math.radians(50), math.radians(10), math.radians(40))
rim = bpy.data.objects.new("rim", bpy.data.lights.new("rim", "SUN"))
bpy.context.collection.objects.link(rim); rim.data.energy = 2.0
rim.rotation_euler = (math.radians(115), 0, math.radians(-120))

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 1500; sc.render.resolution_y = 1250
sc.render.film_transparent = False
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.collection.objects.link(cam); sc.camera = cam
ys = [o.location[1] for o in legs]
cy = (max(ys) + min(ys)) / 2 if ys else 0
span = (max(ys) - min(ys)) if ys else 500
# 3/4 side perspective — look along the legs from front-side-above so craggy flanks show
cam.data.type = "PERSP"; cam.data.lens = 55
import mathutils
target = mathutils.Vector((120, cy, 0))
cam.location = (620, cy - span * 0.55, 380)
d = target - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.resolution_x = 1600; sc.render.resolution_y = 1300
sc.render.filepath = OUT + ".png"
bpy.ops.render.render(write_still=True)
print("[solid] wrote", sc.render.filepath)
