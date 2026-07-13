"""Render leg5 v2 snap-fit finger gloves for operator review.
Panels: full-leg solid (SIDE/TOP/3Q), grip close-up solid + ghost, open/closed
articulation, and TWO cross-sections showing the snap-fit cavity + wall thickness."""
import bpy, bmesh, json, math
import numpy as np
from mathutils import Vector, Matrix
SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
CD = SP + "/leg5_finger_covers"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1000; sc.render.resolution_y = 1000

def imp(p):
    b = set(bpy.data.objects)
    try: bpy.ops.wm.stl_import(filepath=p)
    except Exception: bpy.ops.import_mesh.stl(filepath=p)
    o = list(set(bpy.data.objects) - b)[0]
    if o.data.users > 1: o.data = o.data.copy()
    return o

def mat(name, col, rough=0.9, alpha=1.0, emis=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    if alpha < 1.0: m.blend_method = 'BLEND'
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Emission Color"].default_value = (*col, 1)
    b.inputs["Emission Strength"].default_value = emis
    return m

stone   = mat("stone", (0.60, 0.58, 0.55), 0.92)
stone_c = mat("stone_c", (0.66, 0.55, 0.45), 0.9)
stone_g = mat("stone_g", (0.66, 0.60, 0.52), 0.6, alpha=0.18)
cover_g = mat("cover_g", (0.70, 0.58, 0.42), 0.7, alpha=0.35)
sect_m  = mat("sect", (0.72, 0.50, 0.35), 0.8)
toe_mat = mat("toe", (0.55, 0.55, 0.50), 0.9)
colA = mat("colA", (0.20, 0.55, 0.95), 0.5, emis=0.5)
colB = mat("colB", (0.20, 0.85, 0.35), 0.5, emis=0.5)
colT = mat("colT", (0.98, 0.55, 0.12), 0.5, emis=0.5)

OrigB = imp(SP + "/leg5_aligned_5B.stl"); OrigB.data.materials.append(stone)
A = imp(SP + "/leg5_enclosed_5A.stl"); A.data.materials.append(stone)
B = imp(SP + "/leg5_enclosed_5B.stl"); B.data.materials.append(stone)
TO = imp(SP + "/leg5_enclosed_toecover.stl"); TO.data.materials.append(toe_mat)
fA = imp(CD + "/_finger_primA.stl"); fA.data.materials.append(colA)
fB = imp(CD + "/_finger_primB.stl"); fB.data.materials.append(colB)
fTo = imp(CD + "/_finger_thumb_open.stl"); fTo.data.materials.append(colT)
fTc = imp(CD + "/_finger_thumb_closed.stl"); fTc.data.materials.append(colT)
cA = imp(CD + "/prim_cover_A.stl")
cB = imp(CD + "/prim_cover_B.stl")
cTo = imp(CD + "/thumb_cover.stl")
cTc = imp(CD + "/_thumb_cover_closed.stl")
covers = [cA, cB, cTo, cTc]
for c in covers: c.data.materials.append(stone_c)
shell = [A, B, TO]
fingers = [fA, fB, fTo, fTc]

# ---- pre-built section meshes (cut with manifold at build time) ----
ax = Vector((0.9272, 0.3664, 0.0779)); root = Vector((369, 7, 0))
mvec = ax.cross(Vector((0, 0, 1))).normalized()
secA = imp(CD + "/_sect_prim.stl"); secA.data.materials.append(sect_m)
secT = imp(CD + "/_sect_thumb.stl"); secT.data.materials.append(sect_m)

# lights + world + camera
bpy.ops.object.light_add(type='SUN', location=(300, -300, 500)); bpy.context.object.data.energy = 3.4
bpy.ops.object.light_add(type='SUN', location=(-200, 300, 200)); bpy.context.object.data.energy = 1.5
bpy.ops.object.light_add(type='SUN', location=(150, 200, -300)); bpy.context.object.data.energy = 1.0
bpy.ops.object.light_add(type='SUN', location=(380, -500, 50)); bpy.context.object.data.energy = 1.2
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.08, 1)
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam); sc.camera = cam
cam_d.type = 'ORTHO'

def look(frm, center, scale):
    cam_d.ortho_scale = scale
    cam.location = Vector(frm)
    cam.rotation_euler = (Vector(frm) - Vector(center)).to_track_quat('Z', 'Y').to_euler()

ALL = shell + fingers + covers + [secA, secT, OrigB]
def show(objs):
    for o in ALL: o.hide_render = o not in objs
def setmat(o, m): o.data.materials[0] = m
def render(fn):
    sc.render.filepath = fn; bpy.ops.render.render(write_still=True)

FULLC = (175, 0, -5)
GC = (382, -14, 0); GCAM = (470, -360, 470); GSC = 185

# 1) full leg solid
for o in shell: setmat(o, stone if o != TO else toe_mat)
for c in covers: setmat(c, stone_c)
show(shell + [cA, cB, cTo])
for nm, frm in [("SIDE", (175, -760, 20)), ("TOP", (175, 40, 760)), ("3Q", (560, -560, 360))]:
    look(frm, FULLC, 400); render(SP + f"/_fc5_full_{nm}.png")

# 2) grip close-up solid
show(shell + [cA, cB, cTo])
look(GCAM, GC, GSC); render(SP + "/_fc5_closeup_solid.png")

# 3) ghost: coloured fingers inside translucent gloves
for o in shell: setmat(o, stone_g)
for c in covers: setmat(c, cover_g)
show(shell + [fA, fB, fTo] + [cA, cB, cTo])
look(GCAM, GC, GSC); render(SP + "/_fc5_closeup_ghost.png")

# 4) articulation open/closed
for o in shell: setmat(o, stone_g)
for c in covers: setmat(c, stone_c)
show([fA, fB, fTo, cA, cB, cTo])
look(GCAM, GC, GSC); render(SP + "/_fc5_open.png")
show([fA, fB, fTc, cA, cB, cTc])
look(GCAM, GC, GSC); render(SP + "/_fc5_closed.png")

# 4b) COMPARISON: original toy 2-B foot tip vs our covered tip (same view dir)
for o in shell: setmat(o, stone if o != TO else toe_mat)
show([OrigB])
look((315 + 180, -170, 130), (312, 0, -4), 110)
render(SP + "/_fc5_compare_orig.png")
show(shell + [cA, cB, cTo])
look((358 + 180, -170, 130), (360, 0, -2), 138)
render(SP + "/_fc5_compare_ours.png")

# 5) sections: cavity + wall visible, finger shown inside
show([secA, fA])
look((root + mvec * 220 + Vector((25, 0, 70))), (391, 1, 2), 70)
render(SP + "/_fc5_section_prim.png")
show([secT, fTo])
look((366, -35, 220), (366, -35, 0), 75)
render(SP + "/_fc5_section_thumb.png")
print("RENDER_DONE")
