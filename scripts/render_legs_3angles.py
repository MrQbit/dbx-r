#!/usr/bin/env python3
"""Each leg assembled individually from the RAW pieces (with pegs, PRE peg-trim) in their
o3d-validated orientation, rendered from 3 rotations about the long leg axis.
Run: blender --background --python scripts/render_legs_3angles.py"""
import bpy, os, math, json, mathutils
import numpy as np

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
RAW = "/home/mrqbit/Downloads/dbx-r/reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS"
JSON = os.path.join(SP, "toy_assembled_o3d.json")
OUT = "/home/mrqbit/Downloads/dbx-r/docs/build_plan/leg3ang"

LEGPIECES = {1: ["1-A", "1-C"], 2: ["2-A", "2-B"], 3: ["3-A", "3-B"],
             4: ["4-A", "4-B"], 5: ["5-A", "5-B"]}
data = json.load(open(JSON))


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(c): c.remove(x)


def imp(p):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=p)
    else: bpy.ops.import_mesh.stl(filepath=p)
    return bpy.context.selected_objects[0]


def M4(m):
    return mathutils.Matrix([[m[r][c] for c in range(4)] for r in range(4)])


def stone():
    m = bpy.data.materials.new("s"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.34, 0.31, 0.28, 1); b.inputs["Roughness"].default_value = 0.85
    return m


def setup():
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.06, 0.06, 0.07, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.15
    key = bpy.data.objects.new("k", bpy.data.lights.new("k", "SUN")); bpy.context.collection.objects.link(key)
    key.data.energy = 3.5; key.rotation_euler = (math.radians(55), math.radians(10), math.radians(35))
    fill1 = bpy.data.objects.new("f1", bpy.data.lights.new("f1", "SUN")); bpy.context.collection.objects.link(fill1)
    fill1.data.energy = 2.5; fill1.rotation_euler = (math.radians(-70), 0, math.radians(-140))
    fill2 = bpy.data.objects.new("f2", bpy.data.lights.new("f2", "SUN")); bpy.context.collection.objects.link(fill2)
    fill2.data.energy = 2.0; fill2.rotation_euler = (math.radians(120), 0, math.radians(60))
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1000; sc.render.resolution_y = 620
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"
    return cam


for leg, names in LEGPIECES.items():
    clear(); mat = stone(); objs = []
    for nm in names:
        o = imp(os.path.join(RAW, nm + ".stl")); o.matrix_world = M4(data[nm]); o.data.materials.append(mat); objs.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join()
    leg_obj = bpy.context.active_object
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)  # bake -> verts are world coords
    vs = np.array([[v.co[0], v.co[1], v.co[2]] for v in leg_obj.data.vertices])
    ctr = vs.mean(0); cov = np.cov((vs - ctr).T); w_, V = np.linalg.eigh(cov)
    longax = mathutils.Vector(V[:, -1]).normalized()
    # center at origin then rotate longax -> world X
    R = longax.rotation_difference(mathutils.Vector((1, 0, 0))).to_matrix().to_4x4()
    leg_obj.matrix_world = R @ mathutils.Matrix.Translation(-mathutils.Vector(ctr))
    cam = setup()
    # bounds
    vs2 = np.array([(leg_obj.matrix_world @ v.co) for v in leg_obj.data.vertices])
    ext = (vs2.max(0) - vs2.min(0)).max() * 1.15
    cam.data.ortho_scale = ext * 1.05; cam.data.clip_start = 1; cam.data.clip_end = ext * 12
    D = ext * 4
    for r in (0, 120, 240):
        ar = math.radians(r)
        # orbit camera around the long (X) axis; leg stays fixed & centered
        cam.location = (0, -D * math.cos(ar), -D * math.sin(ar))
        d = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.render.filepath = f"{OUT}_leg{leg}_{r}.png"
        bpy.ops.render.render(write_still=True)
        print(f"[3ang] leg{leg} roll{r}")
print("[3ang] done")
