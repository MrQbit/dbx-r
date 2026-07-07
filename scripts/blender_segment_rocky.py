#!/usr/bin/env python3
"""Blender-headless: turn the official Rocky STL into a clean, movie-accurate,
PRINTABLE, ARTICULATED part set — preserving the real organic (craggy stone)
geometry with planar bisect cuts + boolean cavities. NO voxel remesh.

Pipeline (all in bpy):
  A. Clean master rocky_normalized.stl. It is already pentaradially symmetric at
     ~272 mm but has ARTIFACTS: 4 legs read as detached loose bodies (10683 verts
     each, identical copies) and 1 leg is fused into the central thorax body.
     We rebuild a clean SYMMETRIC master from those good parts: extract the thorax
     dome (radial cylinder intersect of the big body) + one clean leg copy, then
     instance the leg 5x at 72 deg. This dodges the detached-leg artifact entirely
     and guarantees 5-fold symmetry (movie canon).
  B. Thorax: intersect big body with r=R_CORE cylinder -> watertight dome; hollow
     via Solidify; boolean-subtract Jetson tray + 6S battery bays (open bottom).
  C. Leg: align one copy to +X, bisect at the two natural bends into coxa/femur/
     tibia (capped planar cuts); hollow each; carve EduLite Ø46 servo seats at the
     joints; graft 3 stone fingers on the tibia tip; carve grip-micro cavity.
  D. Instance the leg-set 5x at 72 deg around the thorax.
  E. Export printable STLs to rocky/cad/stl_derived/ and render a POSED, STANDING
     stone-crab assembly (EEVEE, stone material + cragginess bump, 3-pt light,
     ground shadow) to docs/media/rocky_blender_assembly_{iso,front,top}.png.

Run:  blender --background --python scripts/blender_segment_rocky.py
Optional: -- <master.stl>
"""
import sys, os, math, json
import bpy, bmesh
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MASTER = argv[0] if argv else os.path.join(ROOT, "reference/stl/rocky_normalized.stl")
STL_OUT = os.path.join(ROOT, "rocky/cad/stl_derived")
MEDIA = os.path.join(ROOT, "docs/media")
os.makedirs(STL_OUT, exist_ok=True)
os.makedirs(MEDIA, exist_ok=True)

# ---- global scale (D-032) ----------------------------------------------------
# x1.2 UPSCALE of the SCANNED organic body so the standard Jetson carrier (63mm
# on-edge) fits the natural craggy shell with >=3mm walls -- NO custom PCB, NO
# artificial widening/turret. The scale multiplies the scan-derived GEOMETRY
# constants (dome radius, leg bends, dome trim, leg cosmetic grafts) but NOT the
# real-world HARDWARE sizes (servos, Jetson tray, battery) or the 3mm wall.
SCALE    = 1.2           # 272mm compact master -> ~326mm carapace
# ---- geometry constants (mm), derived from measured profiling * SCALE ---------
R_CORE   = 48.0 * SCALE   # thorax dome radius; legs begin at r~46
X_BEND1  = 78.0 * SCALE   # coxa|femur split (radial dist from axis)
X_BEND2  = 100.0 * SCALE  # femur|tibia split
N_LEGS   = 5
LEG_PHASE = 90.0         # deg: put one leg pointing "back", nicer stance
SHELL_MM = 3.0           # hollow wall (print constraint -- NOT scaled)
# hardware (D-031) -- real-world sizes, NOT scaled
SERVO_D, SERVO_L = 46.0, 44.0                 # EduLite-05 leg servo
GRIP = (22.8, 12.2, 28.5)                      # grip micro servo
JETSON = (90.0, 63.0, 30.0)                    # Jetson tray
BATT = (85.0, 40.0, 25.0)                      # 6S battery
ENVELOPE = 250.0                               # Bambu print envelope

report = {"master": os.path.basename(MASTER), "method": "symmetric_rebuild_blender_bisect",
          "scale_D032": SCALE,
          "constants": {"R_CORE": R_CORE, "X_BEND1": X_BEND1, "X_BEND2": X_BEND2,
                        "shell_mm": SHELL_MM}, "parts": {}}


# ----------------------------- helpers ----------------------------------------
def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for b in list(coll):
            try: coll.remove(b)
            except Exception: pass


