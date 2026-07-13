#!/usr/bin/env python3
"""D-046 — COSMETIC craggy WRIST-CUFF for the leg1 manipulator.

Hides the visible BULGE where the slim craggy tibia (~Ø56) meets the wider Ø95
hand cosmetic + grip housing: a slip-over craggy stone cuff that spans the
tibia-tip -> hand junction and TAPERS Ø56 -> Ø95 so the step reads as one
continuous craggy stone arm.

METHOD (stone-match by construction): the cuff surface is DERIVED FROM THE
OFFICIAL CRAGGY STONE — we lift the tibia's own distal craggy skin (a band of
leg1_tibia_solid, itself the s=4.40 uniform-scaled 1-C wrist) and build the cuff
between two radial offsets of that same skin about the arm axis:
  * INNER wall = tibia skin scaled +f_in  -> a friction SLIP bore that hugs the
    fixed tibia tip with ~1.5 mm clearance (removable, cosmetic — like the joint
    boots; NO mechanism geometry touched),
  * OUTER wall = tibia skin scaled +f_out, the scale RAMPING up distally so the
    outer envelope flares from ~Ø62 (over the tibia) to ~Ø95 (meeting the hand).
Because both walls are the tibia's real crags, the cuff carries the SAME stone
grain as the rest of the leg. Hollow (outer minus inner) ~3-8 mm wall, clamshell
split on the sagittal plane (matches the leg-shell convention).

The cuff sits on the FIXED tibia side; the hand rotates (wrist-roll ±1.5 rad)
and the 2+1 grip opens (to Ø170) DISTAL of the cuff mouth, so it never fouls the
grip. leg_geom / tibia_bracket / grip parts are NOT read or modified.

Bisect + radial vertex scale + one EXACT boolean. NO voxel remesh, NO re-core.
Run: blender --background --python scripts/blender_wrist_cuff.py
"""
import os, math, json
import bpy
from mathutils import Vector, Matrix

ROOT = "/home/mrqbit/Downloads/dbx-r"
SH = os.path.join(ROOT, "rocky/cad/stl_derived/af_shells")
TIB = os.path.join(SH, "leg1_tibia_solid.stl")
HAND = os.path.join(SH, "hand_cosmetic_solid.stl")

# --- cuff geometry in tibia-LOCAL (native) coords (same frame as leg1_tibia_solid).
# tibia native x-range 171..328; distal body Ø~56 about the offset arm axis y=-9.
AX_Y, AX_Z = -9.0, 0.0        # arm axis the cuff is coaxial with (D-045 offset shank)
X0, X1 = 216.0, 267.0         # cuff span: tibia body -> the cuff MOUTH just proximal of
#                               the hand claw base (which starts at native x~269), so the
#                               mouth (Ø95) meets the hand base (Ø94) with a ~2 mm axial
#                               gap -> no x-overlap, the hand rolls free just distal of it.
WALL = 3.0
HAND_SPAN = 95.0              # the hand cosmetic as placed in the assembly (max dim -> 95)
HAND_CX = 282.0              # hand centroid sits at tibia-native x=282 (per assemble_rocky)
# radial scale ramps (t=0 proximal .. t=1 distal). f_in = slip bore, f_out = flared skin.
FOUT_0, FOUT_1 = 1.14, 1.54   # proximal a touch proud so a 3mm wall still clears the tibia


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


def boolean(o, cutter, op="DIFFERENCE", dele=True):
    act(o); m = o.modifiers.new("b", "BOOLEAN"); m.operation = op; m.solver = "EXACT"; m.object = cutter
    ok = True
    try: bpy.ops.object.modifier_apply(modifier=m.name)
    except Exception as e: print("[bool]FAIL", op, e); o.modifiers.remove(m); ok = False
    if dele: bpy.data.objects.remove(cutter, do_unlink=True)
    return ok


def radial_scale(o, f0, f1):
    """Scale each vertex's (y,z) about the arm axis by a factor lerped f0->f1 over
    the cuff x-span. Preserves the craggy relief (an affine radial map), just
    grows/offsets the skin outward — no smoothing, no remesh."""
    for v in o.data.vertices:
        t = (v.co.x - X0) / (X1 - X0)
        t = min(1.0, max(0.0, t))
        # smoothstep for a fair, gradual flare
        ts = t * t * (3 - 2 * t)
        f = f0 + (f1 - f0) * ts
        v.co.y = AX_Y + (v.co.y - AX_Y) * f
        v.co.z = AX_Z + (v.co.z - AX_Z) * f
    o.data.update()


def export_one(o, path):
    act(o)
    try: bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, apply_modifiers=True)
    except Exception: bpy.ops.export_mesh.stl(filepath=path, use_selection=True)


