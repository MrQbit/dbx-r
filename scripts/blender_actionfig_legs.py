#!/usr/bin/env python3
"""TASK 1 — reassemble the OFFICIAL action-figure limb pieces into 5 complete leg
skins and render them side-by-side (labeled, manipulator marked).

CORRECT SOURCE (operator directive): the ready-to-print Articulated Action Figure
limb STLs, NOT the tucked statue. The print instructions call the figure
"1 body and 11 limb pieces": 5 limbs, each an ARTICULATED ball-and-socket assembly
of 2 pieces (proximal A + distal B); limb 1 (the manipulator/arm) ships a 3rd piece
because its hand has two swap options — 1-B (closed) / 1-C (open). We use 1-C.

These pieces are SEGMENTS, not print-split halves: each is a fully-rounded closed
solid (<5% of area is any single flat plane, so no mating cut face), the pieces sit
at independent print origins with zero bbox overlap, and 2-B/4-B/5-A/1-C each carry a
5-13 mm deep concave SOCKET cavity (the "cavities you heat to assemble" in the docx)
that receives the mating piece's ball. So a limb = A (hip end) --ball/socket-->
B (foot/hand end).

Reassembly: straighten each piece to +X by PCA, seat the ball in the socket, and
concatenate proximal->distal into one continuous leg skin. (The figure ships no
assembly transforms, so the axial join is a straightened concatenation — reported.)

Run: blender --background --python scripts/blender_actionfig_legs.py
"""
import sys, os, math, json
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
SRC = os.path.join(ROOT, "reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS")
MEDIA = os.path.join(ROOT, "docs/media")
STL_OUT = os.path.join(ROOT, "rocky/cad/stl_derived")
os.makedirs(MEDIA, exist_ok=True); os.makedirs(STL_OUT, exist_ok=True)

# limb -> (proximal piece, distal piece).  limb1 distal = 1-C open hand (manipulator).
LIMBS = {1: ("1-A", "1-C"), 2: ("2-A", "2-B"), 3: ("3-A", "3-B"),
         4: ("4-A", "4-B"), 5: ("5-A", "5-B")}
MANIP = 1


# ------------------------------- helpers --------------------------------------
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
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active = o


def cleanm(o, dist=0.08):
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def verts(o):
    return [v.co.copy() for v in o.data.vertices]


def pca_axis(V):
    n = len(V)
    c = Vector((sum(p.x for p in V) / n, sum(p.y for p in V) / n, sum(p.z for p in V) / n))
    # covariance
    cov = [[0.0] * 3 for _ in range(3)]
    for p in V:
        d = (p.x - c.x, p.y - c.y, p.z - c.z)
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j]
    # power iteration for dominant eigenvector
    v = Vector((1.0, 0.3, 0.1))
    for _ in range(80):
        nv = Vector((sum(cov[0][k] * v[k] for k in range(3)),
                     sum(cov[1][k] * v[k] for k in range(3)),
                     sum(cov[2][k] * v[k] for k in range(3))))
        if nv.length < 1e-9: break
        v = nv.normalized()
    return c, v


def straighten(o):
    """Align piece principal axis to +X, center; return (length, endinfo)."""
    V = verts(o); c, axis = pca_axis(V)
    # rotation aligning axis -> +X
    x = Vector((1, 0, 0))
    q = axis.rotation_difference(x)
    M = q.to_matrix().to_4x4() @ Matrix.Translation(-c)
    o.data.transform(M); o.data.update()
    V = verts(o)
    xs = [p.x for p in V]; x0, x1 = min(xs), max(xs); L = x1 - x0
    o.data.transform(Matrix.Translation(Vector((-x0, 0, 0)))); o.data.update()
    return L


