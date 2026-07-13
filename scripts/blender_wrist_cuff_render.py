#!/usr/bin/env python3
"""D-046 renders — regenerate the whole-assembly hero WITH the leg1 wrist cuff, and
a leg1 manipulator-wrist BEFORE/AFTER close-up so the operator can see the bulge is
gone. Reuses the assemble_rocky.py pose/placement machinery (same poses, scale,
material). RENDER-ONLY; no geometry export.
Run: blender --background --python scripts/blender_wrist_cuff_render.py
"""
import bpy, os, math, json
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


def clear_all():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for b in list(c):
            try: c.remove(b)
            except Exception: pass


def imp(p):
    if hasattr(bpy.ops.wm, "stl_import"): bpy.ops.wm.stl_import(filepath=p)
    else: bpy.ops.import_mesh.stl(filepath=p)
    return bpy.context.selected_objects[0]


def world_bb(objs):
    xs = []; ys = []; zs = []
    for o in objs:
        for v in o.data.vertices:
            p = o.matrix_world @ v.co; xs.append(p.x); ys.append(p.y); zs.append(p.z)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def stone_mat(name="stone", tint=(0.46, 0.44, 0.42)):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*tint, 1)
    bsdf.inputs["Roughness"].default_value = 0.86
    if "Specular" in bsdf.inputs: bsdf.inputs["Specular"].default_value = 0.25
    elif "Specular IOR Level" in bsdf.inputs: bsdf.inputs["Specular IOR Level"].default_value = 0.25
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 14.0
    tex.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
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


def build_scene(with_cuff):
    """Build torso + 5 legs (+hand on leg1, +cuff if with_cuff). Returns (objs, leg1_tip_world)."""
    clear_all()
    MAT = stone_mat()
    # D-047: de-pegged torso (5 vestigial hip ball-pegs shaved off); native scale, x4.40 here
    _torso_src = os.path.join(SH, "torso_depeg.stl")
    if not os.path.exists(_torso_src):
        _torso_src = os.path.join(SRC, "torso.stl")
    torso = imp(_torso_src); torso.name = "torso"
    torso.data.transform(Matrix.Scale(SCALE_BODY, 4)); torso.data.update()
    V = [v.co for v in torso.data.vertices]
    cx = sum(p.x for p in V) / len(V); cy = sum(p.y for p in V) / len(V)
    torso.data.transform(Matrix.Translation(Vector((-cx, -cy, 0)))); torso.data.update()
    torso.data.materials.append(MAT)
    pegs = detect_pegs(torso)
    objs = [torso]; leg1_tip = None; hand_center = None
    for idx, peg in enumerate(pegs):
        N = idx + 1; az = math.atan2(peg.y, peg.x); raised = (N == 1)
        fp = FP_RAISE if raised else FP_PLANT
        kn = KNEE_RAISE if raised else KNEE_PLANT
        M_femur = Ry(fp, J1) @ Matrix.Translation(Vector((SH_F, 0, 0)))
        M_tibia = Ry(fp, J1) @ Ry(kn, J2) @ Matrix.Translation(Vector((SH_T, 0, 0)))
        place = Matrix.Translation(peg) @ Matrix.Rotation(az, 4, 'Z')
        segM = {"coxa": Matrix.Identity(4), "femur": M_femur, "tibia": M_tibia}
        for nm, M in segM.items():
            o = imp(os.path.join(SH, f"leg{N}_{nm}_solid.stl")); o.name = f"L{N}_{nm}"
            o.data.materials.append(MAT); o.matrix_world = place @ M; objs.append(o)
        if raised:
            # cuff on the FIXED tibia side (built in tibia-native coords -> same M_tibia)
            if with_cuff:
                c = imp(os.path.join(SH, "leg1_wrist_cuff_hollow.stl")); c.name = "L1_cuff"
                c.data.materials.append(MAT); c.matrix_world = place @ M_tibia; objs.append(c)
            h = imp(os.path.join(SH, "hand_cosmetic_solid.stl")); h.name = "L1_hand"
            Vh = [v.co for v in h.data.vertices]
            hc = Vector((sum(p.x for p in Vh) / len(Vh), sum(p.y for p in Vh) / len(Vh),
                         sum(p.z for p in Vh) / len(Vh)))
            h.data.transform(Matrix.Translation(-hc)); h.data.update()
            hs = 95.0 / max(h.dimensions); h.data.transform(Matrix.Scale(hs, 4)); h.data.update()
            h.data.materials.append(MAT)
            h.matrix_world = place @ M_tibia @ Matrix.Translation(Vector((TIPX, 0, 0)))
            objs.append(h)
            # the manipulator wrist point in world (native x~258 on the tibia axis y=-9)
            leg1_tip = (place @ M_tibia @ Vector((258.0, -9.0, 0.0)))
    return objs, leg1_tip


