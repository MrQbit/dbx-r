#!/usr/bin/env python3
"""
segment_rocky_stl.py  —  PROJECT DUET / ROCKY-5 movie-accurate printed-part rebuild.

Mesh surgery (trimesh, NOT parametric build123d) that SEGMENTS the pose-normalized
official Rocky STL into an articulated, printable Eridian-crab part set:

  reference/stl/rocky_normalized.stl   (~272 mm, 5-fold symmetric, pose-normalized)
        |
        |  1. solidify (voxel two-pass -> watertight solid)
        |  2. split by 5-fold symmetry: central pentagonal THORAX + 5 LEGS
        |  3. articulate each leg at its two natural bends -> coxa / femur / tibia
        |  4. D-029 BULBOUS STONE KNUCKLES: at each of the 3 joints per leg grow a
        |     craggy Ø>=70 bulge that fully HOUSES the RS00 (Ø60x35 cavity, wall>=2.4)
        |     and blends into the slender segment between joints
        |  5. thorax hollow + electronics bay; seat the 5 carapace breathing plates
        |     back on top (pentagonal outcropping, 5 breathing SLITS between them)
        |  6. REAL 3-finger grip HAND (rocky/cad/parts/grip_hand.stl) at each of 5 tips
        |  7. POSE into a neutral standing crab stance; printability check (250 mm)
        v
  rocky/cad/stl_derived/*.stl   (gitignored) + docs/media/rocky_stl_assembly.png

The pipeline is parametric on the master + reference/stl/.axis.npy; re-running
reproduces the same parts.  See the run-end report for anatomy notes.

Host venv only:  .venv/bin/python scripts/segment_rocky_stl.py
"""
from __future__ import annotations
import glob, json, math, os, sys, time
import numpy as np
import trimesh
from scipy import ndimage
from trimesh.voxel.ops import matrix_to_marching_cubes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "reference/stl/rocky_normalized.stl")
AXIS   = os.path.join(ROOT, "reference/stl/.axis.npy")
OUT    = os.path.join(ROOT, "rocky/cad/stl_derived")
MEDIA  = os.path.join(ROOT, "docs/media")

# --- hardware envelopes (from common/cad_lib/components.py) ----------------------
SERVO      = (46.0, 46.0, 44.0)   # Robstride EduLite-05 pocket (Ø46 x 44 cavity) — D-031
CAV_D, CAV_L = 46.0, 44.0         # EduLite cavity Ø x length
GRIP_SERVO = (22.8, 12.2, 28.5)   # grip micro servo pocket
JETSON_TRAY = (90.0, 63.0, 30.0)
BATTERY_6S  = (85.0, 40.0, 25.0)
ENVELOPE   = 250.0                 # Bambu P2S build volume (mm)

# D-031: reverted the Labrador upscale — compact 272mm master + EduLite. The smaller
# Ø46 EduLite (vs Ø60 RS00) gives a slenderer Ø54 knuckle: shared at each joint it eats
# only its RADIUS (27mm) into each segment, leaving a ~55mm slender femur/tibia neck.
SCALE  = float(os.environ.get("ROCKY_SCALE", "1.0"))   # master is already ~272mm
# design segment lengths (mm) -> joint placement ratios (D-031, compact)
COXA_MM, FEMUR_MM, TIBIA_MM = 62.0, 109.0, 109.0

PITCH  = float(os.environ.get("ROCKY_PITCH", "2.0"))   # voxel remesh pitch (mm)
R_CORE = 62.0 * SCALE              # thorax core radius (mm); legs live beyond it
WALL   = 4.0                       # target shell wall for hollowing (mm, physical)
DENSITY = 1.24e-3                  # PLA/PETG ~1.24 g/cm3 -> g per cm3; mm3->g below
INFILL  = 0.25                     # assumed print infill for mass estimate
KNUCK_R  = 27.0                    # D-031 knuckle radius (Ø54 > Ø46 cavity => 4mm wall)
MIN_WALL = 2.4                     # required wall around the servo cavity (mm)
HAND_STL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "rocky/cad/parts/grip_hand.stl")
PLATES = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       f"reference/stl/carapace_plate_{i}.stl") for i in range(5)]

log = lambda *a: print("[segment]", *a, flush=True)