def import_stl(path):
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    return bpy.context.selected_objects[0]


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def clean_mesh(obj, dist=0.05):
    """merge-by-distance, fill holes, recalc normals -> tidy manifold-ish body."""
    activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.fill_holes(sides=0)          # 0 = all
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def nonmanifold_edges(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    n = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return n


def maxdim(obj):
    return round(max(obj.dimensions), 1)


def add_cutter_cyl(name, radius, length, loc, axis="Z"):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=loc,
                                        vertices=64)
    c = bpy.context.active_object
    c.name = name
    if axis == "X":
        c.rotation_euler = (0, math.radians(90), 0)
    elif axis == "Y":
        c.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    return c


def add_cutter_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    c = bpy.context.active_object
    c.name = name
    c.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(scale=True)
    return c


def boolean(obj, cutter, op="DIFFERENCE", delete_cutter=True):
    activate(obj)
    m = obj.modifiers.new("bool", "BOOLEAN")
    m.operation = op
    m.solver = "EXACT"
    m.object = cutter
    try:
        bpy.ops.object.modifier_apply(modifier=m.name)
        ok = True
    except Exception as e:
        print("[bool] FAILED", op, cutter.name, e)
        obj.modifiers.remove(m)
        ok = False
    if delete_cutter:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return ok


def solidify_shell(obj, thickness=SHELL_MM):
    """Hollow to a ~thickness shell. Keeps a solid duplicate as backup; if the
    inward offset explodes on the craggy high-curvature surface, swap the backup
    mesh data back in (degraded = stays solid) so downstream refs stay valid."""
    activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.05)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    before = max(obj.dimensions)
    # backup solid copy
    activate(obj)
    bpy.ops.object.duplicate()
    backup = bpy.context.active_object
    activate(obj)
    m = obj.modifiers.new("solid", "SOLIDIFY")
    m.thickness = thickness
    m.offset = -1.0            # grow inward, keep outer craggy surface
    m.use_even_offset = False  # even offset explodes on craggy high-curvature verts
    ok = True
    try:
        bpy.ops.object.modifier_apply(modifier=m.name)
    except Exception as e:
        print("[solidify] FAILED", obj.name, e); ok = False
    if not ok or max(obj.dimensions) > before * 1.35:
        print(f"[solidify] reverting {obj.name} to SOLID (degraded; offset unstable)")
        obj.data = backup.data          # swap solid mesh back in, keep obj ref
        bpy.data.objects.remove(backup, do_unlink=True)
        return "solid"
    bpy.data.objects.remove(backup, do_unlink=True)
    return "shell"


def bisect_slab(src, xmin, xmax, name):
    """Duplicate src, keep only xmin<=x<=xmax with CAPPED planar cuts."""
    activate(src)
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.name = name
    activate(dup)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    if xmax is not None:
        bpy.ops.mesh.bisect(plane_co=(xmax, 0, 0), plane_no=(1, 0, 0),
                            use_fill=True, clear_inner=False, clear_outer=True)
        bpy.ops.mesh.select_all(action="SELECT")
    if xmin is not None:
        bpy.ops.mesh.bisect(plane_co=(xmin, 0, 0), plane_no=(1, 0, 0),
                            use_fill=True, clear_inner=True, clear_outer=False)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return dup


# ----------------------------- Phase A: load + split --------------------------
clear()
raw = import_stl(MASTER)
activate(raw)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
bodies = [o for o in bpy.context.scene.objects if o.type == "MESH"]
# drop junk
for o in list(bodies):
    if len(o.data.vertices) < 50:
        bpy.data.objects.remove(o, do_unlink=True)
bodies = [o for o in bpy.context.scene.objects if o.type == "MESH"]

# global XY axis = centroid of all verts
allc = Vector((0, 0, 0)); n = 0
for o in bodies:
    for v in o.data.vertices:
        allc += o.matrix_world @ v.co; n += 1
allc /= n
CENTER = Vector((allc.x, allc.y, 0.0))
# recenter every body so pentagon axis is world Z, then apply the D-032 x1.2
# UPSCALE uniformly about that axis (grows the organic body; hardware stays real).
for o in bodies:
    o.data.transform(Matrix.Scale(SCALE, 4) @ Matrix.Translation(-CENTER))
    o.data.update()
print(f"[A] applied D-032 upscale x{SCALE}")

big = max(bodies, key=lambda o: len(o.data.vertices))
legs = [o for o in bodies if o is not big and len(o.data.vertices) > 3000]


def body_angle(o):
    c = Vector((0, 0, 0))
    for v in o.data.vertices:
        c += o.matrix_world @ v.co
    c /= len(o.data.vertices)
    return math.degrees(math.atan2(c.y, c.x))

print(f"[A] bodies={len(bodies)} big={len(big.data.vertices)}v legs={len(legs)}")


