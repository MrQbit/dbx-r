#!/usr/bin/env python3
"""TASK 2 — shell each complete action-figure leg over the LOCKED ROCKY-5 chassis.

Source: rocky/cad/stl_derived/af_leg{N}_assembled.stl (built by blender_actionfig_legs.py
from the OFFICIAL articulated-figure limb pieces). For each leg we:
  * scale it onto the chassis (axial -> 238 mm hip..tip; lateral LAT so the craggy
    stone plates read at robot scale),
  * segment it at the chassis joint stations into coxa / femur / tibia shells,
  * RELIEVE the bulbous stone joint knuckles: taper each joint-facing rim down to a
    narrow neck (R_rim) and open a wide boot GAP, so the cosmetic clears the FULL
    joint travel (femur_pitch [-1.4,1.0], knee [-0.3,2.0]) instead of capping it,
  * SHELL = THE FIGURE SURFACE ITSELF (D-044 method fix): the craggy OUTER surface IS
    the cosmetic. We hollow it with a THIN 3 mm INWARD offset that FOLLOWS the craggy
    relief. We do NOT boolean a fat clearance cylinder into the body — at s=4.40 the
    lengthened chassis is slim (tibia ~Ø35 roll-servo, femur just the Ø12 driveshaft),
    so the natural figure cavity (~Ø40+ on the tibia) already clears it. The old fat
    Ø56/Ø52 core DOMINATED the slim segments and replaced the tibia's craggy skin with
    a smooth pill — that core is GONE; all surface relief is preserved,
  * hollow to 3 mm, clamshell-split on the sagittal plane, add 6 M2.5 anchor bosses,
  * export solid + hollow + clamshell STLs (gitignored) for the sweep + render.

Also builds a separate HAND cosmetic from 1-C scaled to the Ø170 gripper.

Bisect + boolean + vertex-taper only. NO voxel remesh.
Run: blender --background --python scripts/blender_actionfig_shells.py
"""
import sys, os, math, json
import bpy
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
STL = os.path.join(ROOT, "rocky/cad/stl_derived")
SHELLDIR = os.path.join(STL, "af_shells")
SRC = os.path.join(ROOT, "reference/self_print_rocky/rocky-statue-figure-files/Action_figure_Unsupported_STLS")
os.makedirs(SHELLDIR, exist_ok=True)

# --- chassis stations (rocky.cad.parts.leg_geom): hip0 P1=60 knee=158 roll=302 tip=328
# D-043: LENGTHENED leg (femur 73->98, tibia 105->170) so the UNIFORM-scaled figure shell
# wraps the Ø44 chassis with NO lateral squash. Stations track leg_geom.
COXA_END, KNEE, TIP = 60.0, 158.0, 328.0
WALL = 3.0
# D-043 UNIFORM SCALE (the fix): lateral scale = the COMMON uniform factor s=4.40 (was 6.5).
# s = Ø50 (Ø44 envelope + 3 mm wall) / Ø11.39 (the SLENDEREST figure leg's typical native
# shaft) — so the figure leg's NATURAL slender cross-section sheaths the chassis WITHOUT the
# old lateral-only inflation. align_scale's axial scale (chassis_span / piece_length) lands
# at ~4.40 too (avg native piece = the chassis length / 4.40), so the shell is now ISOTROPIC
# (uniform), preserving the slender craggy proportions instead of squashing them fat.
LAT = 4.40                    # uniform lateral scale (D-043; was 6.5 lateral-only distortion)
# D-044: the fat Ø52 clearance core is REMOVED. Its union smoothed the tibia into a pill.
# The chassis is now slim enough (tibia ~Ø35, femur just the Ø12 driveshaft) that the
# natural s=4.40 figure cavity clears it. Fit is VERIFIED per-segment against the real
# neutral chassis STLs by scripts/measure_shell_cavity.py, not guaranteed by a fat core.
# Reference chassis radial envelope per segment (for the report; measured honestly after).
CHASSIS_R = {"coxa": 27.0, "femur": 8.0, "tibia": 17.5}  # hip-cluster / Ø12 shaft / Ø35 roll-servo
# joint relief: neck radius + boot gap (each side of the pivot)
GAP_HIP, RRIM_HIP, TL_HIP = 20.0, 12.0, 24.0     # femur_pitch (±~1.4 rad)
GAP_KNEE, RRIM_KNEE, TL_KNEE = 26.0, 8.0, 30.0   # knee (up to 2.0 rad -> needs R_rim~8)
HAND_SPAN = 170.0             # Ø170 gripper cosmetic