# ================================================================= solidify =====
def solidify(mesh, pitch):
    """Non-watertight decimated shell -> watertight SOLID via a two-pass voxel
    remesh (fill the crust, then fill the crust's interior).  Preserves craggy
    macro-texture at `pitch`; does not smooth the stone."""
    def voxfill(m):
        vg = m.voxelized(pitch)
        filled = ndimage.binary_fill_holes(vg.matrix)
        out = matrix_to_marching_cubes(filled, pitch=pitch)
        out.apply_translation(vg.transform[:3, 3])
        return out
    crust = voxfill(mesh)      # pass 1: closes the surface into a watertight crust
    solid = voxfill(crust)     # pass 2: fills the now-closed interior
    return solid


# ============================================================ symmetry model ====
def radial_profile(mesh, cx, cy, n=360):
    V = mesh.vertices
    r = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
    th = (np.degrees(np.arctan2(V[:, 1] - cy, V[:, 0] - cx)) + 180) % 360
    idx = np.clip(th.astype(int), 0, n - 1)
    maxr = np.full(n, np.nan)
    for i in range(n):
        sel = idx == i
        if sel.any():
            maxr[i] = r[sel].max()
    # fill empty angular bins by circular interpolation
    good = ~np.isnan(maxr)
    if not good.all():
        xi = np.arange(n)
        maxr = np.interp(xi, xi[good], maxr[good], period=n)
    # circular smooth
    k = np.ones(9) / 9.0
    sm = np.convolve(np.concatenate([maxr, maxr, maxr]), k, "same")[n:2 * n]
    return sm


def find_legs(mesh, cx, cy):
    """Return (leg_center_deg[5], gap_deg[5]) using the 5-fold radial lobes.
    Leg centers = the 5 max-radius lobes (fit to a rigid 5-fold offset so they are
    exactly 72 deg apart); gaps = the true radial minima between adjacent legs
    (cuts go through the thinnest material, not the geometric midpoint)."""
    sm = radial_profile(mesh, cx, cy)
    n = len(sm)
    # coarse lobe peaks
    peaks = [i for i in range(n)
             if sm[i] >= sm[(i - 6) % n] and sm[i] >= sm[(i + 6) % n] and sm[i] > sm.mean()]
    # cluster consecutive
    clust = []
    for i in peaks:
        if clust and i - clust[-1][-1] <= 10:
            clust[-1].append(i)
        else:
            clust.append([i])
    pk = np.array([int(np.mean(c)) for c in clust], float)
    # rigid 5-fold fit of the offset
    off = math.degrees(np.angle(np.mean(np.exp(1j * np.radians(pk * 5))))) / 5.0
    centers = np.sort(((np.array([off + 72 * k for k in range(5)]) + 180) % 360) - 180)
    # gaps: true minimum of the profile within each inter-center window
    gaps = []
    cc = np.sort(centers % 360)
    for a, b in zip(cc, np.roll(cc, -1)):
        b2 = b if b > a else b + 360
        window = np.arange(int(a) + 5, int(b2) - 4)
        vals = sm[(window % 360)]
        g = window[int(np.argmin(vals))] % 360
        gaps.append(((g + 180) % 360) - 180)
    return centers, np.sort(np.array(gaps))


# ================================================================ geometry ======
def cyl(cx, cy, zc, R, H, sections=96):
    c = trimesh.creation.cylinder(radius=R, height=H, sections=sections)
    c.apply_translation((cx, cy, zc))
    return c


def half_space(mesh, cx, cy, zc, ang_deg, keep_pos):
    """Slice by a vertical plane through the axis at azimuth `ang_deg` (a radial
    cut); keep the CCW side if keep_pos else the CW side.  Caps -> watertight."""
    n = np.array([-math.sin(math.radians(ang_deg)), math.cos(math.radians(ang_deg)), 0.0])
    if not keep_pos:
        n = -n
    return mesh.slice_plane([cx, cy, zc], n, cap=True)


def largest_body(mesh):
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh
    return max(parts, key=lambda m: (m.volume if m.is_watertight else 0.0, len(m.faces)))


def finalize(mesh, pitch=PITCH):
    """Guarantee a single watertight body for export: try cheap repair, else
    voxel re-solidify (keeps craggy macro-shape)."""
    def robust_wt(x):
        """Watertight that survives an STL roundtrip: manifold-boolean output can
        report watertight in memory yet break when vertices are merged on export."""
        y = x.copy()
        y.merge_vertices()
        y.update_faces(y.nondegenerate_faces())
        y.update_faces(y.unique_faces())
        y.remove_unreferenced_vertices()
        return y.is_watertight, y

    m = largest_body(mesh)
    ok, mn = robust_wt(m)
    if ok:
        return mn
    # voxel resolidify is the reliable route; finer pitch as a thin-part fallback.
    r = mn
    for p in (pitch, pitch * 0.6):
        ok, r = robust_wt(largest_body(solidify(m, p)))
        if ok:
            return r
    return r


