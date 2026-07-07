"""ROCKY-5 leg CHASSIS — kinematic + interface single-source-of-truth.

PHASE 1 (operator directive): design Rocky MECHANISM-FIRST. This module is the
pure-Python skeleton of ONE functional 3-DOF + grip leg: the joint stations, the
joint limits, the EduLite / grip interface dims, and the forward kinematics. It
imports NOTHING from build123d, so the host-venv render (matplotlib) and the CAD
part builders (build123d) both read the SAME numbers — the frame the sculpt shell
scales over in Phase 2.

Leg frame (matches params forward_axis "+X"): X = radial reach (outboard), Z up,
Y = the pitch axis. At the NEUTRAL pose (all joints 0) the whole leg lies along
+X in the X-Z plane. The three drive axes:

  * coxa_yaw     — VERTICAL (Z) at the hip; rotates the whole leg in yaw.
  * femur_pitch  — HORIZONTAL (Y) at P1 (coxa end); lifts/lowers the leg.
  * tibia_pitch  — HORIZONTAL (Y) at P2 (knee);     bends the tibia.
  * tibia_roll   — LONG-AXIS (X) inline in the tibia (D-039); rolls the whole
                   shank+hand about the leg's long axis (wrist roll).
  * grip         — micro-servo at the tibia tip; drives the 3-finger hand.

coxa_yaw ⟂ femur_pitch (Z ⟂ Y) — the perpendicular hip cluster the spec calls for;
the COXA bracket sets that perpendicular offset (COXA_MM between the two axes).
"""
from __future__ import annotations

import math

from common.cad_lib import standards as S   # pure-python constants (no build123d)

# --- Segment lengths (rocky/design/params.yaml -> dimensions) --------------
# Distances BETWEEN drive axes (not sculpt outlines): they set where the servos
# sit, then the printed links are sized by SERVO FIT around those stations.
COXA_MM = 60.0      # coxa_yaw axis  -> femur_pitch axis  (perpendicular offset)
FEMUR_MM = 73.0     # femur_pitch axis -> knee (tibia_pitch) axis  (thigh)
TIBIA_MM = 105.0    # knee axis        -> hand mount            (shank)

# --- Joint limits (params dof_template / manipulators), radians ------------
YAW_LIMIT = (-0.9, 0.9)          # coxa_yaw
FEMUR_PITCH_LIMIT = (-1.4, 1.0)  # femur_pitch
TIBIA_PITCH_LIMIT = (-0.3, 2.0)  # tibia_pitch
TIBIA_ROLL_LIMIT = (-1.5, 1.5)   # tibia_roll (wrist roll about the leg long axis, D-039)
GRIP_LIMIT = (0.0, 2.2)          # grip (open flat foot -> 3-jaw grasp)

# --- Feetech STS slim serial servo (standards.STS_* / components.SERVO_PITCH,
#     SERVO_YR) — the SLIM INLINE leg-joint actuator (D-041) ------------------
# Replaces the fat external Ø54 Robstride EduLite cups. Both leg servos share ONE
# body: 45.2 (L, lies ALONG the link) x 24.7 (W, the SLIM lateral dim) x 35 (H, the
# output-axis direction; horn on the +H face, offset SV_OUT_OFF toward the joint).
# STS3250 on the 10 pitch joints (weight-bearing), STS3215 on the 10 yaw/roll joints.
SV_L = S.STS_BODY_L_MM        # 45.2 body length (along the link)
SV_W = S.STS_BODY_W_MM        # 24.7 SLIM width (lateral) — the slimming point
SV_H = S.STS_BODY_H_MM        # 35   height = output-axis direction
SV_OUT_OFF = S.STS_OUTPUT_OFF_MM  # 13.5 spline offset from body centre along L
HORN_D = S.STS_HORN_DIA_MM        # 24 output-horn disc Ø
HORN_PROTRUDE = S.STS_HORN_PROTRUDE_MM  # 6
FLANGE_DISC = 52.0            # hand-mount flange pad OD (tibia tip <-> grip_palm; UNCHANGED)

# --- Grip micro-servo (components.GRIP_SERVO) ------------------------------
GRIP_BOX = (22.8, 12.2, 28.5)