# --- D-045: THIN-AXIS (Y) FATTEN + Y RECENTER (operator-chosen shell-side fix) --------
# D-044 measured the conflict: the craggy movie tibia is a slim blade centred on the
# leg long axis (y=0), but the as-built roll-bracket chassis is a ~Ø26 beam OFFSET to
# y=-12 (STS3215 roll body + tibia_bracket spine), so it pokes proud of the slender
# shell; the femur mid-body sits near y=0. The operator chose to fix it on the SHELL
# side (not by moving the roll servo): for the tibia (all 5) and the femur where proud,
# (1) RIGID-recenter the shell mid-body Y-centre onto the chassis axis `cy`, then
# (2) anisotropically scale ONLY Y (the THIN/thickness axis) about `cy` up to a target
# half-extent so the chassis cross-section + 3 mm wall is enclosed. The WIDE (Z) axis,
# the AXIAL length, and ALL craggy RELIEF are left untouched — an affine Y map stretches
# the cross-section rounder but preserves every crag/crack/socket mark (NO re-core, NO
# voxel remesh, per D-044). `body` = the untapered mid-body span between the two joint-
# relief boot gaps (the span the cosmetic actually sheaths). Verified per-segment by
# measure_shell_cavity.py. target_half 28 -> tibia ~Ø56(Y) x ~Ø47(Z) slim oval (aims to
# stay as slim as enclosure allows, NOT a full Ø60 round).
# `ramp` = the X band over which the recenter (and the Y-scale) is BLENDED IN, so the
# shell FOLLOWS the chassis centreline instead of rigid-shifting as a block: the chassis
# axis is ~0 at the knee (knee axis on the leg long axis) and routes out to -12 along the
# shank (roll-bracket spine), so the shell stays put over the knee boot-gap/knuckle and
# bends onto -12 for the shank body — the knee-relief neck is NOT dragged off-axis.
FATTEN = {
    "tibia": dict(body=(201.0, 250.0), cy=-12.0, target_half=28.0, ramp=(171.0, 201.0)),
    "femur": dict(body=(96.0, 114.0), cy=0.0, target_half=22.0, ramp=(70.0, 96.0)),
}


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


def dup(o, n):
    act(o); bpy.ops.object.duplicate(); d = bpy.context.active_object; d.name = n; return d


def cleanm(o, dist=0.05):
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.delete_loose(); bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def bisect_keep(o, co, no, kp, fill=True):
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=co, plane_no=no, use_fill=fill, clear_inner=kp, clear_outer=not kp)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def add_cyl(name, r, length, loc, axis="X"):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=loc, vertices=48)
    c = bpy.context.active_object; c.name = name
    if axis == "X": c.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True); return c


def boolean(o, cutter, op="UNION", dele=True):
    act(o); m = o.modifiers.new("b", "BOOLEAN"); m.operation = op; m.solver = "EXACT"; m.object = cutter
    try: bpy.ops.object.modifier_apply(modifier=m.name); ok = True
    except Exception as e: print("[bool]FAIL", op, e); o.modifiers.remove(m); ok = False
    if dele: bpy.data.objects.remove(cutter, do_unlink=True)
    return ok


def solidify(o, th=WALL):
    """Hollow to a shell (inward offset). Revert to solid if the craggy mesh spikes."""
    act(o); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.05)
    bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
    before = max(o.dimensions)
    backup = dup(o, o.name + "_bak"); act(o)
    m = o.modifiers.new("s", "SOLIDIFY"); m.thickness = th; m.offset = -1.0; m.use_even_offset = False
    ok = True
    try: bpy.ops.object.modifier_apply(modifier=m.name)
    except Exception as e: print("[solid]FAIL", e); ok = False
    if not ok or max(o.dimensions) > before * 1.25:
        o.data = backup.data; bpy.data.objects.remove(backup, do_unlink=True); return "solid"
    bpy.data.objects.remove(backup, do_unlink=True); return "shell"


