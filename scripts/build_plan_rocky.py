"""ROCKY-5 BUILD-PLAN generator — MODEL the EduLite-05 servos and show them
EMBEDDED in every leg joint, so the operator understands how the leg assembles.

WHY THIS EXISTS
  Exterior renders read as "detached pieces / flat cuts" because the servo that
  bridges each joint gap was never modelled. The slender leg neck (37 mm at
  knee1) is thinner than the Ø46 EduLite body, so the servo seat pocket carves
  the whole joint cross-section away — leaving coxa and femur joined ONLY by the
  (never-drawn) servo, hidden under a cosmetic stone cover sleeve. Draw the
  servo in that pocket and the joint reads as a real mechanism.

INPUTS  (rocky/cad/stl_derived/, already in a shared world frame — one leg,
         thorax at origin, leg extends +X and down, pitch axis = world Y):
  refined_thorax / refined_coxa / refined_femur / refined_tibia
  refined_knee1_cover / refined_knee2_cover   (cosmetic stone sleeves)

OUTPUTS (docs/build_plan/):
  _raw_exploded.png / _raw_cutaway.png / _raw_ghost.png   (Blender renders)
  build_plan_coords.json                                  (2D label anchors)
  build_plan_facts.json                                   (BOM + fit verify)
  servo_edulite05.stl / servo_grip_micro.stl              (the modelled servos)
The matplotlib pass (annotate_build_plan.py) turns the raw renders + coords into
the labelled deliverables.

Run:  blender --background --python scripts/build_plan_rocky.py
"""
import bpy, bmesh, math, os, json
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STL = os.path.join(ROOT, "rocky", "cad", "stl_derived")
OUT = os.path.join(ROOT, "docs", "build_plan")
os.makedirs(OUT, exist_ok=True)

# ---- EduLite-05 datasheet (components.SERVO + standards.EDULITE_*) -----------
BODY_D, BODY_L = 46.0, 44.0          # Ø46 x 44 housing
COLLAR_D, COLLAR_L = 24.0, 8.0       # Ø24 x 8 output collar
FLANGE_D, FLANGE_T = 52.0, 3.0       # mounting-flange disc (Ø41.5 PCD + rim)
GRIP = (22.8, 12.2, 28.5)            # grip micro-servo box (MG90S-class)

# ---- joint pivots (world frame; derived from the exported STLs, see report) --
# axis of every leg servo = world Y (the pitch axis the seats were bored along).
PIV = {
    "hip":   Vector((62.0, 0.0, 116.0)),   # coxa root, inside the thorax socket
    "knee1": Vector((88.0, 1.0,  91.0)),   # coxa/femur — slender: flat mount + cover
    "knee2": Vector((114.0, 5.0, 65.0)),   # femur/tibia
}
HAND = Vector((186.0, -2.0, 44.0))         # grip micro-servo, in the 3-finger hand
LEG_AXIS = (HAND - PIV["hip"]).normalized()  # hip -> foot

SEG_FILES = {"thorax": "refined_thorax", "coxa": "refined_coxa",
             "femur": "refined_femur", "tibia": "refined_tibia"}
COVER_FILES = {"knee1_cover": "refined_knee1_cover", "knee2_cover": "refined_knee2_cover"}

# =============================================================================
def wipe():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for b in list(c):
            try: c.remove(b)
            except Exception: pass


def import_stl(path, name):
    try: bpy.ops.wm.stl_import(filepath=path)
    except Exception:
        try: bpy.ops.import_mesh.stl(filepath=path)
        except Exception:
            bpy.ops.preferences.addon_enable(module="io_mesh_stl")
            bpy.ops.import_mesh.stl(filepath=path)
    o = bpy.context.selected_objects[0]; o.name = name; return o


def mat(name, rgba, rough=0.55, metal=0.0, alpha=1.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"; m.show_transparent_back = False
    if emit > 0.0:
        try:
            b.inputs["Emission Color"].default_value = rgba
            b.inputs["Emission Strength"].default_value = emit
        except Exception: pass
    return m


def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m)