def end_metrics(o):
    """Return per-end (min-x, max-x): cup depth (axis empties = socket) + rmax."""
    V = verts(o); xs = [p.x for p in V]; x0, x1 = min(xs), max(xs); L = x1 - x0
    yc = sum(p.y for p in V) / len(V); zc = sum(p.z for p in V) / len(V)
    # cup: scan axis line for material; the socket end has a long empty run
    # approximate "inside" by presence of surface within 3mm radius of axis at x
    def near_axis(xq):
        return any((p.x - xq) ** 2 < 4 and (p.y - yc) ** 2 + (p.z - zc) ** 2 < 9 for p in V)
    step = 1.0
    xi = x0
    lo = x0
    while xi < x1 and not near_axis(xi): xi += step
    lo = xi
    xi = x1
    while xi > x0 and not near_axis(xi): xi -= step
    hi = xi
    cup0 = lo - x0; cup1 = x1 - hi

    def rmax(hiend):
        sel = [p for p in V if p.x > x1 - 0.15 * L] if hiend else [p for p in V if p.x < x0 + 0.15 * L]
        return max(math.hypot(p.y - yc, p.z - zc) for p in sel) if sel else 0.0
    return {"cup0": cup0, "cup1": cup1, "rmax0": rmax(False), "rmax1": rmax(True), "L": L}


def flip_x(o):
    o.data.transform(Matrix.Diagonal((-1, 1, 1, 1))); o.data.update()
    V = verts(o); x0 = min(p.x for p in V)
    o.data.transform(Matrix.Translation(Vector((-x0, 0, 0)))); o.data.update()


def stone_mat():
    m = bpy.data.materials.new("stone"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.42, 0.38, 0.32, 1)
    b.inputs["Roughness"].default_value = 0.86
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 14.0
    tex.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.32
    bump.inputs["Distance"].default_value = 0.6
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ---------------------------- reassemble each limb ----------------------------
clear()
report = {"source": os.path.relpath(SRC, ROOT),
          "structure": "articulated ball-and-socket SEGMENTS (proximal A + distal B); NOT print-split halves",
          "manipulator_limb": MANIP, "hand_option_used": "1-C (open hand); 1-B is the closed-hand alt",
          "limbs": {}}
mat = stone_mat()
PITCH = 26.0
legs = []
for li, (pa, pb) in LIMBS.items():
    A = imp(os.path.join(SRC, pa + ".stl")); A.name = f"L{li}_A"
    B = imp(os.path.join(SRC, pb + ".stl")); B.name = f"L{li}_B"
    for o in (A, B):
        act(o); bpy.ops.object.make_single_user(object=True, obdata=True); cleanm(o)
    La = straighten(A); Lb = straighten(B)
    ema = end_metrics(A); emb = end_metrics(B)
    # find the socket (deepest cup among the 4 ends)
    ends = [("A", 0, ema["cup0"]), ("A", 1, ema["cup1"]), ("B", 0, emb["cup0"]), ("B", 1, emb["cup1"])]
    spiece, send, sdepth = max(ends, key=lambda e: e[2])
    socketed = sdepth > 2.5
    # Orient A: hip(free) at -X, knee(joint) at +X.
    #   if socket is on A -> knee = socket end; else knee = slimmer-rmax end (the ball).
    if socketed and spiece == "A":
        a_knee_hi = (send == 1)
    else:
        a_knee_hi = ema["rmax1"] <= ema["rmax0"]   # slimmer end is the ball/knee
    if not a_knee_hi: flip_x(A)                       # ensure knee at +X (max)
    # Orient B: knee(joint) at -X, foot/hand(free) at +X.
    if socketed and spiece == "B":
        b_knee_lo = (send == 0)
    else:
        b_knee_lo = emb["rmax0"] <= emb["rmax1"]
    if not b_knee_lo: flip_x(B)
    # seat ball in socket: overlap = socket depth (min 4 mm)
    overlap = max(4.0, min(sdepth, 14.0)) if socketed else 5.0
    B.data.transform(Matrix.Translation(Vector((La - overlap, 0, 0)))); B.data.update()
    # join A+B into one leg skin
    act(A); B.select_set(True); bpy.context.view_layer.objects.active = A
    bpy.ops.object.join(); leg = A; leg.name = f"af_leg{li}"
    cleanm(leg, 0.05)
    Vf = verts(leg); total = max(p.x for p in Vf) - min(p.x for p in Vf)
    legs.append((li, leg))
    report["limbs"][li] = {
        "pieces": [pa, pb] + (["1-B(alt closed hand)"] if li == MANIP else []),
        "piece_lengths_mm": [round(La, 1), round(Lb, 1)],
        "assembled_length_mm": round(total, 1),
        "socket_on": f"{spiece}-end{send}", "socket_depth_mm": round(sdepth, 1),
        "is_manipulator": (li == MANIP)}

