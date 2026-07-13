"""Export the 3 individual grip fingers (2 primaries + thumb) PLACED in the
chassis leg frame at leg2's tip, exactly as scripts/build_leg_chassis.posed_servos_hand
places the hand (neutral pose, Lshank = identity). Open + closed thumb poses."""
import os
from build123d import Pos, Rotation, export_stl
from rocky.cad.parts import grip_finger as GF
from rocky.cad.parts import leg_geom as G

SP = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"
OUT = SP + "/leg3_finger_covers"
os.makedirs(OUT, exist_ok=True)

# EXACT chassis-frame placement (neutral pose): Lshank = identity, so
#   world = Pos(TIP[0]+1,0,0) * Rotation(0,90,0) * Rotation(0,0,-90) * <hand local>
W = Pos(G.TIP[0] + 1.0, 0, 0) * Rotation(0, 90, 0) * Rotation(0, 0, -90)

a, b = GF.azimuths()            # +12, -12 splay
primA = W * GF._primary_placed(a)
primB = W * GF._primary_placed(b)
thumb_open = W * GF.thumb_placed(0.0)     # grip OPEN  (thumb raised)
thumb_closed = W * GF.thumb_placed(2.2)   # grip CLOSED (thumb pinch)

export_stl(primA, OUT + "/_finger_primA.stl", tolerance=0.05, angular_tolerance=0.3)
export_stl(primB, OUT + "/_finger_primB.stl", tolerance=0.05, angular_tolerance=0.3)
export_stl(thumb_open, OUT + "/_finger_thumb_open.stl", tolerance=0.05, angular_tolerance=0.3)
export_stl(thumb_closed, OUT + "/_finger_thumb_closed.stl", tolerance=0.05, angular_tolerance=0.3)

# Thumb in its CANONICAL local frame (pivot at origin) so the cover built on it is
# rigid; Blender poses it with the two matrices below.
export_stl(GF._thumb_canonical(), OUT + "/_thumb_canonical.stl",
           tolerance=0.05, angular_tolerance=0.3)
# Only the VISIBLE thumb BLADE (hub + crank tail are hidden inside the wrist) — the
# cosmetic cover wraps this. Same canonical frame as the pose matrices below.
from build123d import Pos as _Pos
_blade = _Pos(0, 0, GF.HUB_R * 0.2) * GF._blade(GF.THUMB_LEN, GF.ROOT_R, GF.TIP_R)
export_stl(_blade, OUT + "/_thumb_blade_canonical.stl",
           tolerance=0.05, angular_tolerance=0.3)

# Pose matrices: world = W @ Trans(PIV) @ Ry(angle) applied to canonical thumb.
import numpy as np, json, math
Wr = np.array([[0, 0, 1.0], [-1, 0, 0], [0, -1, 0]]); Wt = np.array([329.0, 0, 0])
W4 = np.eye(4); W4[:3, :3] = Wr; W4[:3, 3] = Wt
def trans4(p):
    M = np.eye(4); M[:3, 3] = p; return M
def ry4(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    M = np.eye(4); M[0, 0] = c; M[0, 2] = s; M[2, 0] = -s; M[2, 2] = c; return M
PIV = list(GF.THUMB_PIV)
def ang(gr):  # thumb angle (deg) at a grip value, mirrors thumb_placed
    a = GF.THUMB_OPEN_A + (gr / GF.GRIP_CLOSED_RAD) * (GF.THUMB_CLOSED_A - GF.THUMB_OPEN_A)
    return math.degrees(a)
M_open = W4 @ trans4(PIV) @ ry4(ang(0.0))
M_closed = W4 @ trans4(PIV) @ ry4(ang(2.2))
json.dump({"M_open": M_open.tolist(), "M_closed": M_closed.tolist(),
           "piv_local": PIV, "open_deg": ang(0.0), "closed_deg": ang(2.2)},
          open(OUT + "/_thumb_pose.json", "w"), indent=1)
print("thumb open_deg=%.2f closed_deg=%.2f" % (ang(0.0), ang(2.2)))

# report placed tip/bbox for each
import numpy as np, trimesh
for nm in ["_finger_primA", "_finger_primB", "_finger_thumb_open", "_finger_thumb_closed"]:
    m = trimesh.load(OUT + "/" + nm + ".stl", process=False)
    lo, hi = m.bounds
    print(f"{nm:24s} x[{lo[0]:6.1f},{hi[0]:6.1f}] y[{lo[1]:6.1f},{hi[1]:6.1f}] z[{lo[2]:6.1f},{hi[2]:6.1f}]")
print("TIP world x =", G.TIP[0] + 1.0)
