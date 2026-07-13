#!/usr/bin/env python3
"""Solid stone render of the final shell legs (coxa+femur+tibia) to confirm the craggy
detail survived the voxel/EDT hollow. Run: blender --background --python this.py"""
import bpy, os, math, mathutils

D = "/home/mrqbit/Downloads/dbx-r/rocky/cad/stl_derived/shells_final"
OUT = "/home/mrqbit/Downloads/dbx-r/docs/build_plan/shells_final_solid"


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(c): c.remove(x)


def imp(p):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=p)
    else: bpy.ops.import_mesh.stl(filepath=p)
    return bpy.context.selected_objects[0]


def stone():
    m = bpy.data.materials.new("s"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.32, 0.29, 0.26, 1); b.inputs["Roughness"].default_value = 0.9
    return m


def render_leg(leg, suffix):
    clear(); mat = stone(); objs = []
    for seg in ("coxa", "femur", "tibia"):
        p = os.path.join(D, f"leg{leg}_{seg}_solid.stl")
        if os.path.exists(p):
            o = imp(p); o.data.materials.append(mat); objs.append(o)
    if not objs: return
    mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
    for o in objs:
        for c in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(c)
            for i in range(3): mn[i] = min(mn[i], wc[i]); mx[i] = max(mx[i], wc[i])
    ctr = (mn + mx)/2; ext = max((mx-mn)[i] for i in range(3))*1.25
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.05, 0.06, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
    key = bpy.data.objects.new("k", bpy.data.lights.new("k", "SUN")); bpy.context.collection.objects.link(key)
    key.data.energy = 4.5; key.rotation_euler = (math.radians(52), math.radians(8), math.radians(40))
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1500; sc.render.resolution_y = 750
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"; cam.data.ortho_scale = ext; cam.data.clip_start = 1; cam.data.clip_end = ext*8
    r = ext*2
    cam.location = (ctr.x, ctr.y - r*0.8, ctr.z + r*0.5)
    d = ctr - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = OUT + suffix + ".png"; bpy.ops.render.render(write_still=True)
    print(f"[sf] leg{leg} -> {sc.render.filepath}")


render_leg(1, "_leg1")
render_leg(2, "_leg2")