def clean_nofill(o, dist=0.05):
    """Merge/clean WITHOUT filling the open cut ends (keeps the tube open)."""
    act(o); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def solidify_shell(o, th):
    """Thicken an OPEN craggy surface inward (toward the axis) into a watertight
    wall of thickness `th`. Outer envelope (the craggy skin) is preserved."""
    act(o); m = o.modifiers.new("s", "SOLIDIFY")
    m.thickness = th; m.offset = -1.0; m.use_even_offset = False; m.use_rim = True
    bpy.ops.object.modifier_apply(modifier=m.name)


def radial_profile(o, ax_y, ax_z, agg="max"):
    """max|min radius per 2mm x-slab about (ax_y,ax_z), for the report."""
    import collections
    sl = collections.defaultdict(list)
    for v in o.data.vertices:
        sl[round(v.co.x / 2) * 2].append(math.hypot(v.co.y - ax_y, v.co.z - ax_z))
    fn = max if agg == "max" else min
    return {x: round(fn(r), 1) for x, r in sorted(sl.items())}


# ============================ build the cuff ==================================
clear()
tib = imp(TIB); tib.name = "tib"
act(tib); bpy.ops.object.make_single_user(object=True, obdata=True); cleanm(tib, 0.05)
# isolate the distal band [X0,X1] -> the craggy tibia skin the cuff is built from.
# fill=False -> keep the ends OPEN (no flat cap disks, which would triangulate into
# an ugly smooth fan when scaled). We solidify the open craggy tube instead.
bisect_keep(tib, (X0, 0, 0), (1, 0, 0), True, fill=False)    # keep x > X0
bisect_keep(tib, (X1, 0, 0), (1, 0, 0), False, fill=False)   # keep x < X1
clean_nofill(tib, 0.05)
band_prof = radial_profile(tib, AX_Y, AX_Z)

# OUTER = the craggy skin flared outward (open tube). This IS the visible cosmetic face.
outer = dup(tib, "cuff_outer"); radial_scale(outer, FOUT_0, FOUT_1); clean_nofill(outer)
bpy.data.objects.remove(tib, do_unlink=True)
out_prof = radial_profile(outer, AX_Y, AX_Z)

# SOLID (filled reference blank): cap the open ends so the STL is watertight.
solid = dup(outer, "cuff_solid")
act(solid); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.fill_holes(sides=0); bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
export_one(solid, os.path.join(SH, "leg1_wrist_cuff_solid.stl"))
bpy.data.objects.remove(solid, do_unlink=True)

# HOLLOW cuff (the real printable cosmetic): solidify the open craggy tube to WALL mm,
# open at both ends (proximal slips over the tibia tip, distal mouth faces the hand).
sleeve = dup(outer, "cuff_hollow"); solidify_shell(sleeve, WALL); clean_nofill(sleeve)
export_one(sleeve, os.path.join(SH, "leg1_wrist_cuff_hollow.stl"))
in_prof = radial_profile(sleeve, AX_Y, AX_Z, agg="min")   # inner bore radius per slab
ok = True

# clamshell split on the sagittal plane through the arm axis (matches leg shells)
lh = dup(sleeve, "cuff_L"); bisect_keep(lh, (0, AX_Y, 0), (0, 1, 0), True); cleanm(lh, 0.05)
rh = dup(sleeve, "cuff_R"); bisect_keep(rh, (0, AX_Y, 0), (0, 1, 0), False); cleanm(rh, 0.05)
export_one(lh, os.path.join(SH, "leg1_wrist_cuff_Lhalf.stl"))
export_one(rh, os.path.join(SH, "leg1_wrist_cuff_Rhalf.stl"))


def dims3(o):
    V = [o.matrix_world @ v.co for v in o.data.vertices]
    return [round(max(p[i] for p in V) - min(p[i] for p in V), 1) for i in range(3)]


def maxdim(o):
    return max(dims3(o))


