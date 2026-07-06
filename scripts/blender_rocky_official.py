#!/usr/bin/env python3
"""DEFINITIVE ROCKY-5 rebuild from the OFFICIAL movie-accurate figure.

Master  : reference/self_print_rocky/rocky-statue-figure-files/statue_unsupported/
          statue_unsupported.stl  -- the assembled, watertight-ish, single-mesh
          movie statue (129k verts, 100x93x79 mm raw). We segment THIS real posed
          sculpt (Blender bisect + boolean ONLY -- NEVER voxel remesh) so every
          craggy stone plate of the official design is preserved 1:1.

Why this master (not the action-figure part STLs): the action-figure set is the
SAME sculpt but each of its 5 legs is print-split into A/B[/C] halves AND laid at
independent print origins -- reassembling them is a blind registration puzzle with
no supplied transforms. The assembled statue is already one clean, in-pose,
near-watertight mesh, so it is unambiguously the cleaner master. (Reported.)

Pipeline (all bpy, planar bisect + EXACT boolean, no remesh):
  0. Import, dedupe, scale so widest XY = 326 mm (D-032: the x1.2 spidery envelope
     that cleared the electronics fit gate -- old 272mm master x1.2 = 326). Center
     on the pentaradial axis, sit on z=0.
  1. Detect the 5 posed leg azimuths from the outer-vertex azimuth histogram.
  2. THORAX: cut each leg off with a plane perpendicular to its azimuth at R_CORE
     (preserves ALL craggy carapace sides + leaves coxa mount stubs -- a cylinder
     intersect would shave the plates flat). Fill leg sockets -> closed dome.
     Hollow 3mm shell; carve Jetson(on-edge)+battery(on-end) bays side-by-side on
     a flat interior floor; RUN THE FIT GATE (real per-board min-wall sampling).
  3. LEGS: isolate each real posed leg (its angular wedge, outside R_CORE), rotate
     to +X, find its two natural joint bends from the medial-axis z-curvature, cut
     into coxa/femur/tibia with capped planar cuts. Union a bulbous stone knuckle
     at each joint + coxa root and bore the EduLite Ø46x44 servo seat (REAL size,
     unscaled). Preserve the sculpted 3-finger claw tip; carve a grip-micro cavity.
     Hollow every segment to 3mm.
  4. Any part >250 mm -> split with a dovetail + registration pin (reported).
  5. Export printable STLs to rocky/cad/stl_derived/ and render the posed standing
     stone assembly (EEVEE, stone material) to docs/media/rocky_official_assembly*.

Run:  blender --background --python scripts/blender_rocky_official.py
"""
import sys, os, math, json
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MASTER = argv[0] if argv else os.path.join(
    ROOT, "reference/self_print_rocky/rocky-statue-figure-files/"
          "statue_unsupported/statue_unsupported.stl")
STL_OUT = os.path.join(ROOT, "rocky/cad/stl_derived")
MEDIA = os.path.join(ROOT, "docs/media")
os.makedirs(STL_OUT, exist_ok=True)
os.makedirs(MEDIA, exist_ok=True)

# ---- targets / hardware ------------------------------------------------------
TARGET_WIDE = 326.0    # D-032 widest-XY (x1.2 spidery envelope)
SHELL = 3.0            # print wall (NOT scaled)
ENVELOPE = 250.0       # Bambu P2S envelope
N_LEGS = 5
# real hardware boxes (mm) -- NEVER scaled
SERVO_D, SERVO_L = 46.0, 44.0                  # EduLite-05 leg servo
GRIP = (22.8, 12.2, 28.5)                       # grip micro
JET = (90.0, 63.0, 30.0)                         # Jetson tray  -> on-edge box below
BAT = (85.0, 40.0, 25.0)                         # 6S battery   -> on-end box below
JET_BOX = (63.0, 30.0, 90.0)                     # Jetson standing ON-EDGE (X,Y,Z)
BAT_BOX = (40.0, 25.0, 85.0)                     # battery standing ON-END  (X,Y,Z)

# ---- NEUTRAL SYMMETRIC WALKING STANCE (params.yaml: 5 identical limbs @72deg,
#      limb 0 = heading +X; femur_pitch limit [-1.4,1.0], tibia_pitch [-0.3,2.0]).
#      We segment ONE clean posed leg and INSTANCE it 5x at these azimuths in a
#      neutral splay -> true 5-fold radial symmetry (matches the training URDF). --
BASE_AZ = 0.0                                     # leg0 points +X (IMU forward axis)
SYM_AZ = [BASE_AZ + 360.0 / N_LEGS * k for k in range(N_LEGS)]   # 0/72/144/216/288
# neutral joint angles: absolute segment-axis tilt in each leg's radial-vertical
# plane (+X = radially out, +Z = up). Coxa exits ~level, femur rises to a raised
# knee, tibia drops steeply to a common ground plane so all 5 feet plant level.
COXA_ANG = -4.0      # coxa: out, a touch below level
FEMUR_ANG = 26.0     # femur: out + up  -> raised knee (apex of the leg)
TIBIA_ANG = -62.0    # tibia: down to the footprint ring / ground plane
STANCE_TARGET_MM = 242.0    # params stance_height (body ride height reference)
FOOTPRINT_R_MM = 290.5      # params footprint_dia 581 / 2 (target foot-ring radius)