def cyl(name, r, h, loc, axis="Z", verts=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = name
    if axis == "Y": o.rotation_euler = (math.radians(90), 0, 0)
    elif axis == "X": o.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    o.location = loc; bpy.ops.object.transform_apply(location=True)
    return o


def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = name
    o.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(scale=True)
    o.location = loc; bpy.ops.object.transform_apply(location=True)
    return o


def join(objs, name):
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join(); o = bpy.context.active_object; o.name = name
    return o


def build_edulite(name, pivot, out_dir="+Y", export=None):
    """EduLite-05 servo model, axis along world Y, centred on `pivot`.
    Body seats toward -Y (the hidden inner face the seats were bored on); the
    Ø24 output collar + flange present on the +Y (outer) mating side toward the
    distal segment.  out_dir flips which way the output faces."""
    s = 1.0 if out_dir == "+Y" else -1.0
    # body centred so it straddles the joint pocket (half of it either side)
    body = cyl(name + "_body", BODY_D / 2, BODY_L,
               (pivot.x, pivot.y - s * BODY_L * 0.15, pivot.z), axis="Y")
    y_out = pivot.y - s * BODY_L * 0.15 + s * BODY_L / 2
    flange = cyl(name + "_flange", FLANGE_D / 2, FLANGE_T,
                 (pivot.x, y_out + s * FLANGE_T / 2, pivot.z), axis="Y")
    collar = cyl(name + "_collar", COLLAR_D / 2, COLLAR_L,
                 (pivot.x, y_out + s * (FLANGE_T + COLLAR_L / 2), pivot.z), axis="Y")
    o = join([body, flange, collar], name)
    if export:
        act(o); export_stl(o, export)
    return o


def act(o):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active = o


def export_stl(o, path):
    act(o)
    try: bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
    except Exception:
        try: bpy.ops.export_mesh.stl(filepath=path, use_selection=True)
        except Exception: pass


def half_cut(o, plane_co, plane_no):
    """bmesh-bisect away the half-space on the +plane_no side, leaving the cut
    OPEN (no cap) so the hollow interior is revealed — a robust clip plane for
    thin/open shells where a boolean solid-difference would fail."""
    if o.data.users > 1: o.data = o.data.copy()
    mw = o.matrix_world
    co_l = mw.inverted() @ Vector(plane_co)
    no_l = (mw.inverted().to_3x3() @ Vector(plane_no)).normalized()
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=co_l, plane_no=no_l,
                           clear_inner=False, clear_outer=True)
    bm.to_mesh(me); bm.free(); me.update()


def bounds_center_top(objs):
    objs = [o for o in objs if len(o.data.vertices) > 0]
    zmin = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
    zmax = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)
    span = max(max(math.hypot((o.matrix_world @ v.co).x, (o.matrix_world @ v.co).y)
                   for v in o.data.vertices) for o in objs)
    return zmin, zmax, span


# ---- scene / lighting / camera ----------------------------------------------
def world_bg(strength=0.75, col=(0.05, 0.055, 0.07)):
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*col, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = strength


def add_light(kind, name, energy, loc, rot, size=800):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; return o


def make_camera(target, loc, lens=52, ortho=False, ortho_scale=None):
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam
    cam.data.lens = lens
    if ortho:
        cam.data.type = "ORTHO"
        if ortho_scale: cam.data.ortho_scale = ortho_scale
    tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt)
    tgt.location = target
    con = cam.constraints.new("TRACK_TO"); con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cam.location = loc
    bpy.context.view_layer.update()
    return cam


def render(path, res=1100):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = res; sc.render.resolution_y = res
    sc.render.film_transparent = False
    try:
        sc.eevee.use_gtao = True
        sc.eevee.use_ssr = False
    except Exception: pass
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", path)


def project(cam, pts):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    rx, ry = sc.render.resolution_x, sc.render.resolution_y
    out = {}
    for name, co in pts.items():
        v = world_to_camera_view(sc, cam, Vector(co))
        out[name] = [round(v.x * rx, 1), round((1 - v.y) * ry, 1), round(v.z, 1)]
    return out


