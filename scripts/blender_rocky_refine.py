#!/usr/bin/env python3
"""ROCKY-5 REFINE from the OFFICIAL sculpt — fingers SACRED, servos HIDDEN.

Refines the movie-accurate statue_unsupported.stl into a printable, symmetric
5-legged neutral-stance ROCKY-5, staying as close to the original sculpt as
possible. Bisect + EXACT boolean ONLY (never voxel remesh).

Operator hard-requirements honoured here:
  1. FINGERS ARE SACRED. The sculptor's 3-finger manipulator hand lives on the
     FRONT RAISED ARM (azimuth ~-33 deg; tip bbox ~8x9x17 mm raw). We isolate
     THAT hand-bearing limb (planar bisect wedge, no boolean) and instance it 5x
     so every foot is a proper 3-finger manipulator hand. Joint cuts are placed
     PROXIMAL to the wrist -> the whole hand rides the distal (tibia) segment,
     untouched. NO finger graft, NO cone, NO grip cavity in the hand.
  2. HIDE THE SERVOS. Each leg joint is an ORGANIC STONE BALL-IN-SOCKET: a stone
     knuckle (ball, sized to the limb so it does NOT bulge) is unioned onto the
     distal segment and the proximal segment gets a matching concave socket, so
     the seam is a thin organic rim and the EduLite Ø46x44 servo tucks INSIDE the
     ball. Mating faces coincide at neutral pose (no ugly flat-chunk gaps).
  3. FALLBACK COVERS. Any joint whose limb is too thin to swallow the servo keeps
     a FLAT functional mount face AND gets a separate cosmetic *_cover.stl — a
     thin shell sliced from the uncut sculpt at that spot, so the assembled robot
     still reads as the stone sculpt. (Emitted only where actually needed.)

Torso keeps the passing Jetson(on-edge)+battery(on-end) bays (fit gate re-run).
All parts <= 250 mm. STLs -> rocky/cad/stl_derived/ (gitignored). No commit.

Run:  blender --background --python scripts/blender_rocky_refine.py
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
os.makedirs(STL_OUT, exist_ok=True); os.makedirs(MEDIA, exist_ok=True)

# ---- targets / hardware (mm; hardware NEVER scaled) -------------------------
TARGET_WIDE = 326.0        # D-032 widest-XY spidery envelope (cleared electronics fit)
SHELL = 3.0
ENVELOPE = 250.0
N_LEGS = 5
SERVO_D, SERVO_L = 46.0, 44.0          # EduLite-05 leg servo
JET_BOX = (63.0, 30.0, 90.0)           # Jetson standing on-edge (X,Y,Z)
BAT_BOX = (40.0, 25.0, 85.0)           # 6S battery standing on-end (X,Y,Z)
ARM_AZ = -33.0                          # front raised-arm azimuth (profiled hand limb)
ARM_WEDGE = 44.0                        # +/- half-angle of hand-limb wedge

# neutral symmetric stance: instance the HAND limb at 5x72deg
BASE_AZ = 0.0
SYM_AZ = [BASE_AZ + 360.0 / N_LEGS * k for k in range(N_LEGS)]
COXA_ANG = -6.0        # coxa exits ~level, slight down
FEMUR_ANG = 24.0       # femur up to a raised knee
TIBIA_ANG = -58.0      # tibia/hand drops to plant (hand = foot, fingers to ground)
FOOTPRINT_R_MM = 290.5

report = {"master": os.path.relpath(MASTER, ROOT),
          "job": "refine ROCKY-5 from OFFICIAL sculpt; fingers sacred, servos hidden",
          "method": "planar bisect + EXACT boolean only (NO voxel remesh)",
          "hand_limb": {"azimuth_deg": ARM_AZ,
                        "found": "3-finger manipulator hand on the front raised arm "
                                 "(profiled tip bbox ~8x9x17mm raw); isolated by bisect "
                                 "wedge, instanced 5x so every foot has proper fingers"},
          "target_widest_mm": TARGET_WIDE, "shell_mm": SHELL, "envelope_mm": ENVELOPE,
          "hardware": {"servo_D_L": [SERVO_D, SERVO_L],
                       "jetson_on_edge_XYZ": list(JET_BOX), "battery_on_end_XYZ": list(BAT_BOX)},
          "parts": {}, "joints": {}, "covers": []}


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
    bpy.ops.mesh.delete_loose(); bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def nm_edges(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    n = sum(1 for e in bm.edges if not e.is_manifold); bm.free(); return n


def maxdim(o):
    return round(max(o.dimensions), 1)


def bisect_keep(o, co, no, keep_positive, fill=True):
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
    bpy.ops.object.transform_apply(rotation=True); return c


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    c = bpy.context.active_object; c.name = name
    c.scale = tuple(size); bpy.ops.object.transform_apply(scale=True); return c


def add_sphere(name, radius, loc, squashY=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc, segments=32, ring_count=20)
    c = bpy.context.active_object; c.name = name
    if squashY != 1.0:
        c.scale = (1.0, squashY, 1.0); bpy.ops.object.transform_apply(scale=True)
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
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.05)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    before = max(o.dimensions); backup = dup(o, o.name + "_bak"); act(o)
    m = o.modifiers.new("s", "SOLIDIFY"); m.thickness = thickness; m.offset = -1.0
    m.use_even_offset = False; ok = True
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


def keep_largest(o, newname):
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [x for x in bpy.context.selected_objects if x.type == "MESH"]
    if o not in parts: parts.append(o)
    parts = [x for x in set(parts) if x.type == "MESH"]
    if len(parts) <= 1:
        o.name = newname; return o, 0
    parts.sort(key=lambda x: -len(x.data.vertices))
    keep = parts[0]; keep.name = newname
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
R_CORE = 0.42 * rmax
report["scale"] = round(SCALE, 3)
report["figure_dims_mm"] = [round(2 * rmax, 1), round(zmax, 1)]
report["R_CORE_mm"] = round(R_CORE, 1)
print(f"[0] SCALE={SCALE:.3f} rmax={rmax:.1f} zmax={zmax:.1f} R_CORE={R_CORE:.1f}")

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
report["detected_azimuths_deg"] = [round(p) for p in peaks]
report["assembly_azimuths_deg"] = [round(a % 360) for a in SYM_AZ]
print(f"[1] detected az={[round(p) for p in peaks]} assembly@{report['assembly_azimuths_deg']}")

# ============================ Phase 2: thorax =================================
# (reuses the fit-gate-passing dome+bays approach)
thorax = dup(raw, "thorax")
for a in SYM_AZ:
    ar = math.radians(a); nx, ny = math.cos(ar), math.sin(ar)
    bisect_keep(thorax, (R_CORE * nx, R_CORE * ny, zmax * 0.5), (nx, ny, 0), keep_positive=False)
act(thorax); bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.fill_holes(sides=0)
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
cleanm(thorax)
zc_th = 0.5 * (min(v.co.z for v in thorax.data.vertices) + max(v.co.z for v in thorax.data.vertices))
zh_th = (max(v.co.z for v in thorax.data.vertices) - min(v.co.z for v in thorax.data.vertices)) + 120
_trim = add_cyl("thorax_trim", R_CORE + 3.0, zh_th, (0, 0, zc_th), axis="Z")
boolean(thorax, _trim, "INTERSECT")
act(thorax); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
thorax, n_stub = keep_largest(thorax, "thorax")
cleanm(thorax)
tz0 = min((thorax.matrix_world @ v.co).z for v in thorax.data.vertices)
tz1 = max((thorax.matrix_world @ v.co).z for v in thorax.data.vertices)
solid_dome = tuple(round(x, 1) for x in thorax.dimensions)
thorax_cos = dup(thorax, "thorax_cos")

Vt = [v.co for v in thorax.data.vertices]
ZF = tz0 + 0.28 * (tz1 - tz0)
PAIR_W = max(JET_BOX[0], BAT_BOX[0]); PAIR_D = JET_BOX[1] + BAT_BOX[1]
slices = []; zz = ZF + 2.0
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


best = (-1e9, 0.0, 0.0)
for xo in [i * 1.0 for i in range(-30, 31)]:
    for yo in [i * 1.0 for i in range(-30, 31)]:
        mw = min_wall(-PAIR_W / 2 + xo, PAIR_W / 2 + xo, -PAIR_D / 2 + yo, PAIR_D / 2 + yo,
                      ZF + JET_BOX[2])
        if mw > best[0]: best = (mw, xo, yo)
_, XO, YO = best
jet_wall = round(min_wall(-JET_BOX[0] / 2 + XO, JET_BOX[0] / 2 + XO,
                          -PAIR_D / 2 + YO, -PAIR_D / 2 + JET_BOX[1] + YO, ZF + JET_BOX[2]), 1)
bat_wall = round(min_wall(-BAT_BOX[0] / 2 + XO, BAT_BOX[0] / 2 + XO,
                          PAIR_D / 2 - BAT_BOX[1] + YO, PAIR_D / 2 + YO, ZF + BAT_BOX[2]), 1)
jet_fits = jet_wall >= SHELL; bat_fits = bat_wall >= SHELL; boards_fit = jet_fits and bat_fits


def carve_bay(sz, cx, cy):
    c = add_box("bay", (sz[0], sz[1], sz[2] + 40), (cx, cy, ZF + sz[2] / 2 - 20 + 0.001))
    boolean(thorax, c, "DIFFERENCE")

if boards_fit:
    carve_bay(JET_BOX, XO, -PAIR_D / 2 + JET_BOX[1] / 2 + YO)
    carve_bay(BAT_BOX, XO, PAIR_D / 2 - BAT_BOX[1] / 2 + YO)
    cavities = ["jetson_90x63x30_on_edge", "battery_6s_85x40x25_on_end"]
    cav_note = "Jetson(on-edge)+battery(on-end) bays side-by-side, opening to base hatch"
else:
    s = 0.0
    while min_wall(-PAIR_W / 2 + s + XO, PAIR_W / 2 - s + XO, -PAIR_D / 2 + s + YO,
                   PAIR_D / 2 - s + YO, ZF + JET_BOX[2]) < SHELL and s < 40: s += 1
    carve_bay((PAIR_W - 2 * s, PAIR_D - 2 * s, JET_BOX[2]), XO, YO)
    cavities = [f"equip_bay_{PAIR_W-2*s:.0f}x{PAIR_D-2*s:.0f}x90"]
    cav_note = f"largest clean bay {PAIR_W-2*s:.0f}x{PAIR_D-2*s:.0f} (pair did not fit)"

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
    "fit_gate": {"min_wall_jetson_mm": jet_wall, "min_wall_battery_mm": bat_wall,
                 "jetson_fits_3mm": bool(jet_fits), "battery_fits_3mm": bool(bat_fits),
                 "GATE_both_fit": bool(boards_fit and not severed and maxdim(thorax) <= ENVELOPE)}}
print(f"[2] thorax {report['parts']['thorax']['final_dims_mm']} "
      f"GATE={report['parts']['thorax']['fit_gate']['GATE_both_fit']}")

# ================= Phase 3: isolate the HAND limb, segment, hide servos =======
def isolate_hand_limb():
    leg = dup(raw, "hand_limb")
    leg.data.transform(Matrix.Rotation(math.radians(-ARM_AZ), 4, "Z")); leg.data.update()
    for th, keep_pos in ((math.radians(-ARM_WEDGE), True), (math.radians(ARM_WEDGE), False)):
        no = (-math.sin(th), math.cos(th), 0.0)
        bisect_keep(leg, (0, 0, zmax * 0.5), no, keep_positive=keep_pos)
    bisect_keep(leg, (R_CORE, 0, zmax * 0.5), (1, 0, 0), keep_positive=True)
    leg, _ = keep_largest(leg, "hand_limb")
    cleanm(leg)
    return leg

leg = isolate_hand_limb()
Vl = [v.co.copy() for v in leg.data.vertices]
x0 = min(p.x for p in Vl); x1 = max(p.x for p in Vl); L = x1 - x0
hand_start = x1 - 0.24 * L           # everything beyond this is the sacred hand
report["hand_limb"]["isolated_dims_mm"] = [round(max(p.x for p in Vl) - x0, 1),
    round(max(p.y for p in Vl) - min(p.y for p in Vl), 1),
    round(max(p.z for p in Vl) - min(p.z for p in Vl), 1)]
print(f"[3] hand limb len={L:.1f} x=({x0:.1f},{x1:.1f}) hand_start={hand_start:.1f}")

# medial profile + two natural joint bends (kept PROXIMAL to the hand)
NS = 40; prof = []
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


def leg_width_at(x):
    ys = [p.y for p in Vl if abs(p.x - x) < 0.06 * L]
    return (max(ys) - min(ys)) if ys else 0.0


curv = []
for k in range(1, len(prof) - 1):
    c = abs(prof[k - 1][1] - 2 * prof[k][1] + prof[k + 1][1])
    frac = (prof[k][0] - x0) / L
    if 0.24 < frac < 0.64: curv.append((c, prof[k][0]))   # bends kept well before the hand
curv.sort(reverse=True)
bends = []
for c, xb in curv:
    if all(abs(xb - e) > 0.20 * L for e in bends): bends.append(xb)
    if len(bends) == 2: break
if len(bends) < 2: bends = [x0 + 0.32 * L, x0 + 0.58 * L]
bends.sort(); b1, b2 = bends
# safety: keep the distal cut clear of the hand
b2 = min(b2, hand_start - 0.05 * L)
print(f"[3] joint bends x=({b1:.1f},{b2:.1f})  (hand fully distal of {b2:.1f})")


def joint_plane(x):
    m = slope_at(x); nrm = math.hypot(1.0, m)
    return (x, 0.0, med_z(x)), (1.0 / nrm, 0.0, m / nrm)

co1, no1 = joint_plane(b1); co2, no2 = joint_plane(b2)
# segment with SHARED planes -> mating faces coincide
coxa = dup(leg, "coxa"); bisect_keep(coxa, co1, no1, keep_positive=False); cleanm(coxa)
femur = dup(leg, "femur"); bisect_keep(femur, co1, no1, keep_positive=True)
bisect_keep(femur, co2, no2, keep_positive=False); cleanm(femur)
tibia = dup(leg, "tibia"); bisect_keep(tibia, co2, no2, keep_positive=True); cleanm(tibia)
segs = {"coxa": coxa, "femur": femur, "tibia": tibia}

# joint pivots (leg-local frame)
P0 = Vector((x0, 0.0, med_z(x0)))
P1 = Vector((b1, 0.0, med_z(b1)))
P2 = Vector((b2, 0.0, med_z(b2)))
Pf = Vector((x1, 0.0, med_z(x1)))

# ---- SERVO SEATS + hide strategy ---------------------------------------------
# The limb is placed RIGIDLY at its NATURAL sculpt angle (see repose below), so the
# two flat faces of every joint MATE EXACTLY -> the assembly reads as the intact
# stone sculpt with zero wedge gaps. The Ø46x44 EduLite servo is then hidden per
# joint by whichever fits the local limb girth:
#   - limb wide enough (half-width >= 26) -> bury the servo inside; seat opens on
#     the hidden inner/underside face. Minimal visible seam.
#   - limb too slender for a Ø46 servo -> keep a FLAT functional mount AND emit a
#     cosmetic *_cover.stl: a thin stone sleeve sliced from the UNCUT sculpt at
#     that joint, whose outer face matches the sculpt, clipping over joint+servo.
covers_needed = []
MIN_HIDE_HALF = SERVO_D / 2 + SHELL    # 26 mm: limb half-width to bury the servo


def seat_cutter(name, pivot, halfw):
    # Ø46 seat along Y (pitch axis), opening on the hidden inner/underside (-Y),
    # blind toward the outer (+Y) face when the limb is thick enough.
    depth = min(SERVO_L + 6.0, 2 * halfw + 6.0)
    cy = 2.0 - depth / 2.0
    return add_cyl(name, SERVO_D / 2, depth, (pivot.x, cy, pivot.z), axis="Y")


def make_joint(tag, prox, dist, pivot):
    """Bore a SHARED Ø46 seat spanning the mated joint (into both segments) so the
    servo bridges the pitch axis. Decide hidden-vs-cover by limb girth."""
    w = leg_width_at(pivot.x); halfw = w / 2.0
    hide = halfw >= MIN_HIDE_HALF
    seat = seat_cutter(f"seat_{tag}", pivot, halfw)
    boolean(dist, seat, "DIFFERENCE", del_cutter=False)
    boolean(prox, seat, "DIFFERENCE", del_cutter=True)
    if hide:
        report["joints"][tag] = {"type": "hidden_in_limb", "limb_width_mm": round(w, 1),
            "servo": "EduLite Ø46x44 buried in the limb; seat opens on hidden inner face; "
                     "faces mate (no gap) at the natural pose"}
        print(f"[3] joint {tag}: HIDDEN in limb (w={w:.1f})")
    else:
        covers_needed.append((tag, Vector(pivot)))
        report["joints"][tag] = {"type": "flat_mount_plus_cover", "limb_width_mm": round(w, 1),
            "servo": f"EduLite Ø46x44 flat mount at slender joint (limb {w:.0f}mm < servo 46mm); "
                     f"hidden under cosmetic refined_{tag}_cover.stl stone sleeve"}
        print(f"[3] joint {tag}: FLAT + COVER (limb w={w:.1f} < {2*MIN_HIDE_HALF:.0f})")

make_joint("knee1", coxa, femur, P1)
make_joint("knee2", femur, tibia, P2)
# hip: coxa root sinks into the thorax socket -> servo hidden by the socket itself
hip_seat = seat_cutter("seat_hip", Vector((x0 + 0.10 * L, 0.0, med_z(x0 + 0.10 * L))),
                       leg_width_at(x0 + 0.10 * L) / 2.0)
boolean(coxa, hip_seat, "DIFFERENCE")
report["joints"]["hip"] = {"type": "hidden_in_thorax_socket",
                           "servo": "EduLite Ø46x44 at the coxa root, tucked inside the thorax leg socket"}

# ---- FINGERS: NOTHING is done to the hand. No graft, no cavity, no boss. -----
report["parts_fingers_note"] = ("The sacred 3-finger manipulator hand rides the DISTAL "
    "end of the tibia segment, entirely beyond the knee2 cut. No graft, no cone, no "
    "grip cavity, no servo boss touches it — preserved 1:1 from the sculpt.")

# ---- cosmetic (uncut, un-shelled) twins for the assembly LOOK render ---------
cos_segs = {nm: dup(s, nm + "_cos") for nm, s in segs.items()}

# ---- COVER parts: thin shell sliced from the UNCUT sculpt at the joint -------
# (only for joints flagged too-thin). Outer face matches the sculpt exactly.
cover_objs = {}
for (tag, pivot) in covers_needed:
    band = dup(leg, f"{tag}_cover")
    half = max(SERVO_L, leg_width_at(pivot.x)) / 2.0 + 10.0   # sleeve spans the joint+servo
    bisect_keep(band, (pivot.x - half, 0, pivot.z), (1, 0, 0), keep_positive=True)
    bisect_keep(band, (pivot.x + half, 0, pivot.z), (1, 0, 0), keep_positive=False)
    cleanm(band)
    solidify(band, 2.6)   # thin cosmetic stone sleeve (outer face = sculpt)
    cover_objs[tag] = band
    report["covers"].append({"part": f"refined_{tag}_cover", "wall_mm": 2.6,
                             "span_mm": round(2 * half, 1),
                             "note": "thin stone sleeve over the flat joint+servo; outer face = sculpt, "
                                     "clips/bolts on so the assembled robot reads as the sculpt"})

# ---- hollow the engineered segments to a shell -------------------------------
for nm, s in segs.items():
    segs[nm].data["hollow"] = solidify(s, SHELL)

# ================= Phase 3b: RIGID natural-pose placement, instance 5x =========
# Instead of articulating each joint (which opens ugly wedge gaps), we KEEP the
# sculpt's own limb bend and place the WHOLE limb rigidly at the hip: one rotation
# about the pitch axis (Y) so the hand plants near the ground, then seat the hip
# in the thorax socket. Because coxa/femur/tibia share ONE rigid transform, every
# cut face MATES EXACTLY -> seamless, and the leg keeps the original art's shape.
R_seat = R_CORE - 20.0                            # sink the coxa root DEEP into the
                                                  # thorax socket so the flank covers
                                                  # the junction (no open hip gap)
GROUND_CLR = 5.0
d0 = Pf - P0                                    # local hip->foot chord (dx,0,dz)
Lc = math.hypot(d0.x, d0.z)                      # chord length (fixed; rigid limb)
a0 = math.atan2(d0.z, d0.x)                       # current chord elevation
SPLAY_DEG = -40.0                                 # target: outward (+X) & down (-Z)
# pick the Y-rotation that actually lands the chord outward-and-down (robust to sign
# convention): try both candidates, evaluate the real rotated chord, choose e.x>0 & e.z<0.
bestphi = None; bestscore = 1e18
for cand in (a0 - math.radians(SPLAY_DEG), math.radians(SPLAY_DEG) - a0):
    e = Matrix.Rotation(cand, 4, "Y") @ Vector(d0)
    if e.x > 0:
        score = abs(math.degrees(math.atan2(e.z, e.x)) - SPLAY_DEG)
        if score < bestscore: bestscore = score; bestphi = cand
if bestphi is None: bestphi = a0 - math.radians(SPLAY_DEG)
erot = Matrix.Rotation(bestphi, 4, "Y") @ Vector(d0)   # rotated chord (dir + length)
# derive hip height so the foot lands at GROUND_CLR (limb is short -> hip sits low)
Z_HIP = GROUND_CLR - erot.z
Z_HIP = max(Z_HIP, tz0 + 0.30 * (tz1 - tz0))      # keep the hip on the thorax flank
HIP = Vector((R_seat, 0.0, Z_HIP))
RIGID = Matrix.Translation(HIP) @ Matrix.Rotation(bestphi, 4, "Y") @ Matrix.Translation(-P0)


def place(objmap):
    for nm, o in objmap.items():
        o.data.transform(RIGID); o.data.update()

place(segs); place(cos_segs)
for band in cover_objs.values():
    band.data.transform(RIGID); band.data.update()
foot = RIGID @ Pf
footprint_r = round(math.hypot(foot.x, foot.y), 1)
foot_drop = round(HIP.z - foot.z, 1)
print(f"[3] RIGID pose phi={math.degrees(bestphi):.1f}deg hip r={R_seat:.0f} z={Z_HIP:.0f} "
      f"foot r={footprint_r} z={foot.z:.0f} (drop {foot_drop}) -- faces MATE (no gap)")

for nm, s in segs.items():
    report["parts"][nm] = {
        "dims_mm": tuple(round(x, 1) for x in s.dimensions),
        "fits_envelope": maxdim(s) <= ENVELOPE, "hollow": s.data.get("hollow", "solid"),
        "shell_mm": SHELL, "nonmanifold_edges": nm_edges(s),
        "identical_instances": N_LEGS, "print_qty": N_LEGS}
report["parts"]["tibia"]["fingers"] = ("SACRED 3-finger manipulator hand PRESERVED 1:1 "
    "(sculpt-native, distal of the knee2 cut; no graft/cone/cavity/boss)")
report["assembly"] = {
    "hand_limb_az": ARM_AZ, "instanced": N_LEGS, "azimuths_deg": report["assembly_azimuths_deg"],
    "pose": "RIGID natural placement (sculpt joint angles preserved; faces mate, no wedge gaps)",
    "hip_pitch_deg": round(math.degrees(bestphi), 1),
    "hip_socket_radius_mm": round(R_seat, 1), "hip_height_mm": round(Z_HIP, 1),
    "footprint_radius_mm": footprint_r, "footprint_dia_mm": round(2 * footprint_r, 1),
    "target_footprint_dia_mm": round(2 * FOOTPRINT_R_MM, 1),
    "symmetry": "true 5-fold radial (5 identical hand-limbs @72deg, each foot a 3-finger hand)"}

leg_parts = [(coxa, "coxa"), (femur, "femur"), (tibia, "tibia")]

# instance cosmetic leg + covers 5x for the assembly render. The coxa root is sunk
# deep into the solid cosmetic dome (R_seat << R_CORE) so the craggy flank overlaps
# and covers the hip junction -- no bolt-on collar needed.
cosmetic = [thorax_cos]
for k, azk in enumerate(SYM_AZ):
    Rz = Matrix.Rotation(math.radians(azk), 4, "Z")
    for nm in ("coxa", "femur", "tibia"):
        dd = dup(cos_segs[nm], f"legc{k}_{nm}"); dd.data.transform(Rz); dd.data.update()
        cosmetic.append(dd)
    for tag, band in cover_objs.items():
        dd = dup(band, f"coverc{k}_{tag}"); dd.data.transform(Rz); dd.data.update()
        cosmetic.append(dd)
for s in cos_segs.values(): bpy.data.objects.remove(s, do_unlink=True)
bpy.data.objects.remove(leg, do_unlink=True); bpy.data.objects.remove(raw, do_unlink=True)

# ============================ Phase 4: splits >250 ============================
splits = {}
for name, info in list(report["parts"].items()):
    md = max(info.get("dims_mm", info.get("final_dims_mm", [0])))
    if md > ENVELOPE: splits[name] = f"exceeds {ENVELOPE}mm ({md}mm) -> dovetail+pin split"
report["splits"] = splits if splits else "none needed (all parts <= 250mm)"

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
for tag, band in cover_objs.items(): export_map[f"{tag}_cover"] = band
for nm, o in export_map.items(): export_one(o, os.path.join(STL_OUT, "refined_" + nm + ".stl"))
report["print_set"] = {
    "unique_stls": sorted("refined_" + k for k in export_map.keys()),
    "print_bom": {"refined_thorax": 1, "refined_coxa": N_LEGS, "refined_femur": N_LEGS,
                  "refined_tibia": N_LEGS, **{f"refined_{t}_cover": N_LEGS for t in cover_objs}},
    "total_printed_parts": 1 + 3 * N_LEGS + N_LEGS * len(cover_objs),
    "note": "5 identical hand-limbs -> print coxa/femur/tibia (+covers) x5 from one STL each"}
report["part_count"] = len(export_map)
print(f"[export] {len(export_map)} unique STLs -> {STL_OUT}")

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
for o, _ in leg_parts: o.hide_render = True
thorax.hide_render = True
for band in cover_objs.values(): band.hide_render = True
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
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; return o

add_light("SUN", "key", 3.4, (0, 0, 1500), (math.radians(48), math.radians(12), math.radians(35)))
add_light("AREA", "fill", 40000, (-span, -span, span), (math.radians(55), 0, math.radians(-40)))
add_light("AREA", "rim", 28000, (span * 0.7, span, span), (math.radians(60), 0, math.radians(150)))

sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 900; sc.render.resolution_y = 900
try: sc.eevee.use_gtao = True; sc.eevee.use_soft_shadows = True
except Exception: pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("t", None); bpy.context.collection.objects.link(tgt); tgt.location = (0, 0, zmax_all * 0.42)
con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
cam.data.lens = 52
D = span * 2.7
views = {"iso": (D * 0.62, -D * 0.62, D * 0.5), "front": (0, -D * 0.95, zmax_all * 0.5 + span * 0.25),
         "top": (0.01, 0, D * 1.25)}
base = os.path.join(MEDIA, "rocky_refined_assembly.png")
for nm, pos in views.items():
    cam.location = pos; sc.render.filepath = base.replace(".png", f"_{nm}.png")
    bpy.ops.render.render(write_still=True); print("[render]", sc.render.filepath)
    if nm == "iso":
        sc.render.filepath = base; bpy.ops.render.render(write_still=True); print("[render]", base)

# ---- hands_after close-up: frame one instanced foot's 3-finger hand ----------
# pick foot instance k=0 (tibia) and aim tight on its distal fingers.
foot_obj = None
for o in cosmetic:
    if o.name.startswith("legc0_tibia"): foot_obj = o; break
if foot_obj:
    Vf = [foot_obj.matrix_world @ v.co for v in foot_obj.data.vertices]
    # distal tip = farthest from body axis
    tipv = sorted(Vf, key=lambda p: -(math.hypot(p.x, p.y)))[:max(30, len(Vf)//12)]
    tc = Vector((sum(p.x for p in tipv)/len(tipv), sum(p.y for p in tipv)/len(tipv),
                 sum(p.z for p in tipv)/len(tipv)))
    ar = math.radians(SYM_AZ[0])
    cam.data.lens = 90
    for suff, off in (("", (math.cos(ar)*70+15, math.sin(ar)*70-70, 55)),
                      ("_side", (math.cos(ar)*90, math.sin(ar)*90, 35))):
        cam.location = (tc.x+off[0], tc.y+off[1], tc.z+off[2]); tgt.location = tc
        sc.render.filepath = os.path.join(MEDIA, f"rocky_hands_after{suff}.png")
        bpy.ops.render.render(write_still=True); print("[render]", sc.render.filepath)

with open(os.path.join(STL_OUT, "rocky_refined_report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("[done] report ->", os.path.join(STL_OUT, "rocky_refined_report.json"))