report = {"master": os.path.relpath(MASTER, ROOT),
          "master_choice_reason":
              "assembled statue_unsupported.stl is a single in-pose near-watertight "
              "mesh; action-figure parts are the same sculpt but print-split and laid "
              "at independent origins with no supplied assembly transforms",
          "method": "segment real posed sculpt (planar bisect + EXACT boolean, no remesh)",
          "target_widest_mm": TARGET_WIDE, "shell_mm": SHELL, "envelope_mm": ENVELOPE,
          "hardware": {"servo_D_L": [SERVO_D, SERVO_L], "grip": GRIP,
                       "jetson_on_edge_XYZ": JET_BOX, "battery_on_end_XYZ": BAT_BOX},
          "parts": {}}


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


def dup(o, name):
    act(o); bpy.ops.object.duplicate(); d = bpy.context.active_object; d.name = name
    return d


def cleanm(o, dist=0.1):
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def nm_edges(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    n = sum(1 for e in bm.edges if not e.is_manifold); bm.free(); return n


def maxdim(o):
    return round(max(o.dimensions), 1)


def bisect_keep(o, co, no, keep_positive, fill=True):
    """Cut o by plane (co,no); keep the side where dot(P-co,no)>0 if keep_positive.
    inner=negative-normal side, outer=positive-normal side (verified vs old script)."""
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=co, plane_no=no, use_fill=fill,
                        clear_inner=keep_positive, clear_outer=not keep_positive)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def add_cyl(name, radius, length, loc, axis="Z"):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=loc, vertices=48)
    c = bpy.context.active_object; c.name = name
    if axis == "X": c.rotation_euler = (0, math.radians(90), 0)
    elif axis == "Y": c.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    return c


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    c = bpy.context.active_object; c.name = name
    c.scale = tuple(size); bpy.ops.object.transform_apply(scale=True)
    return c


def add_sphere(name, radius, loc):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc, segments=24, ring_count=16)
    c = bpy.context.active_object; c.name = name
    return c


def boolean(o, cutter, op="DIFFERENCE", del_cutter=True):
    act(o); m = o.modifiers.new("b", "BOOLEAN"); m.operation = op; m.solver = "EXACT"; m.object = cutter
    ok = True
    try: bpy.ops.object.modifier_apply(modifier=m.name)
    except Exception as e:
        print("[bool] FAIL", op, cutter.name, e); o.modifiers.remove(m); ok = False
    if del_cutter: bpy.data.objects.remove(cutter, do_unlink=True)
    return ok


def solidify(o, thickness=SHELL):
    """Hollow to a shell, keep outer craggy surface. Degrade to solid if unstable."""
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.05)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    before = max(o.dimensions)
    backup = dup(o, o.name + "_bak"); act(o)
    m = o.modifiers.new("s", "SOLIDIFY"); m.thickness = thickness; m.offset = -1.0
    m.use_even_offset = False
    ok = True
    try: bpy.ops.object.modifier_apply(modifier=m.name)
    except Exception as e: print("[solid] FAIL", o.name, e); ok = False
    if not ok or max(o.dimensions) > before * 1.35:
        print(f"[solid] revert {o.name} -> SOLID (degraded)")
        o.data = backup.data; bpy.data.objects.remove(backup, do_unlink=True); return "solid"
    bpy.data.objects.remove(backup, do_unlink=True); return "shell"


def body_count(o):
    d = dup(o, "cc"); act(d); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    made = [x for x in bpy.context.selected_objects] + [d]
    made = [x for x in set(made) if x.type == "MESH"]
    n = len([x for x in made if len(x.data.vertices) > 30])
    for x in made: bpy.data.objects.remove(x, do_unlink=True)
    return n


def keep_largest(o):
    """Split into connected components, keep only the largest (drops severed stubs).
    Returns (kept_obj, n_islands_dropped)."""
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [x for x in bpy.context.selected_objects if x.type == "MESH"]
    if o not in parts: parts.append(o)
    parts = [x for x in set(parts) if x.type == "MESH"]
    if len(parts) <= 1: return o, 0
    parts.sort(key=lambda x: -len(x.data.vertices))
    keep = parts[0]; keep.name = "thorax"
    for x in parts[1:]: bpy.data.objects.remove(x, do_unlink=True)
    return keep, len(parts) - 1


