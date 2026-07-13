"""LEG4 per-finger grip GLOVES v2 — trimesh + manifold3d build (operator correction).

3 snap-fit covers for the real 2+1 grip:
  * 2 PRIMARY covers: THICK + FLAT craggy blades (toy's flat forked foot tip). The
    fused primaries touch, so each is a C-section glove split at the cleft seam
    (z=+/-0.15) and carved 0.35mm clear of the neighbour blade. Axial slide-on
    (follows the blade's 16deg twist); retention = past-center wrap (0.6->3.4mm
    undercut root->tip) + 0.25mm detent band preload.
  * 1 THUMB cover: SMALLER/THINNER full-wrap glove, snap-on axially, 0.25mm detent
    ring; mouth distal of the clevis ears.

SNAP-FIT cavity = finger + FIT_SLIDE 0.20mm/side. WALK-BEARING tip cap >=3.3mm wall,
low-amp crag. GRAB faces (toward opposing digit): low-amp crag + modest wall.
Outer crag matched to leg4 stone (freq 0.09/mm, amp 2.5, 4 octaves).
"""
import json, math
import numpy as np
import trimesh
from trimesh import creation, boolean

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
CD = SP + "/leg4_finger_covers"

NF = 0.09
FIT = 0.20        # FIT_SLIDE_MM (common/cad_lib/standards.py)
DETENT = 0.25     # detent interference per side
SEAM = 0.80       # half the 1.6mm cleft groove — 3 DISTINCT fingers (operator)
ROOT = np.array([369.0, 7.0, 0.0])
AX_A = np.array([0.9272, 0.3664, +0.0779])
AX_B = np.array([0.9272, 0.3664, -0.0779])
D_GRIP_PRIM = np.array([-0.7071, -0.7071, 0.0])

# ---------------- numpy value noise (leg4 stone family: freq 0.09, 4 octaves) ---
def _hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144665) & 0x7fffffff
    h = (h ^ (h >> 13)) * 1274126177 & 0x7fffffff
    return ((h ^ (h >> 16)) % 100000) / 50000.0 - 1.0   # [-1, 1]

def _vnoise(p, seed):
    ip = np.floor(p).astype(np.int64); fp = p - ip
    t = fp * fp * (3 - 2 * fp)
    acc = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                v = _hash3(ip[:, 0] + dx, ip[:, 1] + dy, ip[:, 2] + dz, seed)
                w = (t[:, 0] if dx else 1 - t[:, 0]) * \
                    (t[:, 1] if dy else 1 - t[:, 1]) * \
                    (t[:, 2] if dz else 1 - t[:, 2])
                acc += v * w
    return acc

def noise4(p, seed):
    return (_vnoise(p * NF, seed) + 0.5 * _vnoise(p * NF * 2.3, seed + 7)
            + 0.28 * _vnoise(p * NF * 5.1, seed + 13) + 0.16 * _vnoise(p * NF * 9.7, seed + 29))

def smooth01(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)

# ---------------- mesh helpers ----------------
def load_dense(path, its=4):
    """Uniform 4:1 subdivision keeps the mesh watertight (subdivide_to_size makes
    T-junctions and breaks it)."""
    m = trimesh.load(path, process=True)
    assert m.is_watertight, path
    for _ in range(its):
        m = m.subdivide()
    assert m.is_volume, path
    return m

def displaced(m, fn):
    n = m.vertex_normals
    d = fn(m.vertices, n)
    return trimesh.Trimesh(m.vertices + n * d[:, None], m.faces, process=False)

def box(center, extents, rot=None):
    T = np.eye(4)
    if rot is not None: T[:3, :3] = rot
    T[:3, 3] = center
    return creation.box(extents=extents, transform=T)

def rot_z_to(axis):
    """Rotation taking +Z to `axis`."""
    z = np.array([0.0, 0.0, 1.0]); a = axis / np.linalg.norm(axis)
    v = np.cross(z, a); c = z @ a; s = np.linalg.norm(v)
    if s < 1e-8: return np.eye(3) * (1 if c > 0 else -1)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s**2)

def diff(a, cutters):
    out = a
    for c in cutters:
        out = boolean.difference([out, c], engine="manifold")
    return out

import manifold3d as m3d