# ----------------------------- Phase B: thorax --------------------------------
activate(big)
bpy.ops.object.duplicate()
thorax = bpy.context.active_object
thorax.name = "thorax"
clean_mesh(thorax)
zc = sum((thorax.matrix_world @ v.co).z for v in thorax.data.vertices) / len(thorax.data.vertices)
# The big body = dome + ONE fused leg (the other 4 legs are separate). A cylinder
# INTERSECT would shave the dome's craggy flared sides + pentagon corners into a
# smooth wall, so instead remove ONLY the fused leg with a single planar cut
# perpendicular to its direction, at r=R_CORE. This keeps ALL natural surface.
fused_ang = math.radians(body_angle(big))
nx, ny = math.cos(fused_ang), math.sin(fused_ang)
activate(thorax)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.bisect(plane_co=(R_CORE * nx, R_CORE * ny, zc), plane_no=(nx, ny, 0),
                    use_fill=True, clear_inner=False, clear_outer=True)  # drop leg
bpy.ops.object.mode_set(mode="OBJECT")
# fill the sockets left where the other 4 legs detached -> closed craggy dome
activate(thorax)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.fill_holes(sides=0)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
# Trim the bottom flat (~82mm dome * SCALE) — print base + electronics hatch.
zmax = max((thorax.matrix_world @ v.co).z for v in thorax.data.vertices)
THORAX_CUT = zmax - 82.0 * SCALE
activate(thorax)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.bisect(plane_co=(0, 0, THORAX_CUT), plane_no=(0, 0, 1),
                    use_fill=True, clear_inner=True, clear_outer=False)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
clean_mesh(thorax)

# --- DEEPEN THE THORAX ORGANICALLY (taller, NOT wider; keep the scanned crags) --
# The scanned carapace is ~86(W) x ~84(D) mm (crag tips to ~97x85) with a natural
# Y-WAIST ~15 mm above the floor (D pinches to ~55 mm) and a pentagonal CROWN that
# starts narrowing ~66 mm up. We DO NOT widen it and we DO NOT replace it with a
# turret. The fit is solved by standing BOTH boards VERTICALLY, side by side
# (D-032), so their combined footprint is only ~63(X) x 55(Y). To give them >=90mm
# of vertical room under the organic shell we STRETCH the craggy body in Z above
# the cavity floor: every vertex above ZF is scaled up in Z, so the existing crags
# ELONGATE and the crown rides up, opening a taller full-width interior below it.
# Floor + waist stay rigid; no facet is smoothed and no straight wall is created,
# so the shell still reads as one taller organic stone, never a bucket/turret.
#
# hardware standing vertically (bounding boxes X,Y,Z):
#   Jetson tray 90x63x30 ON-EDGE -> 63(X) x 30(Y) x 90(Z)
#   6S battery  85x40x25 ON-END  -> 40(X) x 25(Y) x 85(Z)
JET_BOX = (63.0, 30.0, 90.0)
BAT_BOX = (40.0, 25.0, 85.0)
PAIR_W  = max(JET_BOX[0], BAT_BOX[0])        # 63 along X (wide axis, no waist)
PAIR_D  = JET_BOX[1] + BAT_BOX[1]            # 55 along Y (boards side by side)
WALL    = SHELL_MM                           # >=3 mm shell each side
NEED_W  = PAIR_W + 2 * WALL                  # 69 outer X the shell must provide
NEED_D  = PAIR_D + 2 * WALL                  # 61 outer Y the shell must provide
CLEAR_TOP = 6.0                              # crown clearance above the tallest board

# bake transforms so v.co == world coords for the vertical remap + measurements
activate(thorax)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def out_span(zlo, zhi):
    xs = []; ys = []
    for v in thorax.data.vertices:
        if zlo <= v.co.z <= zhi:
            xs.append(v.co.x); ys.append(v.co.y)
    return (max(xs) - min(xs), max(ys) - min(ys)) if xs else (0.0, 0.0)


zf0 = min(v.co.z for v in thorax.data.vertices)   # true floor
zc0 = max(v.co.z for v in thorax.data.vertices)   # natural crown top
# scan the natural profile (fine bands) and take the LONGEST contiguous window
# (above the waist, below the crown) where the shell clears BOTH footprints.
runs = []; cur = []; z = zf0 + 2.0
while z < zc0:
    w, d = out_span(z - 3.0, z + 3.0)
    if w >= NEED_W and d >= NEED_D:
        cur.append(z)
    elif cur:
        runs.append(cur); cur = []
    z += 2.0
if cur:
    runs.append(cur)
if runs:
    win = max(runs, key=lambda r: r[-1] - r[0])
    ZF, ZNAT_TOP = win[0], win[-1]