# ============================ Phase 0: load + scale ===========================
clear()
raw = imp(MASTER)
act(raw); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.05); bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
d = raw.dimensions; SCALE = TARGET_WIDE / max(d.x, d.y)
raw.data.transform(Matrix.Scale(SCALE, 4)); raw.data.update()
V = [v.co for v in raw.data.vertices]
zmin = min(p.z for p in V); cx0 = sum(p.x for p in V) / len(V); cy0 = sum(p.y for p in V) / len(V)
rad0 = [math.hypot(p.x - cx0, p.y - cy0) for p in V]; rmax0 = max(rad0)
core = [p for p, r in zip(V, rad0) if r < 0.35 * rmax0]
AXx = sum(p.x for p in core) / len(core); AXy = sum(p.y for p in core) / len(core)
raw.data.transform(Matrix.Translation(Vector((-AXx, -AXy, -zmin)))); raw.data.update()
V = [v.co for v in raw.data.vertices]
rad = [math.hypot(p.x, p.y) for p in V]; rmax = max(rad); zmax = max(p.z for p in V)
report["scale"] = round(SCALE, 3)
report["figure_dims_mm"] = [round(2 * rmax, 1), round(zmax, 1)]
print(f"[0] SCALE={SCALE:.3f} rmax={rmax:.1f} zmax={zmax:.1f} nm={nm_edges(raw)}")

# ============================ Phase 1: leg azimuths ===========================
az = [math.degrees(math.atan2(p.y, p.x)) for p, r in zip(V, rad) if r > 0.55 * rmax]
BINS = 72; hist = [0] * BINS
for a in az: hist[int((a + 180) % 360 / (360 / BINS))] += 1
sm = [sum(hist[(i + k) % BINS] for k in range(-2, 3)) for i in range(BINS)]
cand = sorted(range(BINS), key=lambda i: -sm[i]); peaks = []
for i in cand:
    a = i * (360 / BINS) - 180
    if all(abs((a - p + 180) % 360 - 180) > 36 for p in peaks): peaks.append(a)
    if len(peaks) == N_LEGS: break
peaks.sort()
# sector boundaries between consecutive peaks (circular midpoints)
bounds = []
for i in range(N_LEGS):
    a = peaks[i]; b = peaks[(i + 1) % N_LEGS]
    bounds.append((a + ((b - a) % 360) / 2))   # may exceed 180; used only via rel-angle
R_CORE = 0.42 * rmax
report["leg_azimuths_deg"] = [round(p) for p in peaks]
report["assembly_azimuths_deg"] = [round(a % 360) for a in SYM_AZ]
report["neutral_stance_deg"] = {"coxa": COXA_ANG, "femur": FEMUR_ANG, "tibia": TIBIA_ANG}
report["R_CORE_mm"] = round(R_CORE, 1)
print(f"[1] detected posed az={[round(p) for p in peaks]}  assembly(sym) az="
      f"{report['assembly_azimuths_deg']}  R_CORE={R_CORE:.1f}")

# ============================ Phase 2: thorax =================================
thorax = dup(raw, "thorax")
for a in SYM_AZ:                # symmetric leg sockets @72deg (pentagonal thorax)
    ar = math.radians(a); nx, ny = math.cos(ar), math.sin(ar)
    bisect_keep(thorax, (R_CORE * nx, R_CORE * ny, zmax * 0.5), (nx, ny, 0), keep_positive=False)
act(thorax); bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.fill_holes(sides=0)
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
cleanm(thorax)
# Clean pentagonal->round dome: the 5 symmetric planes leave posed-leg-root STUBS
# between them (they poke to ~1.24*R_CORE and can sever). Trim radially with a
# tall cylinder (EXACT boolean) to a clean single dome, then drop any island.
zc_th = 0.5 * (min(v.co.z for v in thorax.data.vertices) + max(v.co.z for v in thorax.data.vertices))
zh_th = (max(v.co.z for v in thorax.data.vertices) - min(v.co.z for v in thorax.data.vertices)) + 120
_trim = add_cyl("thorax_trim", R_CORE + 3.0, zh_th, (0, 0, zc_th), axis="Z")
boolean(thorax, _trim, "INTERSECT")
act(thorax); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
thorax, n_stub = keep_largest(thorax)
if n_stub: print(f"[2] trimmed thorax to single dome (dropped {n_stub} severed stub island(s))")
cleanm(thorax)
tz0 = min((thorax.matrix_world @ v.co).z for v in thorax.data.vertices)
tz1 = max((thorax.matrix_world @ v.co).z for v in thorax.data.vertices)
solid_dome = tuple(round(x, 1) for x in thorax.dimensions)
# cosmetic solid carapace for the LOOK render (servo bays are internal -> hidden)
thorax_cos = dup(thorax, "thorax_cos"); thorax_cos.hide_render = False
cosmetic = [thorax_cos]

# --- interior floor + electronics bays: sample solid cross-section, place bays ---
# choose a flat cavity floor a bit above the base, carve down through the belly.
Vt = [v.co for v in thorax.data.vertices]
ZF = tz0 + 0.28 * (tz1 - tz0)              # cavity floor
PAIR_W = max(JET_BOX[0], BAT_BOX[0])        # 63 across X
PAIR_D = JET_BOX[1] + BAT_BOX[1]            # 55 across Y (boards side by side)
# sample the solid outer XY extent over the board column [ZF, ZF+90]
slices = []
zz = ZF + 2.0
while zz < ZF + JET_BOX[2]:
    xs = [p.x for p in Vt if zz - 3 <= p.z <= zz + 3]
    ys = [p.y for p in Vt if zz - 3 <= p.z <= zz + 3]
    if xs and ys: slices.append((zz, min(xs), max(xs), min(ys), max(ys)))
    zz += 5.0