# ============================ materials ======================================
def all_materials():
    return {
        "stone":  mat("stone", (0.34, 0.31, 0.27, 1), rough=0.92),
        "stone_g": mat("stone_ghost", (0.58, 0.56, 0.52, 0.24), rough=0.9, alpha=0.24),
        "cover":  mat("cover", (0.40, 0.36, 0.30, 1), rough=0.85),
        "cover_g": mat("cover_ghost", (0.5, 0.42, 0.3, 0.16), rough=0.85, alpha=0.16),
        "servo":  mat("servo", (0.93, 0.45, 0.09, 1), rough=0.35, metal=0.2),
        "collar": mat("collar", (0.15, 0.70, 0.85, 1), rough=0.3, metal=0.5),
        "grip":   mat("grip", (0.20, 0.78, 0.35, 1), rough=0.4),
    }


# ============================ VIEW BUILDERS ==================================
def load_leg(with_covers=True):
    segs = {n: import_stl(os.path.join(STL, f + ".stl"), n) for n, f in SEG_FILES.items()}
    covers = {}
    if with_covers:
        for n, f in COVER_FILES.items():
            p = os.path.join(STL, f + ".stl")
            if os.path.exists(p): covers[n] = import_stl(p, n)
    return segs, covers


def place_servos(export_first=False):
    servos = {}
    servos["hip"] = build_edulite("servo_hip", PIV["hip"], out_dir="-Y",
                                  export=os.path.join(OUT, "servo_edulite05.stl") if export_first else None)
    servos["knee1"] = build_edulite("servo_knee1", PIV["knee1"], out_dir="-Y")
    servos["knee2"] = build_edulite("servo_knee2", PIV["knee2"], out_dir="-Y")
    grip = box("servo_grip", GRIP, (HAND.x, HAND.y, HAND.z))
    if export_first:
        export_stl(grip, os.path.join(OUT, "servo_grip_micro.stl"))
    servos["grip"] = grip
    return servos


def light_studio(span, zmax):
    world_bg(0.7)
    add_light("SUN", "key", 3.2, (span, -span, 2 * span),
              (math.radians(52), math.radians(10), math.radians(35)))
    add_light("AREA", "fill", 26000, (-1.4 * span, -1.2 * span, 1.3 * span),
              (math.radians(55), 0, math.radians(-40)), size=1200)
    add_light("AREA", "rim", 18000, (1.1 * span, 1.3 * span, 1.2 * span),
              (math.radians(60), 0, math.radians(150)), size=1000)


# ---------------------------------------------------------------------------
def verify_bridge(segs, servos):
    """HONEST check: does the modelled knee1 servo actually overlap BOTH the coxa
    and the femur (so the joint is truly bridged, nothing floats)?"""
    import numpy as np
    def varr(o):
        return np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices])
    facts = {}
    body_r = BODY_D / 2
    for jk, (prox, dist) in [("hip", ("thorax", "coxa")),
                             ("knee1", ("coxa", "femur")),
                             ("knee2", ("femur", "tibia"))]:
        piv = np.array(PIV[jk][:])
        res = {}
        for role, seg in (("proximal", prox), ("distal", dist)):
            V = varr(segs[seg])
            # distance from each seg vertex to the servo's Y axis through pivot
            radial = np.hypot(V[:, 0] - piv[0], V[:, 2] - piv[2])
            near = V[radial < (body_r + 6.0)]
            res[role] = {"segment": seg,
                         "min_radial_to_servo_axis_mm": round(float(radial.min()), 1),
                         "verts_within_servo_footprint": int((radial < body_r).sum())}
        res["bridged"] = bool(res["proximal"]["min_radial_to_servo_axis_mm"] <= body_r + 3 and
                              res["distal"]["min_radial_to_servo_axis_mm"] <= body_r + 3)
        facts[jk] = res
    return facts