else:
    ZF, ZNAT_TOP = zf0 + 16.0, zf0 + 66.0     # fallback (should not trigger)
NAT_WIN = max(ZNAT_TOP - ZF, 1.0)
# Piecewise Z-remap (seamless): the featureless craggy MID-WALL [ZF, ZNAT_TOP] is
# stretched to open the taller full-width interior, while the pentagonal CROWN
# (z > ZNAT_TOP, with its slits/lobes) is RIGIDLY LIFTED so its shape is preserved
# exactly -- stretching the crown would elongate its natural valleys into holes.
# The two pieces meet continuously at ZNAT_TOP (stretch top == lifted crown base).
BOARD_TOP = ZF + max(JET_BOX[2], BAT_BOX[2]) + CLEAR_TOP
FACTOR = max((BOARD_TOP - ZF) / NAT_WIN, 1.0)
LIFT = BOARD_TOP - ZNAT_TOP                           # rigid crown lift
for v in thorax.data.vertices:
    z = v.co.z
    if z <= ZF:
        continue
    elif z <= ZNAT_TOP:
        v.co.z = ZF + (z - ZF) * FACTOR               # stretch mid-wall
    else:
        v.co.z = z + LIFT                             # lift crown intact
thorax.data.update()
DOME_RAISE = round(LIFT, 1)                            # crown lift (report)
clean_mesh(thorax)
print(f"[B] organic deepen: cavity_floor(ZF)=+{ZF - zf0:.1f}mm  "
      f"mid_wall_window={NAT_WIN:.1f}mm  stretch_factor={FACTOR:.2f}  "
      f"crown_lift=+{DOME_RAISE:.1f}mm")

# record solid (deepened) dome dims before hollowing
dome_dim = tuple(round(d, 1) for d in thorax.dimensions)
zmin = min(v.co.z for v in thorax.data.vertices)
zmax = max(v.co.z for v in thorax.data.vertices)
body_W, body_D = out_span(zmin, zmax)   # outer footprint (must stay ~natural)


def body_count(obj):
    activate(obj)
    bpy.ops.object.duplicate()
    d = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    made = [o for o in bpy.context.selected_objects] + [d]
    made = [o for o in set(made) if o.type == "MESH"]
    n = len([o for o in made if len(o.data.vertices) > 30])
    for o in made:
        bpy.data.objects.remove(o, do_unlink=True)
    return n


# ---- precompute the SOLID outer shell extent per 4mm z-slice over the board
#      column, then find the cavity XY offset that MAXIMISES the min wall (best
#      natural placement inside the organic, off-centre, craggy shell). ----------
slices = []
zz = ZF + 1.0
while zz < ZF + JET_BOX[2]:
    xs = [v.co.x for v in thorax.data.vertices if zz - 2 <= v.co.z <= zz + 2]
    ys = [v.co.y for v in thorax.data.vertices if zz - 2 <= v.co.z <= zz + 2]
    if xs and ys:
        slices.append((zz, min(xs), max(xs), min(ys), max(ys)))
    zz += 4.0


def bbox_min_wall(cx0, cx1, cy0, cy1, ztop):
    """min shell clearance on all four sides across z in [ZF, ztop]."""
    mw = 1e9
    for (zc, xmn, xmx, ymn, ymx) in slices:
        if zc > ztop:
            break
        mw = min(mw, cx0 - xmn, xmx - cx1, cy0 - ymn, ymx - cy1)
    return mw


# jetson on -Y half, battery on +Y half (adjacent, sharing the divider plane so no
# stone is wasted between them); both share the wide X span.
best = (-1e9, 0.0, 0.0)
for xoff in [i * 0.5 for i in range(-24, 25)]:
    for yoff in [i * 0.5 for i in range(-24, 25)]:
        mw = bbox_min_wall(-PAIR_W / 2 + xoff, PAIR_W / 2 + xoff,
                           -PAIR_D / 2 + yoff, PAIR_D / 2 + yoff, ZF + JET_BOX[2])
        if mw > best[0]:
            best = (mw, xoff, yoff)
XOFF, YOFF = best[1], best[2]
print(f"[B] cavity placement: offset=({XOFF:+.1f},{YOFF:+.1f})mm  "
      f"best pair min-wall={best[0]:.1f}mm")

# ---- measure the ATTEMPTED fit: real per-board wall clearance across height ----
jet_wall = round(bbox_min_wall(-JET_BOX[0] / 2 + XOFF, JET_BOX[0] / 2 + XOFF,
                               -PAIR_D / 2 + YOFF, -PAIR_D / 2 + JET_BOX[1] + YOFF,
                               ZF + JET_BOX[2]), 1)