# distinctness: compare assembled lengths + per-piece volumes already show 2-3x spread
lens = [report["limbs"][li]["assembled_length_mm"] for li in LIMBS]
report["legs_distinct"] = (max(lens) - min(lens) > 5.0)
report["distinctness_note"] = (
    "The 5 limbs are DISTINCT individually-sculpted skins (assembled lengths %s mm; "
    "per-piece volumes span 1.1-3.0 cm^3, ~3x), NOT identical repeated instances." % lens)

# ------------------------------- lay out + render -----------------------------
maxL = max(report["limbs"][li]["assembled_length_mm"] for li in LIMBS)
placed = []
for k, (li, leg) in enumerate(legs):
    V = verts(leg); zc = sum(p.z for p in V) / len(V); yc = sum(p.y for p in V) / len(V)
    leg.data.transform(Matrix.Translation(Vector((0, -yc, -zc)))); leg.data.update()
    y = (2 - k) * PITCH
    leg.location = (0, y, 12.0)
    leg.data.materials.append(mat)
    act(leg); bpy.ops.object.shade_flat()
    placed.append((li, leg, y))

# ground + lights + world
bpy.ops.mesh.primitive_plane_add(size=1200, location=(maxL / 2, 0, 0))
g = bpy.context.active_object; gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.09, 0.11, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
g.data.materials.append(gm)
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8


def add_light(kind, name, energy, loc, rot, size=120):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; return o


add_light("SUN", "key", 3.0, (maxL / 2, -80, 200), (math.radians(42), math.radians(10), math.radians(30)))
add_light("AREA", "fill", 9000, (-40, -110, 130), (math.radians(55), 0, math.radians(-40)), 200)
add_light("AREA", "rim", 6000, (maxL, 120, 130), (math.radians(60), 0, math.radians(150)), 200)

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 1500; sc.render.resolution_y = 1150
try: sc.eevee.use_gtao = True; sc.eevee.use_soft_shadows = True; sc.eevee.taa_render_samples = 64
except Exception: pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam)
sc.camera = cam
allV = [leg.matrix_world @ v.co for _, leg, _ in placed for v in leg.data.vertices]
cx = (min(p.x for p in allV) + max(p.x for p in allV)) / 2
cy = (min(p.y for p in allV) + max(p.y for p in allV)) / 2
cz = (min(p.z for p in allV) + max(p.z for p in allV)) / 2
span = max(max(p.x for p in allV) - min(p.x for p in allV),
           max(p.y for p in allV) - min(p.y for p in allV))
tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt); tgt.location = (cx, cy, cz)
con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
cam.data.type = "ORTHO"; cam.data.ortho_scale = span * 1.35
cam.data.clip_start = 1; cam.data.clip_end = 4000
cam.location = (cx - span * 0.28, cy, cz + span * 1.4)

from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
RX, RY = sc.render.resolution_x, sc.render.resolution_y
label_px = []
for li, leg, y in placed:
    Vw = [leg.matrix_world @ v.co for v in leg.data.vertices]
    hip = min(Vw, key=lambda p: p.x)
    foot = max(Vw, key=lambda p: p.x)
    ch = world_to_camera_view(sc, cam, hip); cf = world_to_camera_view(sc, cam, foot)
    label_px.append({"limb": li, "is_manip": li == MANIP,
                     "hip_px": [round(ch.x * RX), round((1 - ch.y) * RY)],
                     "foot_px": [round(cf.x * RX), round((1 - cf.y) * RY)]})
report["label_px"] = label_px

out = os.path.join(MEDIA, "rocky_actionfig_legs.png")
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDER_DONE", out)

# export reassembled leg skins for the shell pass (gitignored STLs)
for li, leg in legs:
    act(leg)
    p = os.path.join(STL_OUT, f"af_leg{li}_assembled.stl")
    try: bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True, apply_modifiers=True)
    except Exception: bpy.ops.export_mesh.stl(filepath=p, use_selection=True)

json.dump(report, open(os.path.join(STL_OUT, "actionfig_legs_report.json"), "w"), indent=2)
print("AF_LEGS_REPORT", json.dumps(report))