def clean_export(m, path):
    """Re-canonicalize through manifold3d + simplify(10um): collapses the razor
    features whose distinct vertices share a float32 position (those fuse on STL
    reload and break manifoldness). Returns the exported trimesh."""
    mesh = m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                    tri_verts=np.asarray(m.faces, np.uint32))
    man = m3d.Manifold(mesh)
    man = man.simplify(0.01)
    mm3 = man.to_mesh()
    mm = trimesh.Trimesh(np.asarray(mm3.vert_properties[:, :3], np.float64),
                         np.asarray(mm3.tri_verts), process=False)
    # deterministic +/-2um per-vertex jitter: distinct vertices that share a float32
    # position (surface pinch points at the seam) stay distinct on STL reload.
    idx = np.arange(len(mm.vertices), dtype=np.uint64)
    j = np.stack([(idx * k % 9973) / 9973.0 - 0.5
                  for k in (2654435761, 40503, 2246822519)], axis=1) * 0.004
    mm = trimesh.Trimesh(mm.vertices + j, mm.faces, process=False)
    mm.export(path)
    chk = trimesh.load(path, process=False)
    chk.merge_vertices(merge_tex=True, merge_norm=True)
    print(f"    export {path.split('/')[-1]}: wt={mm.is_watertight} "
          f"roundtrip_volume={chk.is_volume} faces={len(mm.faces)}")
    return mm

# ---------------- PRIMARY gloves ----------------
def cavity_prim(ax, band, seed):
    def fn(P, N):
        s = (P - ROOT) @ ax
        b = smooth01(band[0], band[0] + 0.8, s) * (1 - smooth01(band[1] - 0.8, band[1], s))
        return FIT - (FIT + DETENT) * b
    return fn

def outer_prim(ax, seed, prong_mesh):
    """REAL-sculpt prong graft (operator puppet principle): the outer surface
    follows the toy 4-B prong surface (registered/scaled to this finger) wherever
    it satisfies the functional envelope; a floor guarantees min wall / tip pad /
    grip-face profile. Fallback (no prong above the ray) = low-amp matched crag."""
    pp, _ = trimesh.sample.sample_surface(prong_mesh, 250000, seed=seed)
    from scipy.spatial import cKDTree
    kd = cKDTree(pp)
    def fn(P, N):
        s = (P - ROOT) @ ax
        gw = np.clip(N @ D_GRIP_PRIM, 0, None)
        t = smooth01(40.0, 44.5, s) * np.clip((N @ ax) * 1.6, 0, 1)
        pf = smooth01(8.0, 14.0, s)
        # functional floor (min wall, grip-face profile, walking tip pad, collar)
        Wf = (2.0 * (1 - gw) + 1.8 * gw)
        Wf = Wf * (1 - t) + 3.5 * t
        floor = (1.2 + (Wf - 1.2) * pf) * (1 - t) + 3.5 * t
        # occupancy ray-march along the vertex normal against the REAL prong surface
        ts = np.arange(0.4, 12.1, 0.33)
        Q = P[:, None, :] + N[:, None, :] * ts[None, :, None]
        d, _ = kd.query(Q.reshape(-1, 3), workers=-1)
        occ = (d.reshape(len(P), -1) < 0.45)
        has = occ.any(axis=1)
        last = occ.shape[1] - 1 - np.argmax(occ[:, ::-1], axis=1)   # last occupied step
        prong = np.where(has, ts[last], 0.0)
        # caps: keep grip faces low-profile so the grip still closes — any face
        # within ~75deg of the grip direction is capped (glancing faces too)
        cap = 10.0 - 7.6 * smooth01(0.12, 0.40, gw)
        prong = np.minimum(prong, cap)
        # fallback: subtle matched crag where the prong doesn't reach
        fb = floor + (0.9 * (1 - gw) + 0.4 * gw) * (1 + noise4(P, seed)) * 0.8
        d_out = np.where(has & (prong > floor), prong, np.maximum(fb, floor))
        fn.governed = float((has & (prong > floor)).sum()) / len(P) * 100
        return np.maximum(d_out, floor)
    return fn

