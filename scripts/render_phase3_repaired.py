#!/usr/bin/env python3
"""Confirmation render for the Phase-3 mesh-repair (af_shells_v3): one repaired leg
solid (craggy stone preserved) + a wall cross-section of a repaired hollow, proving the
crag survived the topology repair. The VALIDATION TABLE is the deliverable; this is a
sanity picture only.
Run: blender --background --python scripts/render_phase3_repaired.py
"""
import bpy, os, math

ROOT = "/home/mrqbit/Downloads/dbx-r"
SRC = os.path.join(ROOT, "rocky/cad/stl_derived/af_shells_v3")
OUT = os.path.join(ROOT, "docs/build_plan/phase3_repaired.png")
LEG = 1


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for x in list(coll): coll.remove(x)


def imp(path):
    try: bpy.ops.wm.stl_import(filepath=path)
    except Exception: bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


def stone(color=(0.30, 0.27, 0.24, 1)):
    m = bpy.data.materials.new("stone"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = 0.92
    return m


def cut_material():
    return stone(color=(0.72, 0.32, 0.16, 1))  # warm face on the sectioned wall


clear()
smat = stone()

# --- LEFT: repaired leg1 solid (3 segments joined) ---
parts = []
for seg in ("coxa", "femur", "tibia"):
    f = os.path.join(SRC, f"leg{LEG}_{seg}_solid.stl")
    if os.path.exists(f):
        o = imp(f); o.data.materials.append(smat); parts.append(o)
bpy.ops.object.select_all(action="DESELECT")
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
legobj = bpy.context.active_object
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
legobj.location = (0, 70, 0)

# --- RIGHT: repaired hollow, bisected to expose the wall cross-section ---
h = imp(os.path.join(SRC, f"leg{LEG}_femur_hollow.stl"))
h.data.materials.append(smat)
h.data.materials.append(cut_material())
bpy.context.view_layer.objects.active = h
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
# cut across the long (X) axis so the camera (on +X) sees the annular 3 mm wall ring
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(1, 0, 0), use_fill=True,
                    clear_inner=True, clear_outer=False)
# the freshly-created cap faces stay selected -> give them the warm section material
h.active_material_index = 1
bpy.ops.object.material_slot_assign()
bpy.ops.object.mode_set(mode="OBJECT")
h.location = (60, -55, 0)

# --- camera + lights ---
bpy.ops.object.camera_add(location=(430, -5, 300), rotation=(math.radians(60), 0, math.radians(90)))
cam = bpy.context.active_object
bpy.context.scene.camera = cam
bpy.ops.object.light_add(type="SUN", location=(200, 200, 400))
bpy.context.active_object.data.energy = 4.0
bpy.ops.object.light_add(type="SUN", location=(-200, -100, 200))
bpy.context.active_object.data.energy = 2.0

# frame both objects
bpy.ops.object.select_all(action="SELECT")
cam.select_set(False)
for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    lt.select_set(False)
bpy.ops.view3d.camera_to_view_selected() if False else None

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in
    bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else sc.render.engine
sc.render.resolution_x = 1200
sc.render.resolution_y = 900
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
sc.render.filepath = OUT
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.render.render(write_still=True)
print("[render]", OUT)