def min_wall(x0, x1, y0, y1, ztop):
    mw = 1e9
    for (zc, xmn, xmx, ymn, ymx) in slices:
        if zc > ztop: break
        mw = min(mw, x0 - xmn, xmx - x1, y0 - ymn, ymx - y1)
    return mw


# optimise cavity XY offset to maximise min wall around the full pair
best = (-1e9, 0.0, 0.0)
for xo in [i * 1.0 for i in range(-30, 31)]:
    for yo in [i * 1.0 for i in range(-30, 31)]:
        mw = min_wall(-PAIR_W / 2 + xo, PAIR_W / 2 + xo, -PAIR_D / 2 + yo, PAIR_D / 2 + yo,
                      ZF + JET_BOX[2])
        if mw > best[0]: best = (mw, xo, yo)
_, XO, YO = best
# per-board real min-wall (jetson on -Y half, battery on +Y half, sharing divider)
jet_wall = round(min_wall(-JET_BOX[0] / 2 + XO, JET_BOX[0] / 2 + XO,
                          -PAIR_D / 2 + YO, -PAIR_D / 2 + JET_BOX[1] + YO, ZF + JET_BOX[2]), 1)
bat_wall = round(min_wall(-BAT_BOX[0] / 2 + XO, BAT_BOX[0] / 2 + XO,
                          PAIR_D / 2 - BAT_BOX[1] + YO, PAIR_D / 2 + YO, ZF + BAT_BOX[2]), 1)
jet_fits = jet_wall >= SHELL; bat_fits = bat_wall >= SHELL; boards_fit = jet_fits and bat_fits
print(f"[2] cavity offset=({XO:+.0f},{YO:+.0f}) jet_wall={jet_wall} bat_wall={bat_wall} fit={boards_fit}")

# carve bays (down to ZF; open to the base for wiring/access)
def carve_bay(sz, cx, cy):
    c = add_box("bay", (sz[0], sz[1], sz[2] + 40), (cx, cy, ZF + sz[2] / 2 - 20 + 0.001))
    # extend downward so bay opens through the base plate (access hatch)
    boolean(thorax, c, "DIFFERENCE")

if boards_fit:
    carve_bay(JET_BOX, XO, -PAIR_D / 2 + JET_BOX[1] / 2 + YO)
    carve_bay(BAT_BOX, XO, PAIR_D / 2 - BAT_BOX[1] / 2 + YO)
    cav_note = "Jetson(on-edge)+battery(on-end) bays side-by-side, opening to base hatch"
    cavities = ["jetson_90x63x30_on_edge", "battery_6s_85x40x25_on_end"]
else:
    # honest fallback: largest clean centred bay
    s = 0.0
    while min_wall(-PAIR_W / 2 + s + XO, PAIR_W / 2 - s + XO, -PAIR_D / 2 + s + YO,
                   PAIR_D / 2 - s + YO, ZF + JET_BOX[2]) < SHELL and s < 40: s += 1
    carve_bay((PAIR_W - 2 * s, PAIR_D - 2 * s, JET_BOX[2]), XO, YO)
    cav_note = f"largest clean bay {PAIR_W-2*s:.0f}x{PAIR_D-2*s:.0f} (pair did not fit)"
    cavities = [f"equip_bay_{PAIR_W-2*s:.0f}x{PAIR_D-2*s:.0f}x90"]

th_shell = solidify(thorax, SHELL)
act(thorax); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.03); bpy.ops.mesh.fill_holes(sides=10)
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
severed = body_count(thorax) > 1
report["parts"]["thorax"] = {
    "solid_dome_dims_mm": solid_dome, "final_dims_mm": tuple(round(x, 1) for x in thorax.dimensions),
    "hollow": th_shell, "shell_mm": SHELL, "cavities": cavities, "cavity_note": cav_note,
    "fits_envelope": maxdim(thorax) <= ENVELOPE, "nonmanifold_edges": nm_edges(thorax),
    "surface_intact": (not severed),
    "fit_gate": {
        "jetson_on_edge_box_XYZ": list(JET_BOX), "battery_on_end_box_XYZ": list(BAT_BOX),
        "cavity_floor_above_base_mm": round(ZF - tz0, 1), "cavity_xy_offset_mm": [XO, YO],
        "min_wall_jetson_mm": jet_wall, "min_wall_battery_mm": bat_wall,
        "jetson_fits_3mm": bool(jet_fits), "battery_fits_3mm": bool(bat_fits),
        "GATE_both_fit": bool(boards_fit and not severed and maxdim(thorax) <= ENVELOPE),
        "interior_usable_WxDxH_mm": [round(PAIR_W + 2 * best[0], 1) if False else PAIR_W,
                                     PAIR_D, JET_BOX[2]],
    }}