def build_prim(tag, f_self, f_other, ax, seed, keep_pos_z):
    blade = load_dense(CD + f"/{f_self}")
    other = load_dense(CD + f"/{f_other}", its=2)
    prong = trimesh.load(CD + f"/_prong_{tag}.stl", process=True)
    ofn = outer_prim(ax, seed, prong)
    outer = displaced(blade, ofn)
    print(f"  prong-governed outer fraction {tag}: {ofn.governed:.1f}%")
    cav = displaced(blade, cavity_prim(ax, (38.0, 41.0), seed))   # detent in the full-wrap distal zone
    oth = displaced(other, lambda P, N: np.full(len(P), 0.50))
    mouth = box(ROOT + ax * (8.0 - 60.0), (120, 120, 120), rot_z_to(ax))  # s=8: clear of the palm root fillet
    zc = box((390, 14, SEAM - 100 if keep_pos_z else -SEAM + 100), (240, 240, 200))
    cover = diff(outer, [mouth, zc, oth, cav])
    # keep only the main component (crumbs can appear at the carved seam);
    # do NOT re-process/merge: manifold3d output is already manifold and a
    # tolerance merge can glue the thin seam into non-manifold edges.
    parts = cover.split(only_watertight=False)
    cover = max(parts, key=lambda p: p.volume)
    cover = clean_export(cover, CD + f"/prim_cover_{tag}.stl")
    print(f"prim_cover_{tag}: faces={len(cover.faces)} wt={cover.is_watertight} "
          f"vol={cover.volume:.0f}mm3 parts_dropped={len(parts)-1}")
    return cover

pA = build_prim("A", "_finger_primA.stl", "_finger_primB.stl", AX_A, 101, True)
pB = build_prim("B", "_finger_primB.stl", "_finger_primA.stl", AX_B, 202, False)

# ---------------- THUMB glove (canonical frame) ----------------
pose = json.load(open(CD + "/_thumb_pose.json"))
M_open = np.array(pose["M_open"]); M_closed = np.array(pose["M_closed"])
d_grip_th = M_closed[:3, :3].T @ np.array([0.7071, 0.7071, 0.0])
print("thumb grip dir (canonical):", np.round(d_grip_th, 3))

MOUTH_T = 15.0
BAND_T = (17.0, 20.0)

def cavity_th(P, N):
    z = P[:, 2]
    b = smooth01(BAND_T[0], BAND_T[0] + 0.8, z) * (1 - smooth01(BAND_T[1] - 0.8, BAND_T[1], z))
    return FIT - (FIT + DETENT) * b

def outer_th(P, N):
    z = P[:, 2]
    gw = np.clip(N @ d_grip_th, 0, None)
    t = smooth01(41.0, 45.5, z) * np.clip(N[:, 2] * 1.6, 0, 1)
    W = 1.8 * (1 - gw) + 1.7 * gw
    W = W * (1 - t) + 3.5 * t
    amp = (1.8 * (1 - gw) + 0.45 * gw) * (1 - t) + 0.4 * t
    # proximal fade: snug low-crag collar so the CLOSED thumb clears the wrist/clevis
    pf = smooth01(15.0, 24.0, z)
    W = 1.1 + (W - 1.1) * pf
    amp = 0.35 + (amp - 0.35) * pf
    d = W + amp * noise4(P, 303)
    floor = (0.9 + 0.3 * pf) * (1 - t) + 3.5 * t
    return np.maximum(d, floor)

bladeT = load_dense(CD + "/_thumb_blade_canonical.stl")
outerT = displaced(bladeT, outer_th)
cavT = displaced(bladeT, cavity_th)
mouthT = box((0, 0, MOUTH_T - 60), (100, 100, 120))
coverT = diff(outerT, [mouthT, cavT])
parts = coverT.split(only_watertight=False)
coverT = max(parts, key=lambda p: p.volume)
coverT = clean_export(coverT, CD + "/_thumb_cover_canonical.stl")
print(f"thumb cover: faces={len(coverT.faces)} wt={coverT.is_watertight} "
      f"vol={coverT.volume:.0f}mm3")

to = coverT.copy(); to.apply_transform(M_open); to.export(CD + "/thumb_cover.stl")
tc = coverT.copy(); tc.apply_transform(M_closed); tc.export(CD + "/_thumb_cover_closed.stl")

# ---- build-time SECTION meshes for the cross-section render panel ----
mv = np.cross(AX_A, [0, 0, 1.0]); mv /= np.linalg.norm(mv)
sect = boolean.difference([pA, box(ROOT + mv * 100, (240, 240, 200), rot_z_to(mv))],
                          engine="manifold")
sect.export(CD + "/_sect_prim.stl")
sectT = boolean.difference([to, box((370, -35, 100), (240, 240, 200))], engine="manifold")
sectT.export(CD + "/_sect_thumb.stl")
print("sections:", len(sect.faces), len(sectT.faces))
print("DONE gloves v2 (trimesh/manifold)")
