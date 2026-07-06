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
        |  4. hardware cavities: RS00 servo pockets at joints, thorax electronics bay,
        |     grafted 3-finger stone HAND + micro-servo pocket at each tip
        |  5. printability check (250 mm envelope)
        v
  rocky/cad/stl_derived/*.stl   (gitignored) + docs/media/rocky_stl_assembly.png

The pipeline is parametric on the master + reference/stl/.axis.npy; re-running
reproduces the same parts.  See the run-end report for anatomy notes.

Host venv only:  .venv/bin/python scripts/segment_rocky_stl.py
"""
from __future__ import annotations
import json, math, os, sys, time
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
SERVO      = (60.0, 60.0, 35.0)   # Robstride RS00 pocket  (Ø60 x 35 cavity)
GRIP_SERVO = (22.8, 12.2, 28.5)   # grip micro servo pocket
JETSON_TRAY = (90.0, 63.0, 30.0)
BATTERY_6S  = (85.0, 40.0, 25.0)
ENVELOPE   = 250.0                 # Bambu P2S build volume (mm)

PITCH  = float(os.environ.get("ROCKY_PITCH", "1.5"))   # voxel remesh pitch (mm)
R_CORE = 62.0                      # thorax core radius (mm); legs live beyond it
WALL   = 4.0                       # target shell wall for hollowing (mm)

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
    """Two largest-curvature interior points of the medial curve = coxa|femur and
    femur|tibia joints.  Falls back to 1/3, 2/3 of the span if detection is flat."""
    s0, s1 = mids[0], mids[-1]
    if len(mids) >= 5:
        d2 = np.abs(np.gradient(np.gradient(zcs, mids), mids))
        picks = []
        for i in np.argsort(-d2):
            si = mids[i]
            if si < s0 + 15 or si > s1 - 15:
                continue
            if all(abs(si - p) > 18 for p in picks):
                picks.append(si)
            if len(picks) == 2:
                break
        if len(picks) == 2:
            return sorted(picks)
    span = s1 - s0
    return [s0 + span / 3.0, s0 + 2 * span / 3.0]


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
def carve_servo(mesh, cx, cy, zc, ang_deg, s_cut, z_at):
    """Subtract an RS00 pocket (Ø60 x 35) at a joint, hinge axis tangential."""
    rad = np.array([math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg)), 0.0])
    tang = np.array([-rad[1], rad[0], 0.0])
    ctr = np.array([cx, cy, 0.0]) + rad * s_cut + np.array([0, 0, z_at])
    pocket = trimesh.creation.cylinder(radius=SERVO[0] / 2.0, height=SERVO[2])
    T = trimesh.geometry.align_vectors([0, 0, 1], tang)
    pocket.apply_transform(T)
    pocket.apply_translation(ctr)
    try:
        out = mesh.difference(pocket)
        out = largest_body(out)
        if out.is_watertight and out.volume > 0.3 * mesh.volume:
            return out, True
    except Exception:                          # noqa
        pass
    return mesh, False


def stone_hand(cx, cy, zc, ang_deg, tip_pt, size=1.0):
    """Graft: 3 tapered stone finger shards splayed 120 deg at the leg tip, plus a
    stubby palm knuckle, as ONE union.  Crude but reads as a 3-finger Eridian claw.
    Scaled from grip_finger.py (FINGER_LEN 46 -> ~34, ROOT_R 11 -> ~8)."""
    rad = np.array([math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg)), 0.0])
    tang = np.array([-rad[1], rad[0], 0.0])
    down = np.array([0, 0, -1.0])
    flen, root_r, tip_r = 34.0 * size, 8.0 * size, 2.5 * size
    palm = trimesh.creation.icosphere(subdivisions=2, radius=11.0 * size)
    palm.apply_translation(tip_pt)
    pieces = [palm]
    # finger directions: outward-down, splayed +/- around the tangential axis
    base_dir = (rad * 0.6 + down * 0.8)
    base_dir /= np.linalg.norm(base_dir)
    for az in (-40, 0, 40):
        d = base_dir + tang * math.tan(math.radians(az))
        d /= np.linalg.norm(d)
        fng = trimesh.creation.cone(radius=root_r, height=flen, sections=3)
        # cone apex at +Z; align +Z -> finger direction, taper naturally
        fng.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d))
        fng.apply_translation(tip_pt + d * (flen * 0.15))
        pieces.append(fng)
    try:
        hand = trimesh.boolean.union(pieces)
        return largest_body(hand)
    except Exception:                          # noqa
        return None


# ================================================================ printability ==
def size_report(mesh):
    e = mesh.extents
    return dict(x=round(float(e[0]), 1), y=round(float(e[1]), 1), z=round(float(e[2]), 1),
                fits=bool(max(e) <= ENVELOPE))


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
    fig.suptitle("ROCKY-5 — segmented articulated parts (pose-normalized crab stance)",
                 fontsize=15)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


# ==================================================================== main ======
def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MEDIA, exist_ok=True)
    log(f"pitch={PITCH} R_core={R_CORE}")

    m = trimesh.load(MASTER)
    m.merge_vertices()
    ax = np.load(AXIS)
    cx, cy = float(ax[0]), float(ax[1])
    log(f"master faces={len(m.faces)} watertight={m.is_watertight} axis=({cx:.2f},{cy:.2f})")

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
    p = os.path.join(OUT, "thorax.stl")
    thorax_final.export(p)
    # thorax is a naturally thin carapace dome; report its shell wall estimate
    twall = mw if mw else wall_estimate(thorax_final)
    report["parts"]["thorax"] = dict(size_report(thorax_final), watertight=bool(thorax_final.is_watertight),
                                     wall_mm=twall, shell="native_dome" if not mw else "eroded",
                                     cavities=["jetson_tray", "battery_6s"])
    log(f"thorax -> {size_report(thorax_final)} wall~{twall}")

    # ---- LEGS ------------------------------------------------------------------
    legs_all = largest_body(S.difference(core)) if S.body_count == 1 else S.difference(core)
    colored = [(thorax_final, [150, 150, 160, 255])]
    seg_colors = {"coxa": [200, 120, 90, 255], "femur": [180, 160, 110, 255],
                  "tibia": [150, 130, 120, 255], "hand": [210, 90, 90, 255]}
    n = len(centers)
    cc = np.sort(centers)
    for i in range(n):
        c_ang = float(cc[i])
        # gap planes straddling this center
        lo = max([g for g in gaps if g < c_ang], default=None)
        hi = min([g for g in gaps if g > c_ang], default=None)
        if lo is None:
            lo = float(max(gaps)) - 360
        if hi is None:
            hi = float(min(gaps)) + 360
        leg = cut_between(legs_all, cx, cy, zc, lo, hi)
        if not leg.is_watertight or leg.volume < 500:
            report["notes"].append(f"leg{i+1}: extraction weak (wt={leg.is_watertight}); skipped")
            continue
        mids, zcs = medial_curve(leg, cx, cy, c_ang)
        s1, s2 = bend_points(mids, zcs)
        # three segments along the radial axis
        coxa = largest_body(slice_at_radius(leg, cx, cy, zc, c_ang, s1, keep_outer=False))
        mid = slice_at_radius(leg, cx, cy, zc, c_ang, s1, keep_outer=True)
        femur = largest_body(slice_at_radius(mid, cx, cy, zc, c_ang, s2, keep_outer=False))
        tibia = largest_body(slice_at_radius(mid, cx, cy, zc, c_ang, s2, keep_outer=True))

        segs = {"coxa": coxa, "femur": femur, "tibia": tibia}
        legrep = dict(center_deg=round(c_ang, 1),
                      bend_radii_mm=[round(float(s1), 1), round(float(s2), 1)],
                      segments={})
        # servo pockets at the two joints (in femur, which spans both joints)
        z1, z2 = medial_z_at(mids, zcs, s1), medial_z_at(mids, zcs, s2)
        femur, ok1 = carve_servo(femur, cx, cy, zc, c_ang, s1, z1)
        femur, ok2 = carve_servo(femur, cx, cy, zc, c_ang, s2, z2)
        segs["femur"] = femur
        # hollow segments (best effort)
        for nm in ("coxa", "femur", "tibia"):
            sh, w = hollow(segs[nm], WALL, PITCH)
            segs[nm] = sh
            legrep["segments"].setdefault(nm, {})["wall_mm"] = w
        # graft 3-finger hand + micro-servo pocket onto the tibia tip
        tip_pt = segs["tibia"].vertices[np.argmax(
            (segs["tibia"].vertices[:, 0] - cx) * math.cos(math.radians(c_ang)) +
            (segs["tibia"].vertices[:, 1] - cy) * math.sin(math.radians(c_ang)))]
        hand = stone_hand(cx, cy, zc, c_ang, tip_pt)
        hand_ok = False
        if hand is not None:
            try:
                tib_h = trimesh.boolean.union([segs["tibia"], hand])
                tib_h = largest_body(tib_h)
                if tib_h.is_watertight:
                    # micro-servo pocket near the palm
                    gs = trimesh.creation.box(GRIP_SERVO)
                    gs.apply_translation(tip_pt)
                    tib2 = largest_body(tib_h.difference(gs))
                    segs["tibia"] = tib2 if tib2.is_watertight else tib_h
                    hand_ok = True
            except Exception:
                pass
        legrep["hand_grafted"] = hand_ok
        legrep["servo_pockets"] = {"coxa_femur_joint": ok1, "femur_tibia_joint": ok2}

        for nm, mesh in segs.items():
            mesh = finalize(mesh)
            segs[nm] = mesh
            fn = os.path.join(OUT, f"leg{i+1}_{nm}.stl")
            mesh.export(fn)
            legrep["segments"].setdefault(nm, {})
            legrep["segments"][nm].update(size_report(mesh),
                                          watertight=bool(mesh.is_watertight))
            col = seg_colors[nm]
            colored.append((mesh, col))
        report["parts"][f"leg{i+1}"] = legrep
        log(f"leg{i+1}: center={c_ang:.1f} bends={[round(s1,1),round(s2,1)]} "
            f"servos=({ok1},{ok2}) hand={hand_ok}")

    # ---- preview + report ------------------------------------------------------
    png = os.path.join(MEDIA, "rocky_stl_assembly.png")
    try:
        _render_mpl(colored, png, None)
        log(f"preview -> {png}")
    except Exception as e:                      # noqa
        report["notes"].append(f"preview render failed: {e}")
        log("preview FAILED", e)

    # honest hardware note: RS00 is Ø60; legs are far slimmer
    seg_widths = []
    for nm, pr in report["parts"].items():
        if nm.startswith("leg"):
            for sn, sr in pr["segments"].items():
                seg_widths.append(min(sr.get("x", 999), sr.get("y", 999)))
    if seg_widths:
        report["notes"].append(
            f"RS00 servo is Ø{SERVO[0]:.0f}mm; leg segment min cross-sections are "
            f"~{min(seg_widths):.0f}-{max(seg_widths):.0f}mm, so a FULLY ENCLOSED servo "
            f"cavity does not fit inside a leg. The Ø60 pockets that carved cleanly are "
            f"open joint SADDLES; at this scale the RS00 must mount as the external "
            f"structural hub bridging two segments, not buried inside one.")

    # printability summary
    oversize = []
    for nm, pr in report["parts"].items():
        if nm == "thorax":
            if not pr["fits"]:
                oversize.append(nm)
        else:
            for sn, sr in pr["segments"].items():
                if not sr.get("fits", True):
                    oversize.append(f"{nm}_{sn}")
    report["oversize_parts"] = oversize
    report["runtime_s"] = round(time.time() - t0, 1)

    with open(os.path.join(OUT, "segment_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    log(f"done in {report['runtime_s']}s; parts in {OUT}; oversize={oversize}")
    return report


if __name__ == "__main__":
    main()