# --- Structural sizing (driven by the SLIM inline servo, not the sculpt) ----
WALL = 3.0                     # generic frame wall
HOUS_WALL = 3.0                # wall wrapping the inline servo housing
# The driven segment couples to the OUTPUT HORN (Ø24) with a slim cap disc; the far
# end of the output shaft is carried by a 625ZZ IDLER in the host housing (the real
# double-support servo bracket — "a bearing on the far side of the pitch axis").
COUPLE_D = HORN_D + 2 * WALL              # child horn-coupling disc Ø (~30)
COUPLE_BORE = HORN_D + 2 * S.FIT_SLIDE_MM  # caps the Ø24 horn (slide)
IDLER_OD = S.BEARING_625ZZ_OD_MM          # Ø16 far-side idler on the output shaft
IDLER_W = S.BEARING_625ZZ_W_MM
# Slim link struts (gyroid tubes) — NO more Ø54 cups, so the strut is the silhouette.
BEAM_W = 22.0                 # link beam cross-section (Y) — SLIM
BEAM_H = 26.0                 # link beam cross-section (Z)
ROOT_DISC_D = COUPLE_D        # link-root coupling disc Ø (caps the horn)

# --- Tibia-roll inline actuator (D-039, now STS3215 D-041) -----------------
# The 4th servo (STS3215) sits INLINE in the tibia_bracket: its output horn is on the
# leg long axis (+X) at the roll station PR and drives the shank+hand, which ROLLS
# about X; its 24.7-slim body lies proximal (-X) of PR. With the fat Ø54 knee cups
# GONE (D-041), nothing blocks the coaxial body, but PR/TIP are kept UNCHANGED so leg
# reach and the description kinematics are unaffected. The shank distal of PR is a
# short ~26 mm wrist that simply rolls the hand.
ROLL_OUT_OFF = 79.0          # knee axis -> roll output (shank-root) station  (=> PR at 212)

# --- Thin-wall gyroid/lattice struts (D-040) -------------------------------
# The Phase-2 cosmetic sculpt shell carries the volume, so the STRUT links are
# only a stiff core: a thin closed outer wall around a rib lattice (slicer prints
# gyroid infill 30-40% inside). A CLOSED thin-wall tube is far stiffer in TORSION
# than the old open I-beam — important now the roll DOF twists the shank.
STRUT_WALL = 2.7             # thin outer wall (>= 2.4 mm structural min)
STRUT_RIB_T = 2.7            # internal transverse rib thickness
STRUT_RIB_PITCH = 16.0       # rib spacing along the beam
STRUT_WIRE_D = 9.0           # internal wiring channel Ø threaded through the ribs

# Shell budget: Phase-2 cosmetic sculpt scales OVER this frame; leave room.
SHELL_GAP_MM = 5.0

# --- Neutral-pose joint stations in the leg frame --------------------------
YAW_FLOOR_Z = 40.0                                  # coxa_yaw mount-face height
HIP = (0.0, 0.0, 0.0)                               # yaw axis = vertical line x=y=0
P1 = (COXA_MM, 0.0, 0.0)                            # femur_pitch axis (about +Y)
P2 = (COXA_MM + FEMUR_MM, 0.0, 0.0)                 # knee / tibia_pitch axis (+Y)
PR = (COXA_MM + FEMUR_MM + ROLL_OUT_OFF, 0.0, 0.0)  # tibia_roll axis station (on the leg axis)
TIP = (COXA_MM + FEMUR_MM + TIBIA_MM, 0.0, 0.0)     # hand mount
ROLL_FRAC = ROLL_OUT_OFF / TIBIA_MM                 # roll station as a fraction knee->tip


