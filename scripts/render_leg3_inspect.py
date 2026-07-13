#!/usr/bin/env python3
"""Isolate leg 3 (3-A upper + 3-B end piece) in its v2 assembled transforms and render
from many angles, plus each piece alone, so we can diagnose the 'large crease/gap'.
Run: blender --background --python scripts/render_leg3_inspect.py
"""
import bpy, os, math, json, mathutils

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
NAT = os.path.join(SP, "dejoint_work/native_stl")
JSON = os.path.join(SP, "toy_assembled_real_v2.json")
OUTDIR = "/home/mrqbit/Downloads/dbx-r/docs/build_plan"


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(c): c.remove(x)


def imp(path):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=path)
    else: bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


def mat(rgb):
    m = bpy.data.materials.new("m"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    return m


def M4(entry):
    Mrows = (entry.get("world_matrix_4x4") or entry.get("world") or entry.get("matrix")
             or entry.get("world_matrix") or entry.get("M"))
    if isinstance(Mrows[0], list):
        return mathutils.Matrix([[Mrows[r][c] for c in range(4)] for r in range(4)])
    return mathutils.Matrix([Mrows[i*4:i*4+4] for i in range(4)])


data = json.load(open(JSON)); pieces = data["pieces"]


def setup_world_cam():
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.05, 0.06, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    key = bpy.data.objects.new("k", bpy.data.lights.new("k", "SUN")); bpy.context.collection.objects.link(key)
    key.data.energy = 4; key.rotation_euler = (math.radians(50), 0, math.radians(40))
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", "SUN")); bpy.context.collection.objects.link(fill)
    fill.data.energy = 1.5; fill.rotation_euler = (math.radians(110), 0, math.radians(200))
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 700; sc.render.resolution_y = 700
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"
    return cam


def bounds(objs):
    mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
    for o in objs:
        for c in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(c)
            for i in range(3): mn[i] = min(mn[i], wc[i]); mx[i] = max(mx[i], wc[i])
    return mn, mx


def render_orbit(objs, prefix, angles):
    cam = setup_world_cam()
    mn, mx = bounds(objs); ctr = (mn + mx) / 2; ext = max((mx - mn)[i] for i in range(3)) * 1.3
    cam.data.ortho_scale = ext; cam.data.clip_start = 1; cam.data.clip_end = ext * 12
    sc = bpy.context.scene
    for name, (az, el) in angles.items():
        r = ext * 3
        cam.location = (ctr.x + r*math.cos(math.radians(el))*math.sin(math.radians(az)),
                        ctr.y - r*math.cos(math.radians(el))*math.cos(math.radians(az)),
                        ctr.z + r*math.sin(math.radians(el)))
        d = ctr - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUTDIR, f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[leg3] {prefix}_{name}")


ANGLES = {"front": (0, 10), "right": (90, 10), "back": (180, 10), "left": (270, 10),
          "top": (0, 85), "iso": (45, 30)}

# --- assembled leg3 (3-A green, 3-B teal) ---
clear()
a = imp(os.path.join(NAT, "3-A.stl")); a.matrix_world = M4(pieces["3-A"]); a.data.materials.append(mat((0.20, 0.62, 0.30)))
b = imp(os.path.join(NAT, "3-B.stl")); b.matrix_world = M4(pieces["3-B"]); b.data.materials.append(mat((0.15, 0.55, 0.62)))
# gap measurement between 3-A distal and 3-B proximal
import numpy as np
va = np.array([(a.matrix_world @ v.co) for v in a.data.vertices]); vb = np.array([(b.matrix_world @ v.co) for v in b.data.vertices])
# min distance between the two piece surfaces (sampled)
from mathutils.kdtree import KDTree
kt = KDTree(len(vb))
for i, v in enumerate(vb): kt.insert(v, i)
kt.balance()
gaps = [kt.find(mathutils.Vector(v))[2] for v in va[::10]]
print(f"[leg3] 3A<->3B min surface gap ~ {min(gaps):.1f} mm ; median {sorted(gaps)[len(gaps)//2]:.1f}")
render_orbit([a, b], "leg3_asm", ANGLES)

# --- 3-A alone ---
clear()
a = imp(os.path.join(NAT, "3-A.stl")); a.matrix_world = M4(pieces["3-A"]); a.data.materials.append(mat((0.20, 0.62, 0.30)))
render_orbit([a], "leg3_A", {"front": (0, 10), "right": (90, 10), "iso": (45, 30)})

# --- 3-B alone (the end piece) ---
clear()
b = imp(os.path.join(NAT, "3-B.stl")); b.matrix_world = M4(pieces["3-B"]); b.data.materials.append(mat((0.15, 0.55, 0.62)))
render_orbit([b], "leg3_B", {"front": (0, 10), "right": (90, 10), "back": (180, 10), "iso": (45, 30)})
print("[leg3] done")