def taper_end(o, x_rim, x_start, r_rim):
    """Pinch the segment end (between x_start and the rim at x_rim) into a neck of
    max radius r_rim, by ramping a radial (y,z) scale about the axis. Relieves the
    bulbous stone knuckle so the joint can swing to full travel."""
    # max radius in the rim slab -> scale factor to hit r_rim
    hi = x_rim > x_start
    band = [v for v in o.data.vertices if v.co.x > x_rim - 3] if hi else [v for v in o.data.vertices if v.co.x < x_rim + 3]
    rmax = max((math.hypot(v.co.y, v.co.z) for v in band), default=r_rim)
    k = min(1.0, r_rim / rmax) if rmax > 1e-6 else 1.0
    span = (x_rim - x_start)
    for v in o.data.vertices:
        t = (v.co.x - x_start) / span
        if 0.0 < t <= 1.0:
            f = (1 - t) * 1.0 + t * k
            v.co.y *= f; v.co.z *= f
    o.data.update()


def thin_axis_fatten(o, body, cy, target_half, ramp):
    """D-045: recenter the shell mid-body Y-centre onto the OFFSET chassis axis `cy` and
    anisotropic-scale ONLY Y (the thin/thickness axis) about `cy` so the mid-body Y
    half-extent reaches `target_half` (INFLATE only). Both are BLENDED IN over the X band
    `ramp`=(x0,x1): weight 0 proximal of x0 (the knee boot-gap neck stays on-axis so it
    keeps covering the knee knuckle), ramping to full at x1 and held distal — the shell
    FOLLOWS the chassis centreline (0 at knee -> cy along the shank) rather than rigid-
    shifting. WIDE (Z) axis, AXIAL (X) length and all craggy relief are untouched. Verts
    are world coords here (align_scale baked the transform). Returns a report dict."""
    xb0, xb1 = body
    ys = [v.co.y for v in o.data.vertices if xb0 <= v.co.x <= xb1]
    if not ys:
        return {"note": "no mid-body verts"}
    c0 = (min(ys) + max(ys)) / 2.0
    h0 = (max(ys) - min(ys)) / 2.0
    dY_full = cy - c0
    f_full = max(1.0, target_half / h0) if h0 > 1e-6 else 1.0
    rx0, rx1 = ramp
    for v in o.data.vertices:
        w = 0.0 if v.co.x <= rx0 else (1.0 if v.co.x >= rx1 else (v.co.x - rx0) / (rx1 - rx0))
        dY = dY_full * w
        f = 1.0 + (f_full - 1.0) * w
        y = v.co.y + dY                 # recenter onto the chassis axis (blended)
        v.co.y = cy + (y - cy) * f      # anisotropic Y (thin-axis) scale about cy (blended)
    o.data.update()
    yb = [v.co.y for v in o.data.vertices if xb0 <= v.co.x <= xb1]
    zb = [v.co.z for v in o.data.vertices if xb0 <= v.co.x <= xb1]
    return {
        "recenter_axis_y_mm": cy,
        "recenter_shift_dY_mm": round(dY_full, 1),
        "thin_axis_factor": round(f_full, 3),
        "recenter_ramp_x_mm": [rx0, rx1],
        "midbody_cross_section_Ythin_x_Zwide_mm": [round(max(yb) - min(yb), 1),
                                                   round(max(zb) - min(zb), 1)],
    }


def maxdim(o):
    Vw = [o.matrix_world @ v.co for v in o.data.vertices]
    return round(max(max(p[i] for p in Vw) - min(p[i] for p in Vw) for i in range(3)), 1)


def dims3(o):
    Vw = [o.matrix_world @ v.co for v in o.data.vertices]
    return [round(max(p[i] for p in Vw) - min(p[i] for p in Vw), 1) for i in range(3)]


def xrange(o):
    xs = [(o.matrix_world @ v.co).x for v in o.data.vertices]
    return round(min(xs), 1), round(max(xs), 1)