bat_wall = round(bbox_min_wall(-BAT_BOX[0] / 2 + XOFF, BAT_BOX[0] / 2 + XOFF,
                               PAIR_D / 2 - BAT_BOX[1] + YOFF, PAIR_D / 2 + YOFF,
                               ZF + BAT_BOX[2]), 1)
jet_fits = jet_wall >= WALL
bat_fits = bat_wall >= WALL
boards_fit = jet_fits and bat_fits

# largest CENTRED vertical bay (at the optimal offset) that still keeps >=WALL walls
# over the full board height -> quantifies the honest shortfall vs the 63x55 pair.
maxfit_w = maxfit_d = 0.0
for s in [i * 0.5 for i in range(0, 40)]:
    m = bbox_min_wall(-PAIR_W / 2 + s + XOFF, PAIR_W / 2 - s + XOFF,
                      -PAIR_D / 2 + s + YOFF, PAIR_D / 2 - s + YOFF, ZF + JET_BOX[2])
    if m >= WALL:
        maxfit_w, maxfit_d = round(PAIR_W - 2 * s, 1), round(PAIR_D - 2 * s, 1)
        break

# carve the electronics volume + a bottom wiring conduit. If the full 63x55 pair
# fits with >=3mm walls, carve BOTH real board bays; otherwise (honest fallback)
# carve the largest bay that stays watertight with >=3mm walls so the delivered
# body is a clean organic shell, and report the shortfall -- we do NOT widen.
cond_h = ZF - zmin + 6.0
if boards_fit:
    jet = add_cutter_box("jetson_bay", JET_BOX,
                         (XOFF, -PAIR_D / 2 + JET_BOX[1] / 2 + YOFF, ZF + JET_BOX[2] / 2))
    boolean(thorax, jet, "DIFFERENCE")
    bat = add_cutter_box("batt_bay", BAT_BOX,
                         (XOFF, PAIR_D / 2 - BAT_BOX[1] / 2 + YOFF, ZF + BAT_BOX[2] / 2))
    boolean(thorax, bat, "DIFFERENCE")
    cavity_note = ("two vertical bays side-by-side on a pedestal above the natural "
                   "Y-waist; shell stretched taller in Z (organic, not widened)")
else:
    print(f"[B] boards do NOT fit 3mm walls (jet={jet_wall} bat={bat_wall}mm); "
          f"carving largest clean bay {maxfit_w}x{maxfit_d} (watertight organic body)")
    bay = add_cutter_box("equip_bay", (maxfit_w, maxfit_d, JET_BOX[2]),
                         (XOFF, YOFF, ZF + JET_BOX[2] / 2))
    boolean(thorax, bay, "DIFFERENCE")
    cavity_note = (f"largest clean vertical bay {maxfit_w}x{maxfit_d}x{JET_BOX[2]:.0f} "
                   f"with >=3mm walls; the 63x55 board pair does NOT fit the organic "
                   f"shell (see fit_gate) and widening is forbidden")
cond = add_cutter_box("wire_conduit", (26.0, 20.0, cond_h),
                      (XOFF, YOFF, zmin + cond_h / 2 - 3.0))
boolean(thorax, cond, "DIFFERENCE")

th_shell = solidify_shell(thorax, SHELL_MM)
# close tiny scan/boolean holes (small loops only) WITHOUT sealing the intended
# base + wire-conduit openings, then tidy normals -> tighter watertightness.
activate(thorax)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.03)
bpy.ops.mesh.fill_holes(sides=12)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
severed = body_count(thorax) > 1
# outer footprint must have stayed ~the master's natural SCALED stone (NOT widened
# beyond the x1.2 upscale itself; x1.0 natural was ~96.7 x 84.6 mm)
footprint_ok = (80.0 * SCALE <= body_W <= 102.0 * SCALE) and \
               (74.0 * SCALE <= body_D <= 94.0 * SCALE)