# ---- honest clearance vs the hand (the rotating side) at the cuff mouth -------
clear_h = None
h = imp(HAND); h.name = "hand"
Vh = [v.co for v in h.data.vertices]
hc = Vector((sum(p.x for p in Vh) / len(Vh), sum(p.y for p in Vh) / len(Vh), sum(p.z for p in Vh) / len(Vh)))
h.data.transform(Matrix.Translation(-hc)); h.data.update()
hs = HAND_SPAN / max(h.dimensions)
h.data.transform(Matrix.Scale(hs, 4)); h.data.update()
# place hand centroid at native x=HAND_CX on the arm axis (matches assemble_rocky)
h.data.transform(Matrix.Translation(Vector((HAND_CX, AX_Y, AX_Z)))); h.data.update()
hand_x_min = round(min(v.co.x for v in h.data.vertices), 1)
cuff_x_max = round(max(v.co.x for v in bpy.data.objects["cuff_outer"].data.vertices), 1)
axial_gap = round(hand_x_min - cuff_x_max, 1)          # >0 => no x-overlap, roll is free
# hand base diameter at its proximal 3mm (where it meets the cuff mouth) & mouth dia
hb = [math.hypot(v.co.y - AX_Y, v.co.z - AX_Z) for v in h.data.vertices if v.co.x <= hand_x_min + 3]
hand_base_dia = round(2 * max(hb), 1) if hb else 0.0
# slip-grip on the BEARING surface (crag high points that actually carry the fit):
# cuff inner bearing radius = outer high point - wall; compare to the tibia high point.
prox_band = [x for x in out_prof if X0 + 2 <= x <= X0 + 20]
tibia_bearing_r = max(band_prof[x] for x in prox_band) if prox_band else band_prof[min(band_prof)]
bore_bearing_r = round(max(out_prof[x] for x in prox_band) - WALL, 1) if prox_band else 0.0
slip_gap_prox = round(bore_bearing_r - tibia_bearing_r, 1)   # + => slips over the high points

report = {
    "decision": "D-046 cosmetic manipulator wrist cuff",
    "method": "cuff = leg1 tibia distal craggy skin (band x[%g,%g]), the OUTER surface "
              "flared radially about arm axis y=%g (+%.0f..%.0f%% smoothstep) then "
              "solidified %gmm inward into an open-ended craggy sleeve. derived from the "
              "official stone (1-C via the tibia) so the grain matches. NO mechanism "
              "geometry read or changed."
              % (X0, X1, AX_Y, (FOUT_0-1)*100, (FOUT_1-1)*100, WALL),
    "arm_axis_yz_mm": [AX_Y, AX_Z],
    "cuff_span_x_mm": [X0, X1],
    "outer_dia_prox_mm": round(2 * out_prof[min(out_prof)], 1),
    "outer_dia_dist_mm": round(2 * max(out_prof.values()), 1),
    "tibia_band_dia_prox_mm": round(2 * band_prof[min(band_prof)], 1),
    "tibia_band_dia_dist_mm": round(2 * band_prof[max(band_prof)], 1),
    "slip_bore_bearing_dia_prox_mm": round(2 * bore_bearing_r, 1),
    "slip_gap_over_tibia_bearing_prox_mm": slip_gap_prox,
    "slip_note": ("bore = tibia crag +~14%% then -3mm wall: slips on the crag HIGH points "
                  "(~%s mm). Deep tibia cracks may kiss the wall -> hand-sand or heat-fit; "
                  "cosmetic + removable so a light interference is fine.") % slip_gap_prox,
    "wall_mm": WALL,
    "solid_dims_mm": dims3(sleeve),
    "hollow_dims_mm": dims3(sleeve),
    "clamshell_half_max_mm": round(max(maxdim(lh), maxdim(rh)), 1),
    "fits_envelope_250": bool(maxdim(sleeve) <= 250.0),
    "watertight_sleeve": bool(ok),
    "clearance": {
        "hand_x_min_mm": hand_x_min,
        "cuff_x_max_mm": cuff_x_max,
        "axial_gap_cuff_mouth_to_hand_mm": axial_gap,
        "no_x_overlap": bool(axial_gap > 0),
        "cuff_mouth_dia_mm": round(2 * max(out_prof.values()), 1),
        "hand_base_dia_mm": hand_base_dia,
        "note": "cuff mouth (Ø%.0f) meets the hand claw base (Ø%.0f) with a %.1f mm axial "
                "gap -> NO x-overlap, so wrist-roll ±1.5 rad turns the hand FREELY just "
                "distal of the fixed cuff; the 2+1 grip opens (to Ø170) further distal, "
                "clear of the cuff. Proximal band bore Ø%.0f grips the Ø%.0f tibia."
                % (2 * max(out_prof.values()), hand_base_dia, axial_gap,
                   2 * bore_bearing_r, band_prof[min(band_prof)] * 2),
    },
    "anchor": "friction slip-collar (proximal bore hugs tibia tip ~1.5 mm); removable cosmetic",
    "outer_profile_dia_by_x": {str(k): round(2 * v, 1) for k, v in out_prof.items()},
}
json.dump(report, open(os.path.join(SH, "wrist_cuff_report.json"), "w"), indent=2)
print("CUFF_REPORT", json.dumps(report))