def setup_world_lights(center, R):
    scn = bpy.context.scene
    try: scn.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception: scn.render.engine = 'BLENDER_EEVEE'
    for att in ("use_gtao", "use_shadows"):
        try: setattr(scn.eevee, att, True)
        except Exception: pass
    try: scn.view_settings.view_transform = 'Filmic'
    except Exception: pass
    looks = [v.name for v in bpy.types.ColorManagedViewSettings.bl_rna.properties['look'].enum_items]
    scn.view_settings.look = 'Medium High Contrast' if 'Medium High Contrast' in looks else 'None'
    world = bpy.data.worlds['World']; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.04, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.18
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(center.x, center.y, 0))
    g = bpy.context.active_object
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gb = gm.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = (0.025, 0.025, 0.03, 1)
    gb.inputs["Roughness"].default_value = 0.98
    g.data.materials.append(gm)

    def area(name, loc, energy, size):
        bpy.ops.object.light_add(type='AREA', location=loc)
        L = bpy.context.active_object; L.name = name; L.data.energy = energy; L.data.size = size
        d = Vector(loc) - center; L.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        return L
    area("key", (center.x + R * 1.0, center.y - R * 1.1, center.z + R * 1.3), 4.0e6, R * 1.1)
    area("fill", (center.x - R * 1.3, center.y - R * 0.4, center.z + R * 0.5), 1.1e6, R * 1.7)
    area("rim", (center.x - R * 0.2, center.y + R * 1.4, center.z + R * 1.1), 3.0e6, R * 0.9)
    return g


def datum_ground(objs):
    (mnx, mny, mnz), _ = world_bb(objs)
    for o in objs:
        o.location = (o.location.x, o.location.y, o.location.z - mnz)
    bpy.context.view_layer.update()


def make_cam(name, center, dir_vec, ortho_scale, dist):
    scn = bpy.context.scene
    cd = bpy.data.cameras.new(name); cd.type = 'ORTHO'; cd.ortho_scale = ortho_scale
    cam = bpy.data.objects.new(name, cd); scn.collection.objects.link(cam)
    dv = Vector(dir_vec).normalized()
    cam.location = center + dv * dist
    cam.rotation_euler = (cam.location - center).to_track_quat('Z', 'Y').to_euler()
    cd.clip_start = 1.0; cd.clip_end = dist * 10
    return cam


def render_to(cam, path, res):
    scn = bpy.context.scene; scn.camera = cam
    scn.render.resolution_x = res[0]; scn.render.resolution_y = res[1]
    scn.render.film_transparent = False
    scn.render.image_settings.file_format = 'PNG'
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ======================= 1) CLOSE-UP before/after ============================
def closeup(with_cuff, path):
    objs, tip = build_scene(with_cuff)
    (mnx, mny, mnz), _ = world_bb(objs)
    datum_ground(objs)
    center = Vector((tip.x, tip.y, tip.z - mnz))   # apply the same ground datum shift
    setup_world_lights(center, 260.0)
    # frame the leg1 wrist: view roughly perpendicular to the raised arm, 3/4
    cam = make_cam("cu", center, (1.0, -1.2, 0.35), 190.0, 1400.0)
    render_to(cam, path, (1200, 1200))
    return center


c_after = closeup(False, os.path.join(SCRATCH, "cu_after.png"))