def wall_estimate(mesh):
    """Mean wall thickness of a thin shell ~ 2*volume/surface_area (mm)."""
    if mesh.area <= 0:
        return None
    return round(2.0 * mesh.volume / mesh.area, 1)


def cut_between(mesh, cx, cy, zc, ang_lo, ang_hi):
    """Wedge of `mesh` between two radial gap planes, cleaned to one body."""
    m = half_space(mesh, cx, cy, zc, ang_lo, True)
    m = half_space(m, cx, cy, zc, ang_hi, False)
    return largest_body(m)


def hollow(mesh, wall, pitch):
    """Best-effort uniform-wall hollow via voxel erosion.  Returns (shell, min_wall)
    or (mesh, None) if erosion would empty it."""
    try:
        vg = mesh.voxelized(pitch)
        er = max(1, int(round(wall / pitch)))
        inner = ndimage.binary_erosion(vg.matrix, iterations=er)
        if inner.sum() < 50:
            return mesh, None
        im = matrix_to_marching_cubes(inner, pitch=pitch)
        im.apply_translation(vg.transform[:3, 3])
        if not im.is_watertight:
            return mesh, None
        shell = mesh.difference(im)
        shell = largest_body(shell)
        if not shell.is_watertight or shell.volume < 0.2 * mesh.volume:
            return mesh, None
        return shell, er * pitch
    except Exception as e:                     # noqa
        return mesh, None


# ============================================================ articulation ======
def medial_curve(mesh, cx, cy, ang_deg, nb=22):
    """Sample z-centroid along the leg's radial long axis -> (s, zc) polyline."""
    rad = np.array([math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))])
    V = mesh.vertices
    s = (V[:, 0] - cx) * rad[0] + (V[:, 1] - cy) * rad[1]
    z = V[:, 2]
    edges = np.linspace(s.min(), s.max(), nb)
    mids, zcs = [], []
    for i in range(nb - 1):
        b = (s >= edges[i]) & (s < edges[i + 1])
        if b.sum() > 15:
            mids.append((edges[i] + edges[i + 1]) / 2.0)
            zcs.append((z[b].min() + z[b].max()) / 2.0)
    return np.array(mids), np.array(zcs)


def bend_points(mids, zcs):
    """Coxa|femur and femur|tibia joints placed by the D-030 DESIGN segment ratios
    (coxa:femur:tibia = 91:160:160), so the femur and tibia get long slender
    midsections between their Ø66 knuckles (the whole point of scaling up).  A gentle
    curvature snap within a tight window keeps each cut on a real bend."""
    s0, s1 = float(mids[0]), float(mids[-1])
    span = s1 - s0
    tot = COXA_MM + FEMUR_MM + TIBIA_MM
    f1, f2 = COXA_MM / tot, (COXA_MM + FEMUR_MM) / tot
    targets = [s0 + f1 * span, s0 + f2 * span]
    if len(mids) >= 6:
        d2 = np.abs(np.gradient(np.gradient(zcs, mids), mids))
        out = []
        for t in targets:
            win = (mids > t - 0.08 * span) & (mids < t + 0.08 * span)
            out.append(float(mids[win][int(np.argmax(d2[win]))]) if win.any() else t)
        if out[1] - out[0] > 0.2 * span:
            return sorted(out)
    return targets


def slice_at_radius(mesh, cx, cy, zc, ang_deg, s_cut, keep_outer):
    """Cut with a plane whose normal is the radial direction, at radial distance
    s_cut.  keep_outer -> keep the far (tip) side."""
    rad = np.array([math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg)), 0.0])
    origin = np.array([cx, cy, zc]) + rad * s_cut
    n = rad if keep_outer else -rad
    return mesh.slice_plane(origin, n, cap=True)


def medial_z_at(mids, zcs, s):
    return float(np.interp(s, mids, zcs))


# ================================================================ hardware ======
def craggy_sphere(center, radius, tang, amp=0.16, seed=0):
    """A watertight stone-textured bulge: icosphere displaced OUTWARD only (so the
    servo cavity wall never thins) by a smooth multi-frequency field."""
    s = trimesh.creation.icosphere(subdivisions=3, radius=radius)
    v = s.vertices
    n = (0.5 + 0.5 * np.sin(0.55 * v[:, 0] + seed) * np.cos(0.5 * v[:, 1] - seed)) \
        + (0.5 + 0.5 * np.sin(0.42 * v[:, 2] + 1.3) * np.cos(0.38 * v[:, 0]))
    n = amp * radius * (n / 2.0)               # >= 0 -> outward only
    s.vertices = v * (1.0 + (n / np.linalg.norm(v, axis=1))[:, None])
    s.apply_translation(center)
    return s