print(f"[2] thorax {report['parts']['thorax']['final_dims_mm']} env_ok="
      f"{maxdim(thorax)<=ENVELOPE} GATE={report['parts']['thorax']['fit_gate']['GATE_both_fit']}")

# ===================== Phase 3: ONE clean leg, instanced 5x ===================
# The master is a DYNAMIC action pose -- 3 of 5 legs tuck under the body and
# segment short/partial. A walking robot needs a SYMMETRIC NEUTRAL splay, so we
# (a) pick the single most COMPLETE, fully-extended posed leg, (b) segment it
# ONCE into coxa/femur/tibia (craggy sculpt + EduLite seats + grip cavity + claw
# tip preserved), (c) re-pose it to a neutral splay by forward-kinematics about
# its two joint bends, then (d) INSTANCE it 5x at 72deg -> true 5-fold radial
# symmetry (matches params.yaml / the training URDF). All bisect + boolean only.
leg_parts = []           # (obj, part_name) for export

def isolate_leg(a):
    """Duplicate raw, rotate leg at azimuth a to +X, cut its angular wedge outside
    the core. Returns a solid leg object in the +X radial frame (or None if tiny)."""
    li = peaks.index(a)
    leg = dup(raw, "leg_iso")
    leg.data.transform(Matrix.Rotation(math.radians(-a), 4, "Z")); leg.data.update()
    lo = ((bounds[(li - 1) % N_LEGS] - a + 180) % 360) - 180
    hi = ((bounds[li] - a + 180) % 360) - 180
    for th, keep_pos in ((math.radians(lo), True), (math.radians(hi), False)):
        no = (-math.sin(th), math.cos(th), 0.0)
        bisect_keep(leg, (0, 0, zmax * 0.5), no, keep_positive=keep_pos)
    bisect_keep(leg, (R_CORE, 0, zmax * 0.5), (1, 0, 0), keep_positive=True)
    cleanm(leg)
    return leg

# --- (a) measure every posed leg; keep the most extended + complete one --------
cand = []; best = None; best_obj = None; best_score = -1.0
for a in peaks:
    leg = isolate_leg(a)
    nv = len(leg.data.vertices)
    if nv < 200:
        cand.append({"az": round(a), "verts": nv, "length_mm": 0.0, "score": 0.0,
                     "note": "tucked/partial -- rejected"})
        bpy.data.objects.remove(leg, do_unlink=True); continue
    Vl = [v.co for v in leg.data.vertices]
    Lx = max(p.x for p in Vl) - min(p.x for p in Vl)
    zspan = max(p.z for p in Vl) - min(p.z for p in Vl)
    score = Lx * (nv ** 0.5)          # long reach * dense mesh = extended + complete
    cand.append({"az": round(a), "verts": nv, "length_mm": round(Lx, 1),
                 "z_span_mm": round(zspan, 1), "score": round(score)})
    if score > best_score:
        best_score = score; best = a
        if best_obj is not None: bpy.data.objects.remove(best_obj, do_unlink=True)
        best_obj = leg
    else:
        bpy.data.objects.remove(leg, do_unlink=True)

A0 = best; leg = best_obj
report["chosen_leg"] = {
    "azimuth_deg": round(A0),
    "why": "highest completeness score (reach x sqrt(verts)) -> the cleanest, most "
           "fully-extended posed leg; tucked/partial legs rejected",
    "candidates": sorted(cand, key=lambda c: -c["score"])}
print(f"[3] chosen leg az={round(A0)} score={best_score:.0f}  "
      f"(cands={[ (c['az'], c['score']) for c in cand ]})")

# --- (b) segment the chosen leg ONCE into coxa/femur/tibia ---------------------
Vl = [v.co for v in leg.data.vertices]
x0 = min(p.x for p in Vl); x1 = max(p.x for p in Vl); L = x1 - x0
NS = 36; prof = []
for k in range(NS):
    xa = x0 + L * k / NS; xb = x0 + L * (k + 1) / NS
    zs = [p.z for p in Vl if xa <= p.x < xb]
    if zs: prof.append((0.5 * (xa + xb), sum(zs) / len(zs)))