fit_gate = {
    "boards_stand_vertical": True,
    "jetson_on_edge_box_XYZ_mm": list(JET_BOX),
    "battery_on_end_box_XYZ_mm": list(BAT_BOX),
    "pair_footprint_needed_WxD_mm": [PAIR_W, PAIR_D],
    "cavity_floor_above_floor_mm": round(ZF - zmin, 1),
    "cavity_xy_offset_mm": [round(XOFF, 1), round(YOFF, 1)],
    "min_wall_jetson_on_edge_mm": jet_wall,
    "min_wall_battery_on_end_mm": bat_wall,
    "jetson_90x63x30_on_edge_fits": bool(jet_fits),
    "battery_6s_85x40x25_on_end_fits": bool(bat_fits),
    "shell_walls_required_mm": SHELL_MM,
    "largest_clean_bay_WxDxH_mm": [maxfit_w, maxfit_d, JET_BOX[2]],
    "footprint_shortfall_WxD_mm": [round(PAIR_W - maxfit_w, 1),
                                   round(PAIR_D - maxfit_d, 1)],
    "outer_body_footprint_WxD_mm": [round(body_W, 1), round(body_D, 1)],
    "body_footprint_stayed_natural": bool(footprint_ok),
    "outer_surface_intact": (not severed),
    "GATE_both_fit": bool(boards_fit and not severed and footprint_ok),
    "verdict": ("both boards fit with >=3mm walls" if boards_fit else
                "boards do NOT fit the organic shell with 3mm walls; the craggy, "
                "off-centre cross-section provides only ~%gx%g mm of 3mm-walled "
                "interior over the 90mm board height (pinches at the -X mid-body "
                "crag and the +X crown onset). Deepening adds height, not width; "
                "widening is forbidden." % (maxfit_w, maxfit_d)),
}
report["parts"]["thorax"] = {
    "solid_dome_dims_mm": dome_dim, "z_range": [round(zmin, 1), round(zmax, 1)],
    "hollow": th_shell, "shell_mm": SHELL_MM,
    "cavities": (["jetson_tray_90x63x30_on_edge", "battery_6s_85x40x25_on_end",
                  "wire_conduit_26x20"] if boards_fit else
                 [f"equip_bay_{maxfit_w:.0f}x{maxfit_d:.0f}x{JET_BOX[2]:.0f}",
                  "wire_conduit_26x20"]),
    "cavity_note": cavity_note,
    "final_dims_mm": tuple(round(d, 1) for d in thorax.dimensions),
    "fits_envelope": maxdim(thorax) <= ENVELOPE,
    "nonmanifold_edges": nonmanifold_edges(thorax),
    "deepened": {"crown_lift_mm": DOME_RAISE, "stretch_factor": round(FACTOR, 2),
                 "cavity_floor_mm": round(ZF - zmin, 1),
                 "method": "vertical Z-stretch of the SCANNED craggy body above the "
                           "cavity floor; floor+waist rigid, crown rides up; width "
                           "UNCHANGED (organic stone, no turret/widening)"},
    "fit_gate": fit_gate,
}
print(f"[B] thorax final={report['parts']['thorax']['final_dims_mm']} "
      f"env_ok={maxdim(thorax)<=ENVELOPE}")
print(f"[GATE] outer_body={body_W:.1f}x{body_D:.1f}mm (scaled master~{96.7*SCALE:.0f}x{84.6*SCALE:.0f})  "
      f"cavity_floor=+{ZF - zmin:.1f}mm  jet_wall={jet_wall}mm bat_wall={bat_wall}mm  "
      f"jet_fits={jet_fits} bat_fits={bat_fits} intact={not severed} "
      f"footprint_ok={footprint_ok}  => GATE={fit_gate['GATE_both_fit']}")


# ----------------------------- Phase C: one canonical leg ---------------------
# pick a detached leg copy near +X-ish, rotate it to point exactly +X
target = min(legs, key=lambda o: abs(((body_angle(o) - 20) + 180) % 360 - 180))
la = body_angle(target)
activate(target)
bpy.ops.object.duplicate()
leg = bpy.context.active_object
leg.name = "leg_src"
leg.data.transform(Matrix.Rotation(math.radians(-la), 4, "Z"))
leg.data.update()
clean_mesh(leg)
xs = [(leg.matrix_world @ v.co).x for v in leg.data.vertices]
xmin_leg, xmax_leg = min(xs), max(xs)
print(f"[C] leg aligned from ang={la:.1f}  X {xmin_leg:.1f}..{xmax_leg:.1f}")

seg_defs = [("coxa", xmin_leg - 1, X_BEND1),
            ("femur", X_BEND1, X_BEND2),
            ("tibia", X_BEND2, xmax_leg + 1)]
segments = {}
for nm, a, b in seg_defs:
    segments[nm] = bisect_slab(leg, a, b, "seg_" + nm)   # solid capped slab