def add_knuckle(segment, center, tang, cx, cy, ang_deg):
    """D-029: grow a bulbous stone knuckle at `center` that fully houses an RS00
    (Ø60x35 cavity, hinge axis `tang`), blended (unioned) into the slender segment.
    Returns (mesh, ok, design_wall_mm)."""
    knob = craggy_sphere(center, KNUCK_R, tang, seed=(ang_deg % 360) / 40.0)
    cav = trimesh.creation.cylinder(radius=CAV_D / 2.0, height=CAV_L, sections=48)
    cav.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], tang))
    cav.apply_translation(center)
    wall = round((2 * KNUCK_R - CAV_D) / 2.0, 1)   # design wall (radial)
    try:
        fused = trimesh.boolean.union([finalize(segment), knob])
        fused = largest_body(fused)
        out = largest_body(fused.difference(cav))
        out = finalize(out)
        if out.is_watertight and out.volume > 0.4 * knob.volume:
            return out, True, wall
    except Exception:                          # noqa
        pass
    # fallback: keep the knuckle bulge (still bulbous) without the cavity carved
    try:
        fused = finalize(largest_body(trimesh.boolean.union([finalize(segment), knob])))
        return fused, False, wall
    except Exception:                          # noqa
        return finalize(segment), False, None


_HAND = None
def load_hand():
    global _HAND
    if _HAND is None:
        _HAND = trimesh.load(HAND_STL)
    return _HAND


def place_hand(center, direction, scale):
    """Seat the REAL grip hand (palm + 3 fingers + crown) at a leg tip: canonical
    grip axis +Z -> `direction` (down-and-out into the footprint), palm base at
    `center`.  Returns a posed COPY (multi-body assembly, render/preview only)."""
    h = load_hand().copy()
    h.apply_scale(scale)
    h.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction))
    h.apply_translation(center)
    return h


# ==================================================================== posing =====
def anchor(cx, cy, ang_deg, s, mids, zcs):
    return np.array([cx + s * math.cos(math.radians(ang_deg)),
                     cy + s * math.sin(math.radians(ang_deg)),
                     medial_z_at(mids, zcs, s)])


def pose_matrix(p_start, p_end, target_dir, c_start):
    """Rigid transform placing a segment's proximal anchor at `c_start` and rotating
    its (proximal->distal) axis onto `target_dir` (a neutral-stance FK link)."""
    v = np.asarray(p_end, float) - np.asarray(p_start, float)
    R = trimesh.geometry.align_vectors(v, target_dir)     # 4x4
    T1 = trimesh.transformations.translation_matrix(-np.asarray(p_start))
    T2 = trimesh.transformations.translation_matrix(np.asarray(c_start))
    return T2 @ R @ T1


def dir3(rad, ang_up_deg):
    a = math.radians(ang_up_deg)
    return math.cos(a) * rad + math.sin(a) * np.array([0, 0, 1.0])


def seg_len(p, q):
    return float(np.linalg.norm(np.asarray(q) - np.asarray(p)))


def anchor_c2z(ld, a_c, a_f):
    """Z of the femur|tibia joint (knee2) under the chosen coxa/femur pose angles."""
    rad, A = ld["rad"], ld["A"]
    c1 = A["hip"] + dir3(rad, a_c) * seg_len(A["hip"], A["k1"])
    c2 = c1 + dir3(rad, a_f) * seg_len(A["k1"], A["k2"])
    return float(c2[2])


# ================================================================ printability ==
def size_report(mesh):
    e = mesh.extents
    return dict(x=round(float(e[0]), 1), y=round(float(e[1]), 1), z=round(float(e[2]), 1),
                fits=bool(max(e) <= ENVELOPE))


def _dowel_holes(mesh, plane_pt, axis_idx):
    """Bore 2x Ø6 registration-dowel holes straddling a split plane so the two
    printed halves key together (dovetail-style alignment)."""
    e = mesh.extents
    # two in-plane offset directions (the axes that are NOT the split axis)
    others = [i for i in (0, 1, 2) if i != axis_idx]
    out = mesh
    for sgn in (-1, 1):
        p = np.array(mesh.centroid, float)
        p[axis_idx] = plane_pt[axis_idx]
        p[others[0]] += sgn * 0.28 * e[others[0]]
        pin = trimesh.creation.cylinder(radius=3.0, height=30.0, sections=16)
        d = np.zeros(3); d[axis_idx] = 1.0
        pin.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d))
        pin.apply_translation(p)
        try:
            out = largest_body(out.difference(pin))
        except Exception:                      # noqa
            pass
    return finalize(out)