# ======================= 2) FULL assembly (D-047 de-pegged, NO cuff) =========
objs, tip = build_scene(False)
datum_ground(objs)
(mnx, mny, mnz), (mxx, mxy, mxz) = world_bb(objs)
span_x = mxx - mnx; span_y = mxy - mny; height = mxz - mnz
tip_span = max(span_x, span_y)
center = Vector(((mnx + mxx) / 2, (mny + mxy) / 2, (mnz + mxz) / 2))
setup_world_lights(center, max(tip_span, height))
diag_span = max(span_x, span_y, height); MARGIN = 1.12
hero = make_cam("hero", center, (1.0, -1.15, 0.72), diag_span * 1.32, max(tip_span, height) * 3.0)
top = make_cam("top", center, (0.0, 0.0, 1.0), max(span_x, span_y) * MARGIN, max(tip_span, height) * 3.0)
side = make_cam("side", center, (0.0, -1.0, 0.0), max(span_x, height) * MARGIN, max(tip_span, height) * 3.0)
render_to(hero, os.path.join(SCRATCH, "panel_hero.png"), (1500, 1650))
render_to(top, os.path.join(SCRATCH, "panel_top.png"), (1100, 1100))
render_to(side, os.path.join(SCRATCH, "panel_side.png"), (1200, 1000))

# ======================= composites (PIL) ====================================
from PIL import Image, ImageDraw, ImageFont
try: FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
except Exception: FB = ImageFont.load_default()
try: FS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
except Exception: FS = FB
BG = (14, 14, 17)


def load(p): return Image.open(p).convert("RGB")

# ---- close-up: the CLEAN de-pegged leg1 wrist (D-047; cuff dropped) ----
a = load(os.path.join(SCRATCH, "cu_after.png"))
pad = 24
W = a.width + pad * 2
H = a.height + pad * 2 + 40
canvas = Image.new("RGB", (W, H), BG)
canvas.paste(a, (pad, pad + 40))
d = ImageDraw.Draw(canvas)
d.text((pad + 8, pad + 6), "leg1 manipulator wrist — D-047 de-pegged  (1-A/1-C ball-knob removed; reads as broken craggy stone)", fill=(210, 235, 210), font=FS)
d.text((pad + 8, H - 30), "D-046 wrist-cuff DROPPED — the bulge was the vestigial toy ball-joint, now removed at source; no mechanism geometry changed", fill=(160, 160, 165), font=FS)
canvas.save(os.path.join(OUT, "manip_wrist_cover.png"))
print("WROTE", os.path.join(OUT, "manip_wrist_cover.png"), canvas.size)

# ---- full assembly (same layout as before) ----
hero_i = load(os.path.join(SCRATCH, "panel_hero.png"))
top_i = load(os.path.join(SCRATCH, "panel_top.png"))
side_i = load(os.path.join(SCRATCH, "panel_side.png"))
colw = 560


def fit_w(im, w):
    h = int(im.height * w / im.width); return im.resize((w, h))


top_r = fit_w(top_i, colw); side_r = fit_w(side_i, colw)
heroh = max(top_r.height + side_r.height + pad, 1200)
hero_r = hero_i.resize((int(hero_i.width * heroh / hero_i.height), heroh))
W = hero_r.width + pad * 3 + colw
H = max(hero_r.height, top_r.height + side_r.height + pad) + pad * 2
canvas = Image.new("RGB", (W, H), BG)
canvas.paste(hero_r, (pad, pad)); rx = pad * 2 + hero_r.width
canvas.paste(top_r, (rx, pad)); canvas.paste(side_r, (rx, pad + top_r.height + pad))
d = ImageDraw.Draw(canvas)
d.text((pad + 8, pad + 8), "ROCKY-5  —  whole assembly  (D-047: vestigial toy joints removed)", fill=(235, 230, 220), font=FB)
d.text((rx + 8, pad + 6), "TOP  (pentaradial)", fill=(220, 215, 205), font=FS)
d.text((rx + 8, pad + top_r.height + pad + 6), "SIDE  (stance / splay)", fill=(220, 215, 205), font=FS)
d.text((pad + 8, H - pad - 2),
       "span %d mm  x  height %d mm   |   torso x%.2f sculpt scale   |   D-047: 5 torso hip-pegs + leg1 wrist ball-knob removed"
       % (round(tip_span), round(height), SCALE_BODY), fill=(170, 170, 175), font=FS)
canvas.save(os.path.join(OUT, "rocky_full_assembly.png"))
print("WROTE", os.path.join(OUT, "rocky_full_assembly.png"), canvas.size)
print("DONE")