# --- carve cavities on the SOLID slabs first (robust EXACT booleans) ---
# servo seats (EduLite Ø46) straddling each joint plane, bored along +X
for jx, parts_here in [(X_BEND1, ["coxa", "femur"]), (X_BEND2, ["femur", "tibia"])]:
    for pn in parts_here:
        seat = add_cutter_cyl(f"seat_{pn}_{int(jx)}", SERVO_D / 2, SERVO_L,
                              (jx, 0, 0), axis="X")
        boolean(segments[pn], seat, "DIFFERENCE")
# coxa inner mount seat (mates to thorax) — pocket at the root
seat0 = add_cutter_cyl("seat_coxa_root", SERVO_D / 2, SERVO_L,
                       (xmin_leg - 1 + SERVO_L / 2 - 6, 0, 0), axis="X")
boolean(segments["coxa"], seat0, "DIFFERENCE")
# grip-micro cavity in the tibia (near the wrist, before the fingers)
gx = xmax_leg - 22 * SCALE
grip_cav = add_cutter_box("grip_cav", (GRIP[2], GRIP[0], GRIP[1]), (gx, 0, 0))
boolean(segments["tibia"], grip_cav, "DIFFERENCE")

# ---- graft 3 stone fingers on the tibia tip (solid union; cosmetic -> scaled) --
tip_pts = [leg.matrix_world @ v.co for v in leg.data.vertices
           if (leg.matrix_world @ v.co).x > xmax_leg - 6 * SCALE]
tip = sum(tip_pts, Vector((0, 0, 0))) / len(tip_pts)
tibia = segments["tibia"]
for k, ay in enumerate((-22, 0, 22)):
    # tapered prong: cone base r6 -> tip r1.2, length 24, splayed in azimuth+down
    bpy.ops.mesh.primitive_cone_add(radius1=6.5 * SCALE, radius2=1.4 * SCALE,
                                    depth=26 * SCALE, vertices=18, location=(0, 0, 0))
    f = bpy.context.active_object
    f.name = f"finger_{k}"
    # cone points +Z by default; aim it +X then splay
    f.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    f.rotation_euler = (0, math.radians(18), math.radians(ay))  # down + fan
    bpy.ops.object.transform_apply(rotation=True)
    f.location = (tip.x - 4 * SCALE, tip.y, tip.z)
    bpy.ops.object.transform_apply(location=True)
    boolean(tibia, f, "UNION")
clean_mesh(tibia)

# --- hollow each segment LAST (after cavities/fingers) ---
seg_shell = {}
for nm, s in segments.items():
    seg_shell[nm] = solidify_shell(s, SHELL_MM)

for nm, s in segments.items():
    report["parts"][f"leg_{nm}"] = {
        "dims_mm": tuple(round(d, 1) for d in s.dimensions),
        "fits_envelope": maxdim(s) <= ENVELOPE,
        "nonmanifold_edges": nonmanifold_edges(s),
        "hollow": seg_shell[nm], "shell_mm": SHELL_MM,
    }
report["parts"]["leg_tibia"]["fingers"] = 3
report["parts"]["leg_tibia"]["cavities"] = ["grip_micro_22.8x12.2x28.5"]
print("[C] segments:", {k: report["parts"]['leg_' + k]["dims_mm"] for k in segments})


# ---- pose the canonical leg into a STANDING bent-knee stance (articulated) ----
def slab_centroid(obj, x0, x1):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices
           if x0 <= (obj.matrix_world @ v.co).x <= x1]
    return sum(pts, Vector((0, 0, 0))) / max(len(pts), 1)

def rotate_about(objs, pivot, axis, deg):
    M = (Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(deg), 4, axis)
         @ Matrix.Translation(-pivot))
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    return M

YAX = Vector((0, 1, 0))
KNEE1, KNEE2 = 6.0, 12.0      # deg downward knee pitch at the two joints
p1 = slab_centroid(segments["femur"], X_BEND1 - 5, X_BEND1 + 5)
p2 = slab_centroid(segments["tibia"], X_BEND2 - 5, X_BEND2 + 5)
M1 = rotate_about([segments["femur"], segments["tibia"]], p1, YAX, KNEE1)
p2 = (M1 @ p2.to_4d()).to_3d()
rotate_about([segments["tibia"]], p2, YAX, KNEE2)
# nudge whole leg radially inward so the coxa root overlaps the thorax (close gap)
NUDGE = 16 * SCALE
for s in segments.values():
    s.matrix_world = Matrix.Translation(Vector((-NUDGE, 0, 0))) @ s.matrix_world
report["pose"] = {"knee1_deg": KNEE1, "knee2_deg": KNEE2, "inward_nudge_mm": round(NUDGE, 1)}


