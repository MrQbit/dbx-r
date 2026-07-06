#!/usr/bin/env python3
"""Blender-headless processing of the official Rocky STL — preserves the real
geometry (clean bisect cuts, no voxel remesh) instead of the trimesh blobbing.

Run:  blender --background --python scripts/blender_rocky.py -- [master.stl] [out.png]

Stage 1 here: import the master, scale to the compact 272mm target, apply a stone
material + lighting, and render iso/front/top so we can confirm the shape reads as
movie Rocky before segmenting. Segmentation stages are added next.
"""
import sys
import os
import math

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ROOT = "/home/mrqbit/Downloads/dbx-r"
MASTER = argv[0] if argv else os.path.join(ROOT, "reference/stl/rocky_normalized.stl")
OUT = argv[1] if len(argv) > 1 else os.path.join(ROOT, "docs/media/rocky_blender.png")
TARGET_MM = 272.0   # compact thorax across (D-031)


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials):
        for b in list(block):
            block.remove(b)


def import_stl(path):
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)          # Blender 4.x native
    else:
        bpy.ops.import_mesh.stl(filepath=path)        # legacy addon
    return bpy.context.selected_objects[0]


def stone_material():
    m = bpy.data.materials.new("stone")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.32, 0.28, 0.24, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    return m


def main():
    clear()
    obj = import_stl(MASTER)
    # make it the sole active + selected single-user object (transform_apply needs this)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.make_single_user(object=True, obdata=True)
    # center on origin, scale so the widest XY extent = TARGET_MM
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.location = (0, 0, 0)
    dims = obj.dimensions
    span = max(dims.x, dims.y)
    s = TARGET_MM / span if span else 1.0
    obj.scale = (s, s, s)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(stone_material())
    # smooth-ish shading but keep the craggy faces
    bpy.ops.object.shade_flat()

    dims = obj.dimensions
    print(f"[blender] {os.path.basename(MASTER)} scaled x{s:.3f} -> dims {tuple(round(d,1) for d in dims)} mm")

    # world + light
    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    bpy.context.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.film_transparent = False

    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    cam_data.type = "ORTHO"
    r = max(obj.dimensions) * 1.25
    cam_data.ortho_scale = max(obj.dimensions) * 1.15   # fill the frame

    # empty at center to aim the camera
    tgt = bpy.data.objects.new("tgt", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = (0, 0, obj.dimensions.z / 2)
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    views = {"iso": (r, -r, r), "front": (0, -r * 1.6, r * 0.3), "top": (0, 0, r * 1.8)}
    for name, pos in views.items():
        cam.location = (pos[0], pos[1], pos[2] + obj.dimensions.z / 2)
        scene.render.filepath = OUT.replace(".png", f"_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[blender] wrote {scene.render.filepath}")


main()