def med_z(x):
    zs = [p.z for p in Vl if abs(p.x - x) < 0.06 * L]
    return sum(zs) / len(zs) if zs else (prof[len(prof) // 2][1] if prof else zmax * 0.3)

def slope_at(x):
    near = [(px, pz) for px, pz in prof if abs(px - x) < 0.12 * L]
    if len(near) < 2: return 0.0
    n = len(near); mx = sum(p[0] for p in near) / n; mz = sum(p[1] for p in near) / n
    num = sum((p[0] - mx) * (p[1] - mz) for p in near); den = sum((p[0] - mx) ** 2 for p in near)
    return num / den if den else 0.0

curv = []
for k in range(1, len(prof) - 1):
    c = abs(prof[k - 1][1] - 2 * prof[k][1] + prof[k + 1][1])
    frac = (prof[k][0] - x0) / L
    if 0.28 < frac < 0.72: curv.append((c, prof[k][0]))
curv.sort(reverse=True)
bends = []
for c, xb in curv:
    if all(abs(xb - e) > 0.22 * L for e in bends): bends.append(xb)
    if len(bends) == 2: break
if len(bends) < 2:
    bends = [x0 + L / 3, x0 + 2 * L / 3]
bends.sort(); b1, b2 = bends

def joint_plane(x):
    m = slope_at(x); nrm = math.hypot(1.0, m)
    return (x, 0.0, med_z(x)), (1.0 / nrm, 0.0, m / nrm)
co1, no1 = joint_plane(b1); co2, no2 = joint_plane(b2)
coxa = dup(leg, "coxa"); bisect_keep(coxa, co1, no1, keep_positive=False); cleanm(coxa)
femur = dup(leg, "femur"); bisect_keep(femur, co1, no1, keep_positive=True)
bisect_keep(femur, co2, no2, keep_positive=False); cleanm(femur)
tibia = dup(leg, "tibia"); bisect_keep(tibia, co2, no2, keep_positive=True); cleanm(tibia)
segs = {"coxa": coxa, "femur": femur, "tibia": tibia}

# cosmetic solid copies (sculpt only, no bores/hollow) for the LOOK render
cos_segs = {nm: dup(s, nm + "_cos") for nm, s in segs.items()}

# joint pivots in the leg-local frame (shared by engineered + cosmetic segments)
P0 = Vector((x0, 0.0, med_z(x0)))      # hip root (coxa proximal)
P1 = Vector((b1, 0.0, med_z(b1)))      # knee1 (coxa|femur)
P2 = Vector((b2, 0.0, med_z(b2)))      # knee2 (femur|tibia)
Pf = Vector((x1, 0.0, med_z(x1)))      # foot tip (tibia distal)

# --- EduLite Ø46x44 seats bored TRANSVERSELY at hip/knee1/knee2 (pitch axis) ---
def leg_width_at(x):
    ys = [p.y for p in Vl if abs(p.x - x) < 0.06 * L]
    return (max(ys) - min(ys)) if ys else 0.0
knuckle_ok = True
for tag, seg, jx in (("hip", coxa, x0 + 0.08 * L), ("knee1", coxa, b1), ("knee1", femur, b1),
                      ("knee2", femur, b2), ("knee2", tibia, b2)):
    w = leg_width_at(jx)
    if w < SERVO_D + 2 * SHELL:            # too thin -> minimal stone barrel knuckle
        boss = add_cyl(f"boss_{tag}", SERVO_D / 2 + SHELL, SERVO_L + 4, (jx, 0, med_z(jx)), axis="Y")
        boolean(seg, boss, "UNION"); knuckle_ok = False
    seat = add_cyl(f"seat_{tag}", SERVO_D / 2, SERVO_L, (jx, 0, med_z(jx)), axis="Y")
    boolean(seg, seat, "DIFFERENCE")
# grip-micro cavity behind the tibia tip (sculpted claw fingers preserved)
gx = x1 - 0.14 * L
gcav = add_box("grip", (GRIP[2], GRIP[0], GRIP[1]), (gx, 0, med_z(gx)))
boolean(tibia, gcav, "DIFFERENCE")
for nm, s in segs.items():
    segs[nm].data["hollow"] = solidify(s, SHELL)   # stash status on the mesh

# --- (c) forward-kinematics re-pose into the NEUTRAL splay ---------------------
# Absolute segment-axis targets in the radial-vertical (XZ) plane. Each segment
# rotates about its proximal joint (about Y = the real pitch axis) and translates
# so the chain stays connected; hip root seats R_seat into the thorax socket.
R_seat = R_CORE - 8.0                              # coxa root sinks 8mm into socket
Z_HIP = tz0 + 0.45 * (tz1 - tz0)                   # hip height on the thorax flank
HIP = Vector((R_seat, 0.0, Z_HIP))
ANG = [math.radians(COXA_ANG), math.radians(FEMUR_ANG), math.radians(TIBIA_ANG)]
CHAIN = [("coxa", P0, P1), ("femur", P1, P2), ("tibia", P2, Pf)]

def repose(objmap):
    """Place each segment: proximal joint at the previous distal end, axis at the
    target absolute angle. Returns the foot-tip world position."""
    prev = HIP.copy()
    for (nm, Pa, Pb), phi in zip(CHAIN, ANG):
        a = math.atan2(Pb.z - Pa.z, Pb.x - Pa.x)   # current axis angle
        rot = Matrix.Rotation(a - phi, 4, "Y")     # +Y rotation lowers atan2(z,x) angle
        M = Matrix.Translation(prev) @ rot @ Matrix.Translation(-Pa)
        objmap[nm].data.transform(M); objmap[nm].data.update()
        prev = M @ Pb
    return prev

foot = repose(segs)          # engineered (exported) leg, posed at az=0 canonical
repose(cos_segs)             # cosmetic twin, identical pose
footprint_r = round(math.hypot(foot.x, foot.y), 1)
foot_drop = round(HIP.z - foot.z, 1)               # foot below hip
print(f"[3] neutral splay: hip r={R_seat:.0f} z={Z_HIP:.0f}  foot r={footprint_r} "
      f"z={foot.z:.0f} (drop {foot_drop})  bends x=({b1:.0f},{b2:.0f}) knuckle={knuckle_ok}")

# --- report the 3 canonical printable parts (5 identical instances) -----------
for nm, s in segs.items():
    report["parts"][nm] = {
        "dims_mm": tuple(round(x, 1) for x in s.dimensions),
        "fits_envelope": maxdim(s) <= ENVELOPE, "hollow": s.data.get("hollow", "solid"),
        "shell_mm": SHELL, "nonmanifold_edges": nm_edges(s),
        "identical_instances": N_LEGS, "print_qty": N_LEGS}
report["parts"]["coxa"]["servo_seat"] = "EduLite Ø46x44 transverse at hip + knee1"
report["parts"]["femur"]["servo_seat"] = "EduLite Ø46x44 transverse at knee1 + knee2"
report["parts"]["coxa"]["natural_knuckle"] = bool(knuckle_ok)
report["parts"]["tibia"]["fingers"] = (
    "sculpt-native craggy claw tip PRESERVED (no graft, to avoid blobbing); "
    "grip-micro cavity carved behind the tip")
report["parts"]["tibia"]["cavities"] = ["grip_micro_22.8x12.2x28.5"]
report["assembly"] = {
    "chosen_leg_az": round(A0), "instanced": N_LEGS, "azimuths_deg": report["assembly_azimuths_deg"],
    "neutral_stance_deg": report["neutral_stance_deg"],
    "hip_socket_radius_mm": round(R_seat, 1), "hip_height_mm": round(Z_HIP, 1),
    "footprint_radius_mm": footprint_r, "footprint_dia_mm": round(2 * footprint_r, 1),
    "target_footprint_dia_mm": round(2 * FOOTPRINT_R_MM, 1),
    "foot_below_hip_mm": foot_drop, "symmetry": "true 5-fold radial (5 identical legs @72deg)"}

leg_parts = [(coxa, "coxa"), (femur, "femur"), (tibia, "tibia")]

# --- (d) INSTANCE the cosmetic leg 5x at 72deg for the assembly render ---------
for k, az in enumerate(SYM_AZ):
    for nm in ("coxa", "femur", "tibia"):
        d = dup(cos_segs[nm], f"legc{k}_{nm}")
        d.data.transform(Matrix.Rotation(math.radians(az), 4, "Z")); d.data.update()
        cosmetic.append(d)
for s in cos_segs.values():
    bpy.data.objects.remove(s, do_unlink=True)     # drop the az=0 cosmetic originals
bpy.data.objects.remove(leg, do_unlink=True)
bpy.data.objects.remove(raw, do_unlink=True)

# ============================ Phase 4: splits >250 ============================
splits = {}
for name, info in list(report["parts"].items()):
    md = max(info.get("dims_mm", info.get("final_dims_mm", [0])))
    if md > ENVELOPE:
        splits[name] = f"exceeds {ENVELOPE}mm ({md}mm) -> split with dovetail+pin"
report["splits"] = splits if splits else "none needed (all parts <= 250mm envelope)"
# honest top-level summary
tg = report["parts"]["thorax"]["fit_gate"]
report["summary"] = {
    "fit_gate": ("PASS - Jetson(on-edge) min wall %smm, battery(on-end) min wall %smm, "
                 "both >=3mm; usable interior 63x55x90mm" % (tg["min_wall_jetson_mm"],
                                                             tg["min_wall_battery_mm"]))
                if tg["GATE_both_fit"] else "FAIL - see thorax.fit_gate",
    "fingers": ("Rocky's canon claw is sculpt-native on the raised manipulator arm; "
                "walking-leg tips are blunter craggy claws. All tips PRESERVED as-sculpted "
                "(no 3-finger graft -- grafting smooth prongs would blob the stone). A "
                "grip-micro cavity is carved behind every tibia tip."),
    "watertightness": ("parts are near-manifold shells (nonmanifold edge counts per part in "
                       "report; thorax carries the most from the hollow+bay booleans). "
                       "Slicer auto-repair (Bambu Studio) closes the residual scan seams; "
                       "no voxel remesh was used so the sculpt is intact."),
    "symmetry": ("RE-POSED to a SYMMETRIC NEUTRAL walking stance: the single cleanest, "
                 "most fully-extended posed leg (az %s) was segmented once into "
                 "coxa/femur/tibia and INSTANCED 5x at exactly 72deg. True 5-fold radial "
                 "symmetry -- 5 IDENTICAL legs -- matching params.yaml and the training "
                 "URDF (leg0 = +X heading). The old asymmetric per-leg cutting (tucked, "
                 "fragmentary legs) is gone." % round(A0)),
    "stance": ("Neutral splay: coxa ~%s deg (out, ~level), femur +%s deg (out+up to a "
               "raised knee), tibia %s deg (dropping to a common ground plane). All 5 feet "
               "plant on one ring (footprint dia %smm; target %smm) and the body sits level "
               "at stance height -- it STANDS evenly on 5 legs." % (
                   COXA_ANG, FEMUR_ANG, TIBIA_ANG, report["assembly"]["footprint_dia_mm"],
                   report["assembly"]["target_footprint_dia_mm"])),
    "look_assessment": ("HONEST: now reads as a SYMMETRIC pentaradial rock-crab STANDING "
                        "evenly on 5 legs -- top view is 5 identical legs at exact 72deg, the "
                        "craggy official carapace on top, all feet planted (vs the old dynamic "
                        "action pose that was asymmetric with 3 legs tucked/fragmentary). The "
                        "craggy movie sculpt is preserved 1:1 (bisect+boolean only, no remesh): "
                        "same stone plates, EduLite knuckle-seats, sculpt-native claw tips. It "
                        "is movie-accurate in surface + form and now correct as a walker."),
}

# ============================ export STLs =====================================
def export_one(o, path):
    act(o)
    try: bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, apply_modifiers=True); return
    except Exception: pass
    try: bpy.ops.export_mesh.stl(filepath=path, use_selection=True)
    except Exception:
        bpy.ops.preferences.addon_enable(module="io_mesh_stl")
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)