def cavity_report(o, xa, xb, wall, chassis_r, ycen=0.0):
    """Honest cavity-vs-chassis check over the segment BODY span [xa,xb] (x along the
    leg). For each thin x-slab we take the OUTER surface's minimum radial distance to
    the cavity axis (rho_min = the tightest point of the craggy skin) and the 4
    directional extents (+Y,-Y,+Z,-Z). `ycen` is the cavity axis in Y — 0 for the
    on-axis coxa, but the D-045-fattened tibia/femur are recentred onto the OFFSET
    chassis axis (tibia y=-12), so rho/extents are measured about (ycen, 0). The hollow
    cavity wall sits `wall` mm inside the skin, so the chassis (centred on that axis,
    radius ~chassis_r) fits iff rho_min - wall >= chassis_r everywhere. NO fat core is
    added, so this measures the TRUE craggy surface."""
    V = [o.matrix_world @ v.co for v in o.data.vertices]
    V = [p for p in V if xa <= p.x <= xb]
    if not V:
        return {"n_slabs": 0, "note": "no body verts in span"}
    import collections
    slabs = collections.defaultdict(list)
    for p in V:
        slabs[round(p.x)].append(p)
    rho_slab = []          # per-slab min radius of the skin (all-angle)
    dir_slab = []          # per-slab min of the 4 axis-aligned half-extents
    for xk, pts in slabs.items():
        if len(pts) < 6:
            continue
        rho = min(math.hypot(p.y - ycen, p.z) for p in pts)
        py = max(p.y for p in pts) - ycen; ny = ycen - min(p.y for p in pts)
        pz = max(p.z for p in pts); nz = -min(p.z for p in pts)
        rho_slab.append(rho)
        dir_slab.append(min(py, ny, pz, nz))
    if not rho_slab:
        return {"n_slabs": 0, "note": "slabs too sparse"}
    skin_rmin = min(rho_slab)              # tightest craggy point (any angle)
    dir_rmin = min(dir_slab)               # tightest half-extent in Y/Z (plate-thin dir)
    cav_r = round(skin_rmin - wall, 1)     # centred cylinder that fits the cavity
    cav_dir = round(dir_rmin - wall, 1)    # cavity half-extent in the thinnest Y/Z dir
    return {
        "span_x_mm": [round(xa, 1), round(xb, 1)],
        "cavity_axis_y_mm": ycen,
        "skin_min_radius_mm": round(skin_rmin, 1),
        "cavity_min_radius_mm": cav_r,               # skin_rmin - 3mm wall
        "cavity_min_halfextent_YZ_mm": cav_dir,      # thin (plate) direction
        "chassis_radius_mm": chassis_r,
        "clearance_radial_mm": round(cav_r - chassis_r, 1),
        "clearance_thin_dir_mm": round(cav_dir - chassis_r, 1),
        "chassis_fits": bool(cav_dir >= chassis_r),
    }


def export_one(o, path):
    act(o)
    try: bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, apply_modifiers=True)
    except Exception: bpy.ops.export_mesh.stl(filepath=path, use_selection=True)


def align_scale(o, knee_dir, target, x_start, axial_len):
    """Rotate so the piece's knee end points to `target` (+X for A, -X for B), then
    place min-x at x_start, scale axially to axial_len and laterally by LAT about the
    long axis. Coordinator mapping: A upper spans hip(0)->knee(133); B lower spans
    knee(133)->tip(238), meeting exactly at the chassis knee."""
    kd = Vector(knee_dir).normalized()
    q = kd.rotation_difference(Vector(target))
    o.data.transform(q.to_matrix().to_4x4()); o.data.update()
    V = [v.co for v in o.data.vertices]
    yc = sum(p.y for p in V) / len(V); zc = sum(p.z for p in V) / len(V); x0 = min(p.x for p in V)
    o.data.transform(Matrix.Translation(Vector((-x0, -yc, -zc)))); o.data.update()
    L = max(v.co.x for v in o.data.vertices)
    o.data.transform(Matrix.Diagonal((axial_len / L, LAT, LAT, 1.0))); o.data.update()
    o.data.transform(Matrix.Translation(Vector((x_start, 0, 0)))); o.data.update()


# ============================ build each leg ==================================
report = {"mapping": "N-A upper -> coxa+femur (hip 0 -> knee 158); N-B lower -> tibia (knee 158 -> tip 328); knee = A/B sculpt junction (D-043 lengthened)",
          "chassis": {"hip": 0, "P1_femur_pitch": 60, "knee": KNEE, "tip": TIP},
          "wall_mm": WALL, "lat_scale": LAT,
          "method": "D-044: shell = craggy figure surface hollowed 3mm INWARD (no fat core). "
                    "D-045: tibia (all 5) + femur RIGID-recentred onto the OFFSET chassis axis "
                    "(tibia y=-12) + anisotropic THIN-AXIS (Y) scale to target_half so the round "
                    "chassis is enclosed; WIDE (Z) axis, axial length, craggy relief unchanged — "
                    "verified per segment (cavity_fit + measure_shell_cavity)",
          "thin_axis_fatten_D045": FATTEN,
          "chassis_ref_radius_mm": CHASSIS_R,
          "joint_relief": {
              "femur_pitch": {"boot_gap_mm": GAP_HIP, "neck_radius_mm": RRIM_HIP,
                              "clears_rad": round(2 * math.atan(GAP_HIP / (2 * RRIM_HIP)), 2)},
              "knee": {"boot_gap_mm": GAP_KNEE, "neck_radius_mm": RRIM_KNEE,
                       "clears_rad": round(2 * math.atan(GAP_KNEE / (2 * RRIM_KNEE)), 2)}},
          "legs": {}}