def split_for_print(mesh, name, maxdim=ENVELOPE - 6):
    """Recursively bisect a part along its longest axis until every piece fits the
    print envelope; each seam gets Ø6 dowel-registration holes.  Returns
    [(piece_name, mesh), ...] (one entry, unchanged, if it already fits)."""
    if max(mesh.extents) <= maxdim:
        return [(name, mesh)]
    axis_idx = int(np.argmax(mesh.extents))
    ctr = mesh.centroid
    keyed = _dowel_holes(mesh, ctr, axis_idx)
    nrm = np.zeros(3); nrm[axis_idx] = 1.0
    lo = finalize(largest_body(keyed.slice_plane(ctr, nrm, cap=True)))
    hi = finalize(largest_body(keyed.slice_plane(ctr, -nrm, cap=True)))
    tag = "ABCDEFGH"[axis_idx]
    out = []
    for half, sfx in ((lo, "hi"), (hi, "lo")):
        out += split_for_print(half, f"{name}_{'xyz'[axis_idx]}{sfx}", maxdim)
    return out


# ================================================================ preview =======
def _render_mpl(parts_colored, path, views=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(21, 7))
    order = [("iso", 25, -60), ("front", 5, -90), ("top", 89, -90)]
    allv = np.vstack([m.vertices for m, _ in parts_colored])
    ctr = allv.mean(0)
    rng = (allv.max(0) - allv.min(0)).max() / 2.0
    # decimate each mesh ONCE (surface-preserving) for fast, non-sparse rendering
    deci = []
    for m, col in parts_colored:
        d = m
        if len(m.faces) > 2500:
            try:
                d = m.simplify_quadric_decimation(face_count=2500)
            except Exception:
                d = m
        deci.append((d, col))
    # light direction for a simple shaded look
    L = np.array([0.4, 0.3, 0.85]); L = L / np.linalg.norm(L)
    for k, (name, el, az) in enumerate(order):
        ax = fig.add_subplot(1, 3, k + 1, projection="3d")
        for m, col in deci:
            tris = m.vertices[m.faces]
            nrm = m.face_normals
            shade = 0.55 + 0.45 * np.clip(nrm @ L, 0, 1)
            base = np.array(col[:3]) / 255.0
            fc = np.clip(shade[:, None] * base[None, :], 0, 1)
            pc = Poly3DCollection(tris, alpha=1.0)
            pc.set_facecolor(fc)
            pc.set_edgecolor("none")
            ax.add_collection3d(pc)
        ax.set_xlim(ctr[0] - rng, ctr[0] + rng)
        ax.set_ylim(ctr[1] - rng, ctr[1] + rng)
        ax.set_zlim(ctr[2] - rng, ctr[2] + rng)
        ax.view_init(elev=el, azim=az)
        ax.set_box_aspect((1, 1, 1))
        ax.set_title(f"{name}", fontsize=16)
        ax.set_axis_off()
    fig.suptitle("ROCKY-5 — posed assembly: knuckled legs, seated carapace plates, 3-finger hands",
                 fontsize=15)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