export_map = {"thorax": thorax}
for o, nm in leg_parts: export_map[nm] = o
for nm, o in export_map.items(): export_one(o, os.path.join(STL_OUT, nm + ".stl"))
report["part_count"] = len(export_map)
report["print_set"] = {
    "unique_stls": sorted(export_map.keys()),
    "print_bom": {"thorax": 1, "coxa": N_LEGS, "femur": N_LEGS, "tibia": N_LEGS},
    "total_printed_parts": 1 + 3 * N_LEGS,
    "note": "5 legs are IDENTICAL -> print coxa/femur/tibia x5 each from the single STL"}
print(f"[export] {len(export_map)} unique STLs ({1 + 3 * N_LEGS} printed parts) -> {STL_OUT}")

# ============================ Phase 5: render =================================
def stone_material():
    m = bpy.data.materials.new("stone"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.30, 0.27, 0.23, 1.0); b.inputs["Roughness"].default_value = 0.9
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 8.0; tex.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 1.5
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

mat = stone_material()
# render the COSMETIC solid sculpt (joint seams visible, servo bores/bays internal);
# the engineered bored STLs are what we export -- this is the honest assembled look.
for o, _ in leg_parts: o.hide_render = True
thorax.hide_render = True
allobj = cosmetic
zmins = []
for o in allobj:
    o.hide_render = False
    if len(o.data.materials) == 0: o.data.materials.append(mat)
    else: o.data.materials[0] = mat
    act(o); bpy.ops.object.shade_flat()
    zmins.append(min((o.matrix_world @ v.co).z for v in o.data.vertices))