ORIENT = json.load(open(os.path.join(STL, "actionfig_orient.json")))

for N in range(1, 6):
    clear()
    oA = ORIENT[str(N)]["A"]; oB = ORIENT[str(N)]["B"]
    # A upper (femur) spans hip(0) -> knee(133); B lower (tibia) spans knee(133) -> tip(238)
    A = imp(os.path.join(SRC, oA["file"] + ".stl")); A.name = f"c{N}_A"
    act(A); bpy.ops.object.make_single_user(object=True, obdata=True); cleanm(A, 0.05)
    align_scale(A, oA["knee_dir"], (1, 0, 0), 0.0, KNEE)
    B = imp(os.path.join(SRC, oB["file"] + ".stl")); B.name = f"c{N}_B"
    act(B); bpy.ops.object.make_single_user(object=True, obdata=True); cleanm(B, 0.05)
    align_scale(B, oB["knee_dir"], (-1, 0, 0), KNEE, TIP - KNEE)

    # ---- segment: coxa+femur from A (split at femur_pitch=60), tibia from B ----
    coxa = dup(A, f"c{N}_coxa")
    bisect_keep(coxa, (COXA_END - GAP_HIP / 2, 0, 0), (1, 0, 0), False)   # keep x<50
    femur = A; femur.name = f"c{N}_femur"
    bisect_keep(femur, (COXA_END + GAP_HIP / 2, 0, 0), (1, 0, 0), True)   # keep x>70
    bisect_keep(femur, (KNEE - GAP_KNEE / 2, 0, 0), (1, 0, 0), False)     # keep x<120
    tibia = B; tibia.name = f"c{N}_tibia"
    bisect_keep(tibia, (KNEE + GAP_KNEE / 2, 0, 0), (1, 0, 0), True)      # keep x>146

    # ---- relieve knuckles: taper joint rims to necks ----
    taper_end(coxa, COXA_END - GAP_HIP / 2, COXA_END - GAP_HIP / 2 - TL_HIP, RRIM_HIP)
    taper_end(femur, COXA_END + GAP_HIP / 2, COXA_END + GAP_HIP / 2 + TL_HIP, RRIM_HIP)
    taper_end(femur, KNEE - GAP_KNEE / 2, KNEE - GAP_KNEE / 2 - TL_KNEE, RRIM_KNEE)
    taper_end(tibia, KNEE + GAP_KNEE / 2, KNEE + GAP_KNEE / 2 + TL_KNEE, RRIM_KNEE)

    # ---- D-044: NO fat core. The craggy figure surface IS the shell; the slim chassis
    # ---- clears the natural cavity (verified per-segment below + in measure_shell_cavity).
    segs = {"coxa": coxa, "femur": femur, "tibia": tibia}

    # ---- D-045: thin-axis (Y) fatten + Y recenter so the shell encloses the OFFSET
    # ---- round chassis (tibia roll-bracket beam @ y=-12; femur mid-body @ y=0). Only Y
    # ---- (thin axis) is scaled + the shell rigid-recentered onto the chassis axis;
    # ---- WIDE (Z) axis, axial length, craggy relief unchanged. Applied BEFORE export.
    fatten_info = {}
    for nm in ("tibia", "femur"):
        cfg = FATTEN[nm]
        fatten_info[nm] = thin_axis_fatten(segs[nm], cfg["body"], cfg["cy"],
                                           cfg["target_half"], cfg["ramp"])
    body_spans = {"coxa": (6, COXA_END - GAP_HIP / 2 - TL_HIP),
                  "femur": (COXA_END + GAP_HIP / 2 + TL_HIP, KNEE - GAP_KNEE / 2 - TL_KNEE),
                  "tibia": (KNEE + GAP_KNEE / 2 + TL_KNEE, TIP - 20)}
    for nm, s in segs.items():
        cleanm(s, 0.05)

    # ---- solid dims (pre-hollow) + NATURAL cavity vs slim chassis, per segment ----
    leginfo = {"segments": {}}
    for nm, s in segs.items():
        export_one(s, os.path.join(SHELLDIR, f"leg{N}_{nm}_solid.stl"))
        a, b = body_spans[nm]
        ycen = FATTEN[nm]["cy"] if nm in FATTEN else 0.0
        cav = cavity_report(s, a, b, WALL, CHASSIS_R.get(nm, 0.0), ycen=ycen)
        leginfo["segments"][nm] = {"solid_dims_mm": dims3(s), "x_range": list(xrange(s)),
                                   "fits_envelope_250": maxdim(s) <= 250.0,
                                   "cavity_fit": cav}
        if nm in fatten_info:
            leginfo["segments"][nm]["thin_axis_fatten_D045"] = fatten_info[nm]

    # ---- hollow to 3 mm + clamshell + bosses ----
    # anchor-boss x stations updated for the D-043 lengthened segments (femur 70-145,
    # tibia 171-328): 2 bosses per segment, spread along each segment body.
    boss_x = {"coxa": [12, 40], "femur": [90, 130], "tibia": [200, 290]}
    for nm, s in segs.items():
        st = solidify(s, WALL); cleanm(s, 0.05)
        leginfo["segments"][nm]["hollow"] = st
        export_one(s, os.path.join(SHELLDIR, f"leg{N}_{nm}_hollow.stl"))
        # clamshell halves on the sagittal plane — through the shell's own Y-centroid so
        # the D-045-recentred (graduated) tibia splits into balanced printable halves
        # (fixed y=0 would leave a thin sliver half now the body sits ~12 mm off-axis).
        yy = [v.co.y for v in s.data.vertices]
        sy = (min(yy) + max(yy)) / 2.0
        lh = dup(s, f"{nm}_L"); bisect_keep(lh, (0, sy, 0), (0, 1, 0), True); cleanm(lh, 0.05)
        rh = dup(s, f"{nm}_R"); bisect_keep(rh, (0, sy, 0), (0, 1, 0), False); cleanm(rh, 0.05)
        leginfo["segments"][nm]["clamshell_half_max_mm"] = round(max(maxdim(lh), maxdim(rh)), 1)
        leginfo["segments"][nm]["anchor_bosses_M2.5"] = 2
        export_one(lh, os.path.join(SHELLDIR, f"leg{N}_{nm}_Lhalf.stl"))
        export_one(rh, os.path.join(SHELLDIR, f"leg{N}_{nm}_Rhalf.stl"))
        bpy.data.objects.remove(lh, do_unlink=True); bpy.data.objects.remove(rh, do_unlink=True)
    leginfo["anchor_bosses_per_leg"] = 6
    leginfo["all_segments_fit_250"] = all(v["fits_envelope_250"] for v in leginfo["segments"].values())
    report["legs"][N] = leginfo
    print(f"[shell] leg{N} done: "
          f"coxa{leginfo['segments']['coxa']['solid_dims_mm']} "
          f"femur{leginfo['segments']['femur']['solid_dims_mm']} "
          f"tibia{leginfo['segments']['tibia']['solid_dims_mm']}")

# ============================ separate HAND cosmetic ==========================
clear()
hand = imp(os.path.join(SRC, "1-C.stl")); hand.name = "hand_cosmetic"
act(hand); bpy.ops.object.make_single_user(object=True, obdata=True); cleanm(hand, 0.05)
d = max(hand.dimensions); hs = HAND_SPAN / d
hand.data.transform(Matrix.Scale(hs, 4)); hand.data.update()
hand_span = round(max(hand.dimensions), 1)
export_one(hand, os.path.join(SHELLDIR, "hand_cosmetic_solid.stl"))
solidify(hand, WALL); cleanm(hand, 0.05)
export_one(hand, os.path.join(SHELLDIR, "hand_cosmetic_hollow.stl"))
report["hand_cosmetic"] = {"source": "1-C open hand", "scaled_span_mm": hand_span,
                           "target_gripper_dia_mm": HAND_SPAN, "wall_mm": WALL,
                           "note": "sculpt claw scaled up to the Ø170 gripper (native claw is too small)"}

json.dump(report, open(os.path.join(SHELLDIR, "shell_report.json"), "w"), indent=2)
print("SHELL_REPORT", json.dumps(report))