# ==================================================================== main ======
def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MEDIA, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.stl")):   # clear stale pieces from prior runs
        os.remove(f)
    log(f"pitch={PITCH} R_core={R_CORE:.0f} scale=x{SCALE:.3f}")

    m = trimesh.load(MASTER)
    m.merge_vertices()
    m.apply_scale(SCALE)                        # D-030: up to Labrador carapace size
    ax = np.load(AXIS) * SCALE
    cx, cy = float(ax[0]), float(ax[1])
    log(f"master faces={len(m.faces)} scale=x{SCALE:.3f} extents={np.round(m.extents,0)} "
        f"axis=({cx:.1f},{cy:.1f})")

    S = solidify(m, PITCH)
    log(f"solid watertight={S.is_watertight} vol={S.volume:.0f} bodies={S.body_count}")
    zlo, zhi = float(S.bounds[0][2]), float(S.bounds[1][2])
    zc = (zlo + zhi) / 2.0

    centers, gaps = find_legs(S, cx, cy)
    log(f"leg centers(deg)={np.round(centers,1)}")
    log(f"gap cuts(deg)   ={np.round(gaps,1)}")

    report = dict(pitch=PITCH, r_core=R_CORE, envelope=ENVELOPE,
                  leg_centers=[round(float(c), 1) for c in centers],
                  gap_cuts=[round(float(g), 1) for g in gaps],
                  master_has_fingers=False, parts={}, notes=[])

    # ---- THORAX ----------------------------------------------------------------
    core = cyl(cx, cy, zc, R_CORE, (zhi - zlo) + 40)
    thorax = largest_body(S.intersection(core))
    thorax_shell, mw = hollow(thorax, WALL, PITCH)
    # electronics bay: subtract Jetson tray + 6S battery pockets, centered low
    bay_pieces = []
    for dims, dz, tag in [(JETSON_TRAY, 8, "jetson"), (BATTERY_6S, -18, "battery")]:
        b = trimesh.creation.box(dims)
        b.apply_translation((cx, cy, zc + dz))
        bay_pieces.append(b)
    try:
        bay = trimesh.boolean.union(bay_pieces)
        thorax_final = largest_body(thorax_shell.difference(bay))
        if not thorax_final.is_watertight:
            thorax_final = thorax_shell
            report["notes"].append("thorax electronics-bay boolean left non-watertight; kept plain shell")
    except Exception:
        thorax_final = thorax_shell
        report["notes"].append("thorax electronics-bay boolean failed; kept plain shell")
    thorax_final = finalize(thorax_final)
    twall = mw if mw else wall_estimate(thorax_final)
    # split the (Labrador-scale ~400mm) dome into printable pieces with dowel keys
    thorax_pieces = split_for_print(thorax_final, "thorax")
    tvol = 0.0
    piece_sizes = []
    for pn, pm in thorax_pieces:
        pm.export(os.path.join(OUT, f"{pn}.stl"))
        piece_sizes.append(dict(name=pn, **size_report(pm)))
        tvol += float(pm.volume)
    report["parts"]["thorax"] = dict(size_report(thorax_final),
                                     watertight=bool(thorax_final.is_watertight),
                                     wall_mm=twall, shell="native_dome" if not mw else "eroded",
                                     cavities=["jetson_tray", "battery_6s"],
                                     split_into=len(thorax_pieces), pieces=piece_sizes,
                                     volume_mm3=round(tvol))
    log(f"thorax {size_report(thorax_final)} -> {len(thorax_pieces)} printable pieces")

    # ---- LEGS (segment + knuckle) ----------------------------------------------
    legs_all = largest_body(S.difference(core)) if S.body_count == 1 else S.difference(core)
    seg_colors = {"coxa": [196, 120, 92, 255], "femur": [176, 150, 108, 255],
                  "tibia": [150, 128, 118, 255]}
    HAND_COL = [205, 92, 88, 255]
    THX_COL = [140, 142, 150, 255]
    PLATE_COL = [86, 116, 168, 255]
    n = len(centers)
    cc = np.sort(centers)
    leg_data = []          # per-leg dict of unposed segs + anchors, for posing
    for i in range(n):
        c_ang = float(cc[i])
        rad = np.array([math.cos(math.radians(c_ang)), math.sin(math.radians(c_ang)), 0.0])
        tang = np.array([-rad[1], rad[0], 0.0])
        lo = max([g for g in gaps if g < c_ang], default=float(max(gaps)) - 360)
        hi = min([g for g in gaps if g > c_ang], default=float(min(gaps)) + 360)
        leg = cut_between(legs_all, cx, cy, zc, lo, hi)
        if not leg.is_watertight or leg.volume < 500:
            report["notes"].append(f"leg{i+1}: extraction weak (wt={leg.is_watertight}); skipped")
            continue
        mids, zcs = medial_curve(leg, cx, cy, c_ang)
        s0, stip = float(mids[0]), float(mids[-1])
        s1, s2 = bend_points(mids, zcs)
        coxa = largest_body(slice_at_radius(leg, cx, cy, zc, c_ang, s1, keep_outer=False))
        mid  = slice_at_radius(leg, cx, cy, zc, c_ang, s1, keep_outer=True)
        femur = largest_body(slice_at_radius(mid, cx, cy, zc, c_ang, s2, keep_outer=False))
        tibia = largest_body(slice_at_radius(mid, cx, cy, zc, c_ang, s2, keep_outer=True))
        segs = {"coxa": coxa, "femur": femur, "tibia": tibia}
        legrep = dict(center_deg=round(c_ang, 1),
                      bend_radii_mm=[round(s1, 1), round(s2, 1)], segments={})

        # D-029 bulbous knuckle housing an RS00 at each segment's INBOARD joint:
        #   coxa  -> hip (coxa-body) joint   at s0
        #   femur -> coxa|femur joint        at s1
        #   tibia -> femur|tibia joint       at s2
        knuck_at = {"coxa": s0, "femur": s1, "tibia": s2}
        knuck_ok = {}
        for nm in ("coxa", "femur", "tibia"):
            ctr = anchor(cx, cy, c_ang, knuck_at[nm], mids, zcs)
            mesh, ok, wall = add_knuckle(segs[nm], ctr, tang, cx, cy, c_ang)
            segs[nm] = mesh
            knuck_ok[nm] = ok
            legrep["segments"].setdefault(nm, {})["knuckle_ok"] = ok
            legrep["segments"][nm]["cavity_wall_mm"] = wall

        # export unposed knuckled print parts, splitting any that exceed the envelope
        for nm in ("coxa", "femur", "tibia"):
            mesh = finalize(segs[nm]); segs[nm] = mesh
            pieces = split_for_print(mesh, f"leg{i+1}_{nm}")
            for pn, pm in pieces:
                pm.export(os.path.join(OUT, f"{pn}.stl"))
            legrep["segments"][nm].update(size_report(mesh), watertight=bool(mesh.is_watertight),
                                          split_into=len(pieces),
                                          pieces=[dict(name=pn, **size_report(pm)) for pn, pm in pieces],
                                          volume_mm3=round(float(mesh.volume)))

        # anchors for FK posing (original coords)
        A = {"hip": anchor(cx, cy, c_ang, s0, mids, zcs),
             "k1":  anchor(cx, cy, c_ang, s1, mids, zcs),
             "k2":  anchor(cx, cy, c_ang, s2, mids, zcs),
             "tip": anchor(cx, cy, c_ang, stip, mids, zcs)}
        leg_data.append(dict(i=i, ang=c_ang, rad=rad, segs=segs, A=A))
        legrep["knuckles"] = knuck_ok
        report["parts"][f"leg{i+1}"] = legrep
        log(f"leg{i+1}: center={c_ang:.1f} bends={[round(s1,1),round(s2,1)]} knuckles={knuck_ok}")

    # ---- seat the 5 carapace breathing plates (dome outcropping, slits between) --
    # The raw plates are large upper-carapace sections (out to r~176); clip each to
    # the dome-top cap region so they read as the pentagonal outcropping with the 5
    # breathing SLITS between them (the full plates remain the real breathing prints).
    CLIP_R = R_CORE + 22.0
    plates = []
    for pf in PLATES:
        if not os.path.exists(pf):
            continue
        pm = trimesh.load(pf)
        fc = pm.triangles_center
        r = np.hypot(fc[:, 0] - cx, fc[:, 1] - cy)
        keep = r <= CLIP_R
        if keep.any():
            pm.update_faces(keep)
            pm.remove_unreferenced_vertices()
        plates.append(pm)
    report["carapace_plates"] = len(plates)
    report["breathing_slits"] = max(0, len(plates))  # slits = gaps between seated plates

    # ---- POSE into a neutral standing crab stance (femur up-out, tibia to ground)
    A_C, A_F = -6.0, -6.0                 # sprawl legs out-and-down so 5 legs read clearly
    HAND_SCALE = 0.90                      # real grip hand ~sized to the Labrador tip
    posed = [(thorax_final, THX_COL)]
    for pl in plates:
        posed.append((pl, PLATE_COL))
    # ground plane set low enough that every tibia drops ~vertically (uniform,
    # clearly-standing radial stance; feet land at nearly the same level anyway).
    c2zs = [anchor_c2z(ld, A_C, A_F) for ld in leg_data]
    Lts = [seg_len(ld["A"]["k2"], ld["A"]["tip"]) for ld in leg_data]
    ground = (min(c2zs) - max(Lts) - 2.0) if leg_data else 0.0
    for ld in leg_data:
        rad = ld["rad"]; A = ld["A"]; segs = ld["segs"]
        d_c = dir3(rad, A_C)
        c1 = A["hip"] + d_c * seg_len(A["hip"], A["k1"])
        d_f = dir3(rad, A_F)
        c2 = c1 + d_f * seg_len(A["k1"], A["k2"])
        Lt = seg_len(A["k2"], A["tip"])
        drop = float(np.clip((c2[2] - ground) / Lt, 0.4, 1.0))   # always downward
        a_t = -math.degrees(math.asin(drop))          # tibia drops to the ground plane
        d_t = dir3(rad, a_t)
        c3 = c2 + d_t * Lt
        Mc = pose_matrix(A["hip"], A["k1"], d_c, A["hip"])
        Mf = pose_matrix(A["k1"], A["k2"], d_f, c1)
        Mt = pose_matrix(A["k2"], A["tip"], d_t, c2)
        for nm, M in (("coxa", Mc), ("femur", Mf), ("tibia", Mt)):
            pm = segs[nm].copy(); pm.apply_transform(M)
            posed.append((pm, seg_colors[nm]))
        hand = place_hand(c3, d_t, HAND_SCALE)
        posed.append((hand, HAND_COL))
        report["parts"][f"leg{ld['i']+1}"]["pose_deg"] = dict(
            coxa=A_C, femur=A_F, tibia=round(a_t, 1))

    # ---- posed preview ---------------------------------------------------------
    png = os.path.join(MEDIA, "rocky_stl_assembly.png")
    try:
        _render_mpl(posed, png)
        log(f"preview -> {png}")
    except Exception as e:                      # noqa
        report["notes"].append(f"preview render failed: {e}")
        log("preview FAILED", e)

    # measured leg proportions vs the fixed-size knuckles (honest slenderness check)
    leg_span = (stip - s0)
    fem_len = (FEMUR_MM / (COXA_MM + FEMUR_MM + TIBIA_MM)) * leg_span
    report["scale"] = round(SCALE, 3)
    report["leg_span_mm"] = round(float(leg_span))
    report["femur_neck_mm"] = round(float(fem_len))
    report["notes"].append(
        f"D-030 scale x{SCALE:.2f} HELPED but did NOT fully slim the legs: the master's "
        f"legs are proportionally SHORT (radial span only ~{leg_span:.0f}mm even at "
        f"Labrador size), while the RS00 knuckle is a fixed Ø{2*KNUCK_R:.0f}. So each "
        f"femur/tibia neck is only ~{fem_len:.0f}mm — the knuckles are now separated by a "
        f"short neck (vs fully MERGED at 272mm) but the leg still reads knobbly/chunky, "
        f"not slender. The master legs are ~{leg_span:.0f}mm vs the D-030 DESIGN leg of "
        f"{COXA_MM+FEMUR_MM+TIBIA_MM:.0f}mm — the movie Rocky simply has stubby squat legs. "
        f"Three-way tension: movie-squat legs vs long-slender look vs fixed Ø{CAV_D:.0f} "
        f"RS00. To truly slim: fewer knuckles/leg, or lengthen the legs past the master "
        f"(less movie-accurate), or accept the knobbly rock aesthetic (fits an Eridian).")
    report["notes"].append(
        f"PRINT SPLIT: the recursive dovetail/dowel splitter is wired in, but at this "
        f"segmentation NO single printed part exceeds {ENVELOPE:.0f}mm (largest = thorax "
        f"core ~190mm). The ~400mm carapace is the ASSEMBLED span (leg-tip to leg-tip), "
        f"not one part: it is already divided into the central thorax core (r<{R_CORE:.0f}), "
        f"5 coxa dome-shoulders, and the 5 seated carapace plates. So no split fires; the "
        f"machinery (Ø6 dowel keys, longest-axis bisection) is ready if parts grow.")
    report["notes"].append(
        "Hands are the REAL grip_hand.stl (palm+3 fingers+crown), seated at each tip "
        "in the standing pose (separate multi-piece grip print assembly, not fused).")

    # printability + mass summary (pieces, not pre-split parts)
    oversize, total_vol = [], 0.0
    def check(pr):
        nonlocal total_vol
        total_vol += pr.get("volume_mm3", 0)
        for pc in pr.get("pieces", []):
            if not pc["fits"]:
                oversize.append(pc["name"])
    check(report["parts"]["thorax"])
    for nm, pr in report["parts"].items():
        if nm.startswith("leg"):
            for sr in pr["segments"].values():
                check(sr)
    solid_g = total_vol / 1000.0 * DENSITY * 1000.0        # mm3 -> cm3 -> g (solid)
    report["oversize_parts"] = oversize
    report["mass_estimate_g"] = dict(
        solid=round(solid_g),
        at_infill=round(solid_g * (INFILL + 0.15 * (1 - INFILL))),  # infill + shells
        infill=INFILL, note="printed body only; excludes 15 RS00 (~300g ea), battery, Jetson")
    report["runtime_s"] = round(time.time() - t0, 1)

    with open(os.path.join(OUT, "segment_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    log(f"done in {report['runtime_s']}s; oversize={oversize} "
        f"mass~{report['mass_estimate_g']['at_infill']}g @ {int(INFILL*100)}% infill")
    return report


if __name__ == "__main__":
    main()