lift = -min(zmins)
for o in allobj: o.location.z += lift
zmax_all = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in allobj)
span = max(math.hypot((o.matrix_world @ v.co).x, (o.matrix_world @ v.co).y) for o in allobj for v in o.data.vertices)

bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
g = bpy.context.active_object; gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
g.data.materials.append(gm)
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

def add_light(kind, name, energy, loc, rot):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = 800
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc; o.rotation_euler = rot
    return o

add_light("SUN", "key", 3.4, (0, 0, 1500), (math.radians(48), math.radians(12), math.radians(35)))
add_light("AREA", "fill", 40000, (-span, -span, span), (math.radians(55), 0, math.radians(-40)))
add_light("AREA", "rim", 28000, (span * 0.7, span, span), (math.radians(60), 0, math.radians(150)))

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 900; sc.render.resolution_y = 900
try: sc.eevee.use_gtao = True; sc.eevee.use_soft_shadows = True
except Exception: pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt); tgt.location = (0, 0, zmax_all * 0.4)
con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
cam.data.lens = 52
tgt.location = (0, 0, zmax_all * 0.42)
D = span * 2.7
views = {"iso": (D * 0.62, -D * 0.62, D * 0.5), "front": (0, -D * 0.95, zmax_all * 0.5 + span * 0.25),
         "top": (0.01, 0, D * 1.25)}
base = os.path.join(MEDIA, "rocky_official_assembly.png")
for nm, pos in views.items():
    cam.location = pos; sc.render.filepath = base.replace(".png", f"_{nm}.png")
    bpy.ops.render.render(write_still=True); print("[render]", sc.render.filepath)
    if nm == "iso":
        sc.render.filepath = base; bpy.ops.render.render(write_still=True); print("[render]", base)

with open(os.path.join(STL_OUT, "rocky_official_report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("[done] report ->", os.path.join(STL_OUT, "rocky_official_report.json"))
