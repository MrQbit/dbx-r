#!/usr/bin/env python3
"""D-047 orientation check — is each leg assembled proximal->distal in the right ORDER and
each segment the right way round? Renders the 5 legs in their assembly placement with the
3 segments COLOUR-CODED (coxa=blue, femur=green, tibia=orange, hand=red) and MARKERS at the
hip (white), the knee A/B junction (magenta), and the distal tip (yellow). If a marker for the
knee lands at the tip, or a colour is out of order, a segment is reversed / mis-ordered.

Uses the SAME placement math as scripts/blender_wrist_cuff_render.py build_scene (the real
assembly). Writes docs/build_plan/leg_orientation_check.png. RENDER-ONLY.
Run: blender --background --python scripts/render_leg_orientation.py
"""
import bpy, os, math
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
SRC = os.path.join(ROOT, "reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS")
SH = os.path.join(ROOT, "rocky/cad/stl_derived/af_shells")
OUT = os.path.join(ROOT, "docs/build_plan")
SCRATCH = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
SCALE_BODY = 4.40
J1, J2, TIPX = 50.0, 125.0, 282.0
SH_F, SH_T = -20.0, -46.0
FP_PLANT, KNEE_PLANT = 0.698, 0.611
FP_RAISE, KNEE_RAISE = -0.95, 0.65
COL = {"coxa": (0.15, 0.35, 0.9), "femur": (0.2, 0.8, 0.25),
       "tibia": (0.95, 0.55, 0.1), "hand": (0.9, 0.15, 0.15)}


def clear_all():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.objects, bpy.data.lights, bpy.data.cameras):
        for b in list(c):
            try: c.remove(b)
            except Exception: pass


def imp(p):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=p)
    else: bpy.ops.import_mesh.stl(filepath=p)
    return bpy.context.selected_objects[0]