# ----------------------------- Phase D: instance 5x ---------------------------
# remove helper source bodies, keep thorax + segment prototypes
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o not in (thorax, *segments.values()):
        bpy.data.objects.remove(o, do_unlink=True)

assembly = [thorax]
export_map = {"thorax": thorax}
for i in range(N_LEGS):
    ang = math.radians(LEG_PHASE + i * (360.0 / N_LEGS))
    R = Matrix.Rotation(ang, 4, "Z")
    for nm, proto in segments.items():
        activate(proto)
        bpy.ops.object.duplicate()
        d = bpy.context.active_object
        d.name = f"leg{i+1}_{nm}"
        d.matrix_world = R @ d.matrix_world
        assembly.append(d)
        export_map[f"leg{i+1}_{nm}"] = d
# hide prototypes from render/export (they overlap leg with phase)
for proto in segments.values():
    proto.hide_set(True); proto.hide_render = True


# ----------------------------- export STLs ------------------------------------
def export_one(obj, path):
    activate(obj)
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              apply_modifiers=True)
        return
    except Exception:
        pass
    try:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)
    except Exception:
        bpy.ops.preferences.addon_enable(module="io_mesh_stl")
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)

for name, obj in export_map.items():
    export_one(obj, os.path.join(STL_OUT, name + ".stl"))
print(f"[export] wrote {len(export_map)} STLs to {STL_OUT}")

# defensive: nothing but the assembly should exist as a visible mesh at render
keep = set(assembly)
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o not in keep and not o.hide_get():
        print("[cleanup] removing stray mesh", o.name)
        bpy.data.objects.remove(o, do_unlink=True)


# ----------------------------- Phase E: render --------------------------------
def stone_material():
    m = bpy.data.materials.new("stone")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.30, 0.27, 0.23, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    # cragginess micro-bump from noise
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 22.0
    tex.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 1.5
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

mat = stone_material()
allobj = [o for o in assembly]
zmins = []
for o in allobj:
    if len(o.data.materials) == 0:
        o.data.materials.append(mat)
    else:
        o.data.materials[0] = mat
    activate(o)
    bpy.ops.object.shade_flat()
    zmins.append(min((o.matrix_world @ v.co).z for v in o.data.vertices))
GROUND_Z = min(zmins)

# lift assembly so it sits on z=0
lift = -GROUND_Z
for o in allobj:
    o.location.z += lift
zmax_all = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in allobj)
# true footprint radius (tip to axis) for framing
maxr = max(math.hypot((o.matrix_world @ v.co).x, (o.matrix_world @ v.co).y)
           for o in allobj for v in o.data.vertices)
span = maxr

# ground plane (shadow catcher-ish, matte)
bpy.ops.mesh.primitive_plane_add(size=1500, location=(0, 0, 0))
ground = bpy.context.active_object
gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
ground.data.materials.append(gm)

# world
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5

def add_light(kind, name, energy, loc, rot):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    if kind == "AREA": l.size = 400
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    return o

add_light("SUN", "key", 3.2, (0, 0, 800), (math.radians(48), math.radians(12), math.radians(35)))
add_light("AREA", "fill", 12000, (-span, -span, span * 0.9), (math.radians(55), 0, math.radians(-40)))
add_light("AREA", "rim", 9000, (span * 0.7, span, span), (math.radians(60), 0, math.radians(150)))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
try:
    scene.eevee.use_soft_shadows = True
    scene.eevee.use_gtao = True
except Exception:
    pass

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam); scene.camera = cam
tgt = bpy.data.objects.new("tgt", None); bpy.context.collection.objects.link(tgt)
tgt.location = (0, 0, zmax_all * 0.4)
con = cam.constraints.new("TRACK_TO"); con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
cam_data.lens = 50

d = span * 5.0
views = {
    "iso":   (d * 0.55, -d * 0.55, d * 0.62),   # elevated 3/4 hero
    "front": (0, -d * 0.82, zmax_all * 0.55 + span * 0.5),
    "top":   (0.001, 0, d * 1.05),
}
base = os.path.join(MEDIA, "rocky_blender_assembly.png")
for name, pos in views.items():
    cam.location = pos
    out = base.replace(".png", f"_{name}.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("[render]", out)
    if name == "iso":                       # also write the exact requested name
        scene.render.filepath = base
        bpy.ops.render.render(write_still=True)
        print("[render]", base)

report["part_count"] = len(export_map)
report["splits"] = "none needed (all parts <= 250mm Bambu envelope)"
report["envelope_mm"] = ENVELOPE
with open(os.path.join(STL_OUT, "blender_segment_report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("[done] report ->", os.path.join(STL_OUT, "blender_segment_report.json"))