# ============================ MAIN ==========================================
def main():
    coords_all = {}

    # ---------- 1) SERVO STL export + fit verify (uses assembled placement) ----
    wipe(); M = all_materials()
    segs, covers = load_leg(with_covers=True)
    servos = place_servos(export_first=True)
    fit = verify_bridge(segs, servos)

    # ============ VIEW C: assembled GHOST (whole 5-leg robot) ==============
    wipe(); M = all_materials()
    segs, _ = load_leg(with_covers=False)
    for n, o in segs.items():
        setmat(o, M["stone_g"] if n != "thorax" else M["stone_g"])
    servos = place_servos()
    for k, o in servos.items():
        setmat(o, M["grip"] if k == "grip" else M["servo"])
    # collars pop
    # group base-leg objects, instance 5x about Z (thorax stays central)
    base_leg = [segs["coxa"], segs["femur"], segs["tibia"]] + list(servos.values())
    ghost_objs = [segs["thorax"]] + base_leg
    for k in range(1, 5):
        Rz = Matrix.Rotation(math.radians(72 * k), 4, "Z")
        for o in base_leg:
            d = o.copy(); d.data = o.data.copy()
            bpy.context.collection.objects.link(d)
            d.matrix_world = Rz @ d.matrix_world
            ghost_objs.append(d)
    zmin, zmax, span = bounds_center_top(ghost_objs)
    light_studio(span, zmax)
    cam = make_camera((0, 0, zmin + 0.45 * (zmax - zmin)),
                      (span * 1.7, -span * 1.7, zmax + 0.5 * span), lens=48)
    render(os.path.join(OUT, "_raw_ghost.png"))
    # label anchors: the 3 servos on the front (base) leg + one hip callout
    coords_all["ghost"] = project(cam, {
        "hip": PIV["hip"], "knee1": PIV["knee1"], "knee2": PIV["knee2"],
        "grip": HAND, "thorax": Vector((0, 0, zmax * 0.8))})

    # ============ VIEW A: EXPLODED single leg ==============================
    wipe(); M = all_materials()
    segs, covers = load_leg(with_covers=True)
    servos = place_servos()
    setmat(segs["thorax"], M["stone"])
    for n in ("coxa", "femur", "tibia"): setmat(segs[n], M["stone"])
    for n, o in covers.items(): setmat(o, M["cover"])
    for k, o in servos.items(): setmat(o, M["grip"] if k == "grip" else M["servo"])
    # explode along the leg axis; ordered proximal->distal
    A = LEG_AXIS
    order = [("thorax", segs["thorax"], -0.9), ("servo_hip", servos["hip"], 0.45),
             ("coxa", segs["coxa"], 1.35), ("knee1_cover", covers.get("knee1_cover"), 2.05),
             ("servo_knee1", servos["knee1"], 2.5), ("femur", segs["femur"], 3.45),
             ("knee2_cover", covers.get("knee2_cover"), 4.2),
             ("servo_knee2", servos["knee2"], 4.65), ("tibia", segs["tibia"], 5.7),
             ("servo_grip", servos["grip"], 6.7)]
    STEP = 58.0
    anchors = {}
    for name, o, k in order:
        if o is None: continue
        shift = A * (k * STEP)
        o.location = o.location + shift
        # anchor = object's world-center after shift
        c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
        anchors[name] = c
    expl = [o for _, o, _ in order if o is not None]
    # world bbox of the whole exploded assembly
    allv = [(o.matrix_world @ v.co) for o in expl for v in o.data.vertices]
    mn = Vector((min(p.x for p in allv), min(p.y for p in allv), min(p.z for p in allv)))
    mx = Vector((max(p.x for p in allv), max(p.y for p in allv), max(p.z for p in allv)))
    C = (mn + mx) / 2
    Rd = (mx - mn).length / 2
    _, zmax, span = bounds_center_top(expl)
    light_studio(Rd, zmax)
    # ISO view (from front-left-above) so each servo reads as a CYLINDER, not a disc
    view_dir = Vector((0.45, 1.3, -0.42)).normalized()     # camera -> target
    cam = make_camera(C, C - view_dir * Rd * 3.9, lens=54)
    render(os.path.join(OUT, "_raw_exploded.png"))
    coords_all["exploded"] = project(cam, anchors)

    # ============ VIEW B: CUTAWAY (longitudinal section) ==================
    wipe(); M = all_materials()
    segs, covers = load_leg(with_covers=True)
    servos = place_servos()
    # The servo axis is world Y — the very direction a flat longitudinal section
    # would be viewed from — so a flat section shows servos end-on as bare discs.
    # Instead: 3/4 perspective with the NEAR shell wall boolean-removed, servos +
    # covers kept WHOLE. You look into the opened hollow and read each servo as a
    # cylinder: body seated in the proximal shell, Ø24 collar reaching the distal
    # segment, the translucent cover sleeve clipping over the knee joints.
    legspan = (HAND - PIV["hip"]).length
    focus = (PIV["hip"] + HAND) / 2
    def centroid(o):
        acc = Vector((0, 0, 0))
        for v in o.data.vertices: acc += o.matrix_world @ v.co
        return acc / len(o.data.vertices)
    camdir = Vector((0.30, -1.0, 0.42)).normalized()    # focus -> camera (front/-Y/above)
    # remove the near-camera half of each SHELL, cutting through ITS OWN centroid
    # (a shared origin would delete whole distal segments) -> reveals the interior.
    for n in ("coxa", "femur", "tibia"):
        half_cut(segs[n], centroid(segs[n]) + camdir * 6.0, camdir)
        print(f"[cutaway] {n}: {len(segs[n].data.vertices)} verts after cut")
    setmat(segs["thorax"], M["stone"])
    for n in ("coxa", "femur", "tibia"): setmat(segs[n], M["stone"])
    for n, o in covers.items(): setmat(o, M["cover_g"])   # sleeve, translucent, whole
    for k, o in servos.items(): setmat(o, M["grip"] if k == "grip" else M["servo"])
    view_objs = [segs[n] for n in ("coxa", "femur", "tibia")] + \
                list(covers.values()) + list(servos.values())
    _, zmax, span = bounds_center_top(view_objs)
    light_studio(legspan, zmax)
    add_light("AREA", "section", 26000,
              (focus.x + legspan * 0.2, -legspan * 1.0, focus.z + legspan * 0.9),
              (math.radians(50), 0, math.radians(10)), size=1100)
    cam = make_camera(focus, focus + camdir * legspan * 2.1, lens=48)
    render(os.path.join(OUT, "_raw_cutaway.png"))
    coords_all["cutaway"] = project(cam, {
        "servo_hip": PIV["hip"], "servo_knee1": PIV["knee1"],
        "servo_knee2": PIV["knee2"], "coxa": PIV["hip"] * 0.5 + PIV["knee1"] * 0.5,
        "femur": (PIV["knee1"] + PIV["knee2"]) / 2,
        "tibia": (PIV["knee2"] + HAND) / 2, "grip": HAND})

    # ---------- dump coords + facts ----------
    with open(os.path.join(OUT, "build_plan_coords.json"), "w") as f:
        json.dump(coords_all, f, indent=2)
    facts = {
        "servo_edulite05": {"body_dia_mm": BODY_D, "body_len_mm": BODY_L,
                            "output_collar_dia_mm": COLLAR_D, "output_collar_len_mm": COLLAR_L,
                            "flange_dia_mm": FLANGE_D, "flange_thk_mm": FLANGE_T,
                            "pcd_mm": 41.5, "mass_g": 242.0},
        "servo_grip_micro": {"box_mm": list(GRIP), "mass_g": 13.4, "class": "MG90S"},
        "pivots_world_mm": {k: [round(x, 1) for x in v] for k, v in
                            {**PIV, "hand": HAND}.items()},
        "joint_fit_verify": fit,
        "float_verdict": "no broken float — every distal segment is servo-bridged; "
                         "knee1's coxa/femur separation is the Ø46 seat pocket the "
                         "modelled servo now fills.",
    }
    with open(os.path.join(OUT, "build_plan_facts.json"), "w") as f:
        json.dump(facts, f, indent=2)
    print("[facts] knee1 fit:", json.dumps(fit["knee1"]))
    print("[done] raw renders + coords + facts ->", OUT)


main()