def mat(name, rgb, emit=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.7
    if emit and "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m


def Ry(a, piv):
    return Matrix.Translation(Vector((piv, 0, 0))) @ Matrix.Rotation(a, 4, 'Y') @ Matrix.Translation(Vector((-piv, 0, 0)))


def detect_pegs(torso):
    verts = [v.co.copy() for v in torso.data.vertices]
    prof = [0.0] * 360; vat = [None] * 360
    for p in verts:
        r = math.hypot(p.x, p.y); a = int(math.degrees(math.atan2(p.y, p.x))) % 360
        if r > prof[a]: prof[a] = r; vat[a] = p
    best = None
    for ph in range(72):
        s = sum(prof[(ph + 72 * k) % 360] for k in range(5))
        if best is None or s > best[0]: best = (s, ph)
    ph0 = best[1]; raw = []
    for k in range(5):
        a0 = ph0 + 72 * k
        ab = max(range(a0 - 16, a0 + 17), key=lambda a: prof[a % 360]) % 360
        raw.append(vat[ab])
    raw = [p for p in raw if p is not None]; raw.sort(key=lambda p: math.atan2(p.y, p.x))
    det_r = sorted(math.hypot(p.x, p.y) for p in raw); det_z = sorted(p.z for p in raw)
    HIP_R = det_r[len(det_r) // 2]; HIP_Z = det_z[len(det_z) // 2]
    az0 = math.atan2(raw[0].y, raw[0].x)
    return [Vector((HIP_R * math.cos(az0 + math.radians(72 * k)),
                    HIP_R * math.sin(az0 + math.radians(72 * k)), HIP_Z)) for k in range(5)]


def marker(loc, rgb, r=9.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc)
    o = bpy.context.active_object; o.data.materials.append(mat("mk", rgb, emit=True))
    return o


def seg_xrange(o):
    xs = [v.co.x for v in o.data.vertices]
    return min(xs), max(xs)


def build(depeg=True):
    clear_all()
    tsrc = os.path.join(SH, "torso_depeg.stl") if depeg and os.path.exists(os.path.join(SH, "torso_depeg.stl")) else os.path.join(SRC, "torso.stl")
    torso = imp(tsrc); torso.name = "torso"
    torso.data.transform(Matrix.Scale(SCALE_BODY, 4)); torso.data.update()
    V = [v.co for v in torso.data.vertices]
    cx = sum(p.x for p in V) / len(V); cy = sum(p.y for p in V) / len(V)
    torso.data.transform(Matrix.Translation(Vector((-cx, -cy, 0)))); torso.data.update()
    torso.data.materials.append(mat("torso", (0.5, 0.5, 0.5)))
    # detect pegs from the ORIGINAL pegged torso (placement reference), matching build_scene
    ptorso = imp(os.path.join(SRC, "torso.stl")); ptorso.data.transform(Matrix.Scale(SCALE_BODY, 4))
    Vp = [v.co for v in ptorso.data.vertices]
    pcx = sum(p.x for p in Vp) / len(Vp); pcy = sum(p.y for p in Vp) / len(Vp)
    ptorso.data.transform(Matrix.Translation(Vector((-pcx, -pcy, 0)))); ptorso.data.update()
    pegs = detect_pegs(ptorso); bpy.data.objects.remove(ptorso, do_unlink=True)
    objs = [torso]
    for idx, peg in enumerate(pegs):
        N = idx + 1; az = math.atan2(peg.y, peg.x); raised = (N == 1)
        fp = FP_RAISE if raised else FP_PLANT; kn = KNEE_RAISE if raised else KNEE_PLANT
        M_femur = Ry(fp, J1) @ Matrix.Translation(Vector((SH_F, 0, 0)))
        M_tibia = Ry(fp, J1) @ Ry(kn, J2) @ Matrix.Translation(Vector((SH_T, 0, 0)))
        place = Matrix.Translation(peg) @ Matrix.Rotation(az, 4, 'Z')
        segM = {"coxa": Matrix.Identity(4), "femur": M_femur, "tibia": M_tibia}
        for nm, M in segM.items():
            o = imp(os.path.join(SH, f"leg{N}_{nm}_solid.stl")); o.name = f"L{N}_{nm}"
            o.data.materials.append(mat(f"{nm}{N}", COL[nm])); o.matrix_world = place @ M; objs.append(o)
        tmax = seg_xrange(bpy.data.objects[f"L{N}_tibia"])[1]
        # markers: hip (peg), knee (femur-distal/tibia-proximal junction), tip (tibia foot)
        objs.append(marker(place @ Vector((0, 0, 0)), (1, 1, 1)))              # hip white
        objs.append(marker(place @ Ry(fp, J1) @ Vector((J2, 0, 0)), (1, 0, 1)))  # knee magenta
        objs.append(marker(place @ M_tibia @ Vector((tmax, 0, 0)), (1, 1, 0)))    # tip yellow
        if raised:
            h = imp(os.path.join(SH, "hand_cosmetic_solid.stl")); h.name = f"L{N}_hand"
            Vh = [v.co for v in h.data.vertices]
            hc = Vector((sum(p.x for p in Vh) / len(Vh), sum(p.y for p in Vh) / len(Vh), sum(p.z for p in Vh) / len(Vh)))
            h.data.transform(Matrix.Translation(-hc)); h.data.update()
            hs = 95.0 / max(h.dimensions); h.data.transform(Matrix.Scale(hs, 4)); h.data.update()
            h.data.materials.append(mat("hand", COL["hand"]))
            h.matrix_world = place @ M_tibia @ Matrix.Translation(Vector((TIPX, 0, 0))); objs.append(h)
    return objs


def bb(objs):
    xs = []; ys = []; zs = []
    for o in objs:
        for v in o.data.vertices:
            p = o.matrix_world @ v.co; xs.append(p.x); ys.append(p.y); zs.append(p.z)
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def lights(center, R):
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    for loc, e in [((1, -1, 1.4), 4.0), ((-1, -0.5, 0.6), 2.0)]:
        L = bpy.data.objects.new("l", bpy.data.lights.new("l", "SUN")); bpy.context.collection.objects.link(L)
        L.data.energy = e; L.rotation_euler = (-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def cam(center, view, R, ortho):
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = ortho
    c = bpy.data.objects.new("c", cd); bpy.context.scene.collection.objects.link(c); bpy.context.scene.camera = c
    c.location = center + Vector(view).normalized() * R * 4
    c.rotation_euler = (center - c.location).to_track_quat('-Z', 'Y').to_euler(); cd.clip_end = R * 30
    return c


def render(view, ortho, path, res=(1500, 1100)):
    objs = build()
    mn, mx = bb(objs); center = (mn + mx) / 2; R = max(mx - mn)
    lights(center, R); cam(center, view, R, ortho)
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    print("wrote", path)


render((0, 0, 1), 620, os.path.join(SCRATCH, "orient_top.png"), (1500, 1500))
render((0, -1, 0.05), 620, os.path.join(SCRATCH, "orient_side.png"), (1600, 900))

# composite with legend
from PIL import Image, ImageDraw, ImageFont
def Fn(s, b=False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else "")
    try: return ImageFont.truetype(p, s)
    except Exception: return ImageFont.load_default()
top = Image.open(os.path.join(SCRATCH, "orient_top.png")).convert("RGB")
side = Image.open(os.path.join(SCRATCH, "orient_side.png")).convert("RGB")
pad = 20; W = max(top.width, side.width) + pad * 2; H = top.height + side.height + pad * 3 + 90
c = Image.new("RGB", (W, H), (16, 16, 20)); d = ImageDraw.Draw(c)
d.text((pad, 8), "ROCKY-5 leg ORIENTATION check (D-047)  —  coxa=BLUE  femur=GREEN  tibia=ORANGE  hand=RED", fill=(240, 235, 225), font=Fn(26, True))
d.text((pad, 40), "markers:  HIP=white   KNEE(A/B junction)=magenta   TIP(foot/hand)=yellow.   Correct = blue->green->[magenta knee]->orange->yellow tip.", fill=(180, 180, 185), font=Fn(19))
c.paste(top, (pad, 74)); c.paste(side, (pad, 74 + top.height + pad))
d.text((pad, 74 + top.height + 2), "TOP", fill=(200, 200, 205), font=Fn(20, True))
d.text((pad, 74 + top.height + pad + side.height - 24), "SIDE", fill=(200, 200, 205), font=Fn(20, True))
c.save(os.path.join(OUT, "leg_orientation_check.png"))
print("WROTE", os.path.join(OUT, "leg_orientation_check.png"), c.size)
