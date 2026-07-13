#!/usr/bin/env python3
"""Close-up of the DISTAL ends (feet / manipulator hand) of the raw toy pieces in o3d
orientation, to check: are they flat, or fingered? Run: blender --background --python this.py"""
import bpy, os, math, json, mathutils
import numpy as np

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
RAW = "/home/mrqbit/Downloads/dbx-r/reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS"
OUT = "/home/mrqbit/Downloads/dbx-r/docs/build_plan/toyend"
data = json.load(open(os.path.join(SP, "toy_assembled_o3d.json")))
# distal pieces: leg1 hand = 1-C, feet = N-B
PIECES = {"1-C(hand)": "1-C", "2-B(foot)": "2-B", "3-B(foot)": "3-B", "4-B(foot)": "4-B", "5-B(foot)": "5-B"}


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
    b.inputs["Base Color"].default_value = (0.36, 0.33, 0.30, 1); b.inputs["Roughness"].default_value = 0.85
    return m


def setup():
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.06, 0.06, 0.07, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    for i, rot in enumerate([(55, 10, 35), (-60, 0, -130), (110, 0, 60)]):
        s = bpy.data.objects.new(f"l{i}", bpy.data.lights.new(f"l{i}", "SUN")); bpy.context.collection.objects.link(s)
        s.data.energy = [3.5, 2.5, 2.0][i]; s.rotation_euler = tuple(math.radians(a) for a in rot)
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 700; sc.render.resolution_y = 700
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"
    return cam


for label, nm in PIECES.items():
    clear(); mat = stone()
    o = imp(os.path.join(RAW, nm + ".stl")); o.matrix_world = M4(data[nm])
    o.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = np.array([[v.co[0], v.co[1], v.co[2]] for v in o.data.vertices])
    ctr = vs.mean(0); cov = np.cov((vs - ctr).T); w_, V = np.linalg.eigh(cov)
    la = mathutils.Vector(V[:, -1]).normalized()
    R = la.rotation_difference(mathutils.Vector((1, 0, 0))).to_matrix().to_4x4()
    o.matrix_world = R @ mathutils.Matrix.Translation(-mathutils.Vector(ctr))
    cam = setup()
    vs2 = np.array([(o.matrix_world @ v.co) for v in o.data.vertices])
    # focus on the DISTAL half (toe end = +X extreme). center camera on distal third.
    xmax = vs2[:, 0].max(); distal = vs2[vs2[:, 0] > xmax - (xmax - vs2[:, 0].min()) * 0.5]
    dctr = distal.mean(0); ext = (distal.max(0) - distal.min(0)).max() * 1.4
    cam.data.ortho_scale = ext; cam.data.clip_start = 1; cam.data.clip_end = ext * 12
    for j, (ang, suf) in enumerate([((0, -1, 0.3), "a"), ((0, -0.3, -1), "b")]):  # side, look-up-toe
        D = ext * 3
        cam.location = (dctr[0] + ang[0] * D, dctr[1] + ang[1] * D, dctr[2] + ang[2] * D)
        d = mathutils.Vector(dctr) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.render.filepath = f"{OUT}_{nm}_{suf}.png"
        bpy.ops.render.render(write_still=True)
    print(f"[toyend] {label}")
print("[toyend] done")
