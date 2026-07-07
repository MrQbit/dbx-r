#!/usr/bin/env python3
"""TASK 3 — render docs/build_plan/legs_with_shells.png : the 5 action-figure leg
SHELLS (N-A femur + N-B tibia, coordinator mapping), each a semi-transparent stone
clamshell wrapping the SAME locked ROCKY-5 chassis (frame + hip-cluster QDD + knee
driveshaft + inline roll servo + 2+1 grip hand ghosted inside), at neutral, iso.
Per-joint motion-clearance verdicts (from the trimesh sweep) are baked on by PIL.

Run: blender --background --python scripts/blender_actionfig_render.py
"""
import os, math, json
import bpy
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
BP = os.path.join(ROOT, "docs/build_plan")
SH = os.path.join(ROOT, "rocky/cad/stl_derived/af_shells")
PITCH = 150.0


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for b in list(c):
            try: c.remove(b)
            except Exception: pass


def imp(p):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=p)
    else: bpy.ops.import_mesh.stl(filepath=p)
    return bpy.context.selected_objects[0]


def act(o):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o


def stone(alpha):
    m = bpy.data.materials.new("stone"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.52, 0.47, 0.40, 1); b.inputs["Roughness"].default_value = 0.82
    b.inputs["Alpha"].default_value = alpha
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 16.0; tex.inputs["Detail"].default_value = 9.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 1.4
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    m.blend_method = "BLEND"; m.show_transparent_back = True
    return m


def solid(col, metal=0.0):
    m = bpy.data.materials.new("s"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = 0.45
    b.inputs["Metallic"].default_value = metal
    return m


clear()
sweep = json.load(open(os.path.join(SH, "clearance_sweep.json")))
SHELLMAT = stone(0.52)
FRM = solid((0.55, 0.57, 0.62)); SRV = solid((0.92, 0.52, 0.12), 0.3); HND = solid((0.22, 0.72, 0.34))
allobj = []; allshell = []
for k in range(5):
    N = k + 1
    yoff = (2 - k) * PITCH
    for part, mat in (("frame", FRM), ("servos", SRV), ("hand", HND)):
        g = imp(os.path.join(BP, f"leg_chassis_neutral_{part}.stl"))
        g.data.transform(Matrix.Translation(Vector((0, yoff, 0)))); g.data.update()
        g.data.materials.append(mat); allobj.append(g)
    for seg in ("coxa", "femur", "tibia"):
        s = imp(os.path.join(SH, f"leg{N}_{seg}_solid.stl")); s.name = f"leg{N}_{seg}"
        s.data.transform(Matrix.Translation(Vector((0, yoff, 0)))); s.data.update()
        s.data.materials.append(SHELLMAT); act(s); bpy.ops.object.shade_flat()
        allobj.append(s); allshell.append((N, s, yoff))

# scene bounds
Vall = [o.matrix_world @ v.co for o in allobj for v in o.data.vertices]
xs = [p.x for p in Vall]; ys = [p.y for p in Vall]; zs = [p.z for p in Vall]
cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2; cz = (min(zs) + max(zs)) / 2
zmin = min(zs)
for o in allobj:
    o.location.z += -zmin
cz += -zmin

bpy.ops.mesh.primitive_plane_add(size=6000, location=(cx, cy, 0))
g = bpy.context.active_object; gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.09, 0.11, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
g.data.materials.append(gm)
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.85


def light(kind, name, energy, loc, rot, size=1200):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc; o.rotation_euler = rot
    return o


span = max(max(xs) - min(xs), max(ys) - min(ys))
light("SUN", "key", 2.6, (cx, cy, 2000), (math.radians(32), math.radians(8), math.radians(28)))
light("AREA", "fill", 260000, (cx - span, cy - span * 0.5, span), (math.radians(55), 0, math.radians(-40)), 1800)
light("AREA", "rim", 160000, (cx + span * 0.6, cy + span, span), (math.radians(60), 0, math.radians(150)), 1800)

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 1450; sc.render.resolution_y = 2000
try: sc.eevee.use_gtao = True; sc.eevee.use_soft_shadows = True; sc.eevee.taa_render_samples = 64
except Exception: pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt); tgt.location = (cx, cy, cz)
con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_X"
cam.data.type = "ORTHO"; cam.data.ortho_scale = (max(ys) - min(ys)) * 1.08
cam.data.clip_start = 1; cam.data.clip_end = 9000
cam.location = (cx - span * 0.22, cy, cz + span * 1.5)

from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
RX, RY = sc.render.resolution_x, sc.render.resolution_y
label_px = []
for N, s, yoff in [(n, s, y) for (n, s, y) in allshell if s.name.endswith("coxa")]:
    Vw = [s.matrix_world @ v.co for v in s.data.vertices]
    hip = min(Vw, key=lambda p: p.x)
    co = world_to_camera_view(sc, cam, hip)
    label_px.append({"leg": N, "px": round(co.x * RX), "py": round((1 - co.y) * RY)})
json.dump({"label_px": label_px, "sweep": sweep}, open(os.path.join(SH, "render_labels.json"), "w"), indent=2)

sc.render.filepath = os.path.join(BP, "legs_with_shells.png")
bpy.ops.render.render(write_still=True)
print("RENDER_DONE", sc.render.filepath)