# --- Small 3x3 / point maths (no numpy — importable anywhere) --------------
def _rot_y(a: float):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _rot_z(a: float):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _mv(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _about(m, pt, v):
    """Apply rotation m about point pt to point v."""
    d = tuple(v[i] - pt[i] for i in range(3))
    r = _mv(m, d)
    return tuple(r[i] + pt[i] for i in range(3))


# --- STS inline-servo body placement (pure python; parts size housings to this) --
# Maps a point in the feetech.py CANONICAL frame (output axis +Z at origin, body on
# -Z, length along X) to the WORLD, for each output-face normal — matching
# leg_mounts._FACE_ROT / sts_face_cut exactly. Parts wrap a housing box around the
# returned AABB so the slim servo is always enclosed with >= wall material.
_SERVO_MAP = {
    "+Z": lambda x, y, z: (x, y, z),
    "-Z": lambda x, y, z: (x, -y, -z),
    "+Y": lambda x, y, z: (x, z, -y),
    "-Y": lambda x, y, z: (x, -z, y),
    "+X": lambda x, y, z: (z, y, -x),
    "-X": lambda x, y, z: (-z, y, x),
}


def sts_body_aabb(joint_pt, normal, pad=0.0):
    """World-frame AABB (xmin,xmax,ymin,ymax,zmin,zmax) of the STS body at a joint
    whose output axis passes through `joint_pt` along `normal`."""
    m = _SERVO_MAP[normal]
    bx0, bx1 = -SV_OUT_OFF - SV_L / 2, -SV_OUT_OFF + SV_L / 2
    corners = [m(cx, cy, cz)
               for cx in (bx0, bx1)
               for cy in (-SV_W / 2, SV_W / 2)
               for cz in (-SV_H, 0.0)]
    xs, ys, zs = ([c[i] for c in corners] for i in range(3))
    jx, jy, jz = joint_pt
    return (jx + min(xs) - pad, jx + max(xs) + pad,
            jy + min(ys) - pad, jy + max(ys) + pad,
            jz + min(zs) - pad, jz + max(zs) + pad)


def joint_housing_aabb(joint_pt, normal):
    """Body AABB unioned with the ON-AXIS output-horn clearance envelope in the two
    axes perpendicular to `normal` — so a host housing wrapped around this always
    encloses the Ø(horn) output bore too (the horn sits on the axis, which for the
    offset body can reach past the body's own footprint)."""
    x0, x1, y0, y1, z0, z1 = sts_body_aabb(joint_pt, normal)
    r = HORN_D / 2 + S.FIT_LOOSE_MM
    jx, jy, jz = joint_pt
    if normal in ("+Z", "-Z"):
        x0, x1 = min(x0, jx - r), max(x1, jx + r)
        y0, y1 = min(y0, jy - r), max(y1, jy + r)
    elif normal in ("+Y", "-Y"):
        x0, x1 = min(x0, jx - r), max(x1, jx + r)
        z0, z1 = min(z0, jz - r), max(z1, jz + r)
    else:  # +X / -X
        y0, y1 = min(y0, jy - r), max(y1, jy + r)
        z0, z1 = min(z0, jz - r), max(z1, jz + r)
    return (x0, x1, y0, y1, z0, z1)


def fk(q1: float, q2: float, q3: float, q4: float = 0.0):
    """Forward kinematics -> dict of the posed axis stations + hand tip.

    q1 = coxa_yaw (about +Z at HIP), q2 = femur_pitch, q3 = tibia_pitch,
    q4 = tibia_roll (about the tibia long axis, D-039). The pitch joints act in the
    leg's BODY frame (their axes are Y only at yaw=0), so the chain is built
    pitch-first then yawed as a whole — the physically correct order (the pitch
    axes ride along with the yaw). Returns world points 'hip','p1','knee','roll',
    'tip'. Sign: +pitch swings the outboard segment about +Y, which with the leg
    reaching +X drops the tip (-Z).

    tibia_roll spins the shank about its own long axis; the hand tip lies ON that
    axis, so q4 does NOT move 'tip' (it re-orients the off-axis hand — see the
    assembly render). q4 is accepted so callers share one signature.
    """
    Ry2, Ry3, Rz = _rot_y(q2), _rot_y(q3), _rot_z(q1)
    # --- pitch chain in the un-yawed body frame ---
    knee_b = _about(Ry2, P1, P2)
    tip_b = _about(Ry3, knee_b, _about(Ry2, P1, TIP))
    roll_b = _about(Ry3, knee_b, _about(Ry2, P1, PR))
    # --- yaw the whole leg about Z at the hip ---
    p1 = _about(Rz, HIP, P1)
    knee = _about(Rz, HIP, knee_b)
    roll = _about(Rz, HIP, roll_b)
    tip = _about(Rz, HIP, tip_b)
    return {"hip": HIP, "p1": p1, "knee": knee, "roll": roll, "tip": tip}


def reach(q1: float, q2: float, q3: float, q4: float = 0.0):
    """(radius, z) of the hand tip in the leg frame for a joint tuple (roll is a
    long-axis spin and does not move the on-axis tip)."""
    t = fk(q1, q2, q3, q4)["tip"]
    return math.hypot(t[0], t[1]), t[2]
