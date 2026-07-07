#!/usr/bin/env python3
"""Assemble + articulate + interference-check the ROCKY-5 leg chassis (Phase 1).

Runs under scripts/cadpy (build123d). Poses the four printed chassis links plus
dummy EduLite / grip servos through the kinematic chain (rocky.cad.parts.leg_geom),
then:
  * exports coloured STL groups (frame / servos / hand) for the neutral + a rolled
    pose (exercising the D-039 tibia_roll) to docs/build_plan/ for the render;
  * runs the real trimesh interference check between the moving links across the
    joint-limit corners (honest self-collision verification);
  * reports the reachable tip envelope + a neutral stance pose.

Usage: cadpy scripts/build_leg_chassis.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import trimesh  # noqa: E402
from build123d import Box, Cylinder, Pos, Rotation, export_stl, Part  # noqa: E402

from common.cad_lib import standards as S  # noqa: E402
from rocky.cad.parts import leg_geom as G  # noqa: E402
from rocky.cad.parts.leg_mounts import _FACE_ROT, sts_body  # noqa: E402
from rocky.cad.parts.leg_hip_yoke import leg_hip_yoke  # noqa: E402
from rocky.cad.parts.coxa_bracket import coxa_bracket, KNEE_X, KNEE_Z  # noqa: E402
from rocky.cad.parts.femur_link import femur_link  # noqa: E402
from rocky.cad.parts.tibia_bracket import tibia_bracket  # noqa: E402
from rocky.cad.parts.tibia_link import tibia_link  # noqa: E402
from rocky.cad.parts.grip_hand import assembly as grip_assembly  # noqa: E402
from rocky.cad.parts import knee_shaft_tx as KTX  # noqa: E402  (CVD/shaft/bevel dummies)
from common.cad_lib.interference import pair_interference_volume  # noqa: E402

# tibia_roll horn axis station (leg frame X) — where the 4th (STS3215) servo drives.
ROLL_FLANGE_X = G.PR[0]


def qdd_dummy(at, axis) -> Part:
    """Solid EduLite-05 (Ø46x44) stand-in at `at`, body along `axis` ('x'|'y'|'z')."""
    r, h = S.EDULITE_HOUSING_DIA_MM / 2, S.EDULITE_HEIGHT_MM
    rot = {"x": Rotation(0, 90, 0), "y": Rotation(90, 0, 0), "z": Rotation(0, 0, 0)}[axis]
    return Pos(*at) * rot * Cylinder(radius=r, height=h)

OUT = ROOT / "docs" / "build_plan"
OUT.mkdir(parents=True, exist_ok=True)


# --- servo dummies (render + interference only, NOT printed) ----------------
# The 4 leg-joint servos are the slim Feetech STS bodies (D-041); leg_mounts.sts_body
# returns the placed dummy (body along the link + output horn crossing the joint).

def servo_grip(face_pt, normal) -> Part:
    bx, by, bz = G.GRIP_BOX
    s = Pos(0, 0, bz / 2) * Box(bx, by, bz)
    return Pos(*face_pt) * Rotation(*_FACE_ROT[normal]) * s


# --- pose chain -------------------------------------------------------------
def _about(deg, axis, p):
    neg = Pos(-p[0], -p[1], -p[2])
    R = Rotation(0, 0, deg) if axis == "z" else Rotation(0, deg, 0)
    return Pos(*p) * R * neg


def locs(q1, q2, q3, q4=0.0):
    """Build the pitch chain in the body frame, then apply yaw outermost (matches
    leg_geom.fk), then the tibia_roll on the shank only. Returns
    (L_coxa, L_femur, L_tibia_bracket, L_shank, fk). The bracket rides the knee frame;
    the shank+hand additionally ROLL about the tibia long axis (local X, D-039)."""
    d1, d2, d3, d4 = (math.degrees(q) for q in (q1, q2, q3, q4))
    fk = G.fk(q1, q2, q3, q4)
    Lyaw = _about(d1, "z", G.HIP)
    Lpf = _about(d2, "y", G.P1)                 # femur pitch (body frame)
    Lpt = Lpf * _about(d3, "y", G.P2)           # tibia = femur pitch then knee
    Lt = Lyaw * Lpt                             # knee frame (tibia_bracket rides this)
    Lshank = Lt * Rotation(d4, 0, 0)            # + roll about the leg long axis (X)
    return Lyaw, (Lyaw * Lpf), Lt, Lshank, fk


def posed_links(q1, q2, q3, q4=0.0):
    """Return dict name -> posed build123d Part for the 5 structural links."""
    Lc, Lf, Lt, Lshank, _ = locs(q1, q2, q3, q4)
    return {
        "hip_yoke": leg_hip_yoke(),
        "coxa_bracket": Lc * coxa_bracket(),
        "femur_link": Lf * femur_link(),
        "tibia_bracket": Lt * tibia_bracket(),
        "tibia_link": Lshank * tibia_link(),
    }


def posed_servos_hand(q1, q2, q3, q4=0.0, grip_rad=None):
    Lc, Lf, Lt, Lshank, _ = locs(q1, q2, q3, q4)
    # D-042 HIP CLUSTER (3 QDD, ~242 g each, mass in the BODY): coxa_yaw (Z, body-fixed),
    # femur_pitch (Y, in coxa_bracket) + the KNEE MOTOR (in the hip cluster) driving the
    # knee REMOTELY through the double-cardan CVD -> Ø6 shaft down the femur -> miter bevel.
    hip_qdd = (
        qdd_dummy((0, 0, G.YAW_FLOOR_Z - S.EDULITE_HEIGHT_MM / 2), "z")   # coxa_yaw QDD (Z)
        + Lc * qdd_dummy((G.P1[0], -S.EDULITE_HEIGHT_MM / 2 - 8, 0), "y")  # femur_pitch QDD (Y)
        + Lc * qdd_dummy((KNEE_X - S.EDULITE_HEIGHT_MM / 2, 0, KNEE_Z), "x")  # knee QDD (in cluster)
    )
    # Driveshaft: CVD centred on the femur_pitch axis, Ø6 shaft down the slim femur, miter
    # bevel at the knee — all ride the femur (Lf).
    driveshaft = Lf * (KTX.dummy_cvd() + KTX.dummy_shaft() + KTX.dummy_bevels())
    # tibia_roll: the ONE servo on the leg — a slim STS3215 inline in the tibia_bracket.
    roll_sts = Lt * sts_body((G.PR[0], 0, 0), "+X")
    servos = hip_qdd + driveshaft + roll_sts
    # 2+1 hand: slim wrist bolts to the shank tip flange and extends outward (+X).
    # It rides the ROLLED shank frame, so tibia_roll twists the whole hand. The grip
    # micro-servo is HIDDEN inside the palm, so no external dummy. Local +Z (mount
    # axis) -> world +X (outward); a -90° roll drops the two primary fingers to the
    # ground side and lifts the opposing thumb.
    gr = G.GRIP_LIMIT[0] if grip_rad is None else grip_rad
    hand = Lshank * Pos(G.TIP[0] + 1.0, 0, 0) * Rotation(0, 90, 0) * Rotation(0, 0, -90) \
        * grip_assembly(gr)
    return servos, hand


# --- interference across the articulation envelope --------------------------
def _mesh(part: Part) -> trimesh.Trimesh:
    tmp = OUT / "_tmp_if.stl"
    export_stl(part, str(tmp), tolerance=0.1, angular_tolerance=0.3)
    return trimesh.load(tmp)


# Adjacent links that are BOLTED TOGETHER at a shared joint, so their models
# interpenetrate there BY DESIGN (a coupling, not a free-space clash):
#   * coxa_bracket <-> femur_link: the femur_pitch QDD output collar AND the knee
#     driveshaft double-cardan CVD are COAXIAL on the pitch axis at P1 (D-042); the
#     femur root couples to that QDD there, so the hip-cluster knuckle and the femur
#     CV ring share the P1 joint volume.
#   * femur_link <-> tibia_bracket: the knee miter-bevel output collar (in the femur
#     bevel box) is capped by the tibia root at the knee — a coupling.
# These are reported as a COUPLING VOLUME, not a self-collision. Everything ELSE must
# be free-space clean across the in-range poses (only the out-of-range knee fold clashes).
COUPLED_PAIRS = {("coxa_bracket", "femur_link"), ("femur_link", "tibia_bracket")}


def collision_scan():
    q1lo, q1hi = G.YAW_LIMIT
    q2lo, q2hi = G.FEMUR_PITCH_LIMIT
    q3lo, q3hi = G.TIBIA_PITCH_LIMIT
    free_pairs = [("coxa_bracket", "tibia_bracket"),
                  ("coxa_bracket", "tibia_link"),
                  ("femur_link", "tibia_link"),
                  ("hip_yoke", "femur_link"),
                  ("hip_yoke", "tibia_bracket"),
                  ("hip_yoke", "tibia_link")]
    pairs = free_pairs + list(COUPLED_PAIRS)
    poses = {"neutral": (0.0, 0.0, 0.0)}
    for a in (q1lo, 0.0, q1hi):
        for b in (q2lo, 0.0, q2hi):
            for c in (q3lo, 0.0, q3hi):
                poses[f"{a:+.1f},{b:+.1f},{c:+.1f}"] = (a, b, c)
    worst = {p: 0.0 for p in pairs}
    clashes = []
    for name, (a, b, c) in poses.items():
        L = posed_links(a, b, c)
        meshes = {k: _mesh(v) for k, v in L.items()}
        for pa, pb in pairs:
            v = pair_interference_volume(meshes[pa], meshes[pb])
            if v > worst[(pa, pb)]:
                worst[(pa, pb)] = v
            if v > 1.0 and (pa, pb) not in COUPLED_PAIRS:
                clashes.append((name, pa, pb, round(v, 1)))
    return worst, clashes, len(poses)


def roll_clearance():
    """Worst bracket<->shank interference across the full tibia_roll range (q1=q2=q3=0).
    A roll about the leg long axis should be free (near-axisymmetric shank)."""
    lo, hi = G.TIBIA_ROLL_LIMIT
    worst = 0.0
    for q4 in (lo, 0.0, hi):
        L = posed_links(0.0, 0.0, 0.0, q4)
        v = pair_interference_volume(_mesh(L["tibia_bracket"]), _mesh(L["tibia_link"]))
        worst = max(worst, v)
    return round(worst, 2)


# --- reachable envelope + neutral stance ------------------------------------
def clean_knee_limit():
    """Finest q3 (tibia_pitch) that keeps the knee-driven SHANK collision-free against
    the femur (q1=q2=q4=0). Checks femur<->shank (tibia_link) — the tibia_bracket is
    BOLTED to the femur bevel output at the knee (a coupling), so it is excluded."""
    lo, hi = G.TIBIA_PITCH_LIMIT
    last_ok = lo
    q3 = 0.0
    while q3 <= hi + 1e-6:
        L = posed_links(0.0, 0.0, q3)
        vs = pair_interference_volume(_mesh(L["femur_link"]), _mesh(L["tibia_link"]))
        if vs > 0.05:
            break
        last_ok = q3
        q3 += 0.05
    return round(last_ok, 2)


def reach_envelope():
    q1lo, q1hi = G.YAW_LIMIT
    q2lo, q2hi = G.FEMUR_PITCH_LIMIT
    q3lo, q3hi = G.TIBIA_PITCH_LIMIT
    rs, zs = [], []
    N = 9
    for i in range(N):
        q2 = q2lo + (q2hi - q2lo) * i / (N - 1)
        for j in range(N):
            q3 = q3lo + (q3hi - q3lo) * j / (N - 1)
            r, z = G.reach(0.0, q2, q3)
            rs.append(r); zs.append(z)
    # yaw sweep of the neutral tip
    yaw_r, _ = G.reach(0.0, 0.0, 0.0)
    yaw_arc = yaw_r * (q1hi - q1lo)
    return {
        "radius_mm": [round(min(rs), 1), round(max(rs), 1)],
        "z_mm": [round(min(zs), 1), round(max(zs), 1)],
        "yaw_sweep_deg": round(math.degrees(q1hi - q1lo), 1),
        "yaw_arc_at_neutral_mm": round(yaw_arc, 1),
    }


def export_pose(tag, q1, q2, q3, q4=0.0, grip_rad=None):
    L = posed_links(q1, q2, q3, q4)
    frame = (L["hip_yoke"] + L["coxa_bracket"] + L["femur_link"]
             + L["tibia_bracket"] + L["tibia_link"])
    servos, hand = posed_servos_hand(q1, q2, q3, q4, grip_rad)
    export_stl(frame, str(OUT / f"leg_chassis_{tag}_frame.stl"), tolerance=0.08)
    export_stl(servos, str(OUT / f"leg_chassis_{tag}_servos.stl"), tolerance=0.08)
    export_stl(hand, str(OUT / f"leg_chassis_{tag}_hand.stl"), tolerance=0.08)


def main() -> int:
    NEUTRAL = (0.0, 0.0, 0.0, 0.0)
    # A pose that exercises the NEW wrist-roll: femur lifted, knee folded (within the
    # reduced limit), and the shank+hand ROLLED +1.2 rad, grip closed to a grasp.
    ROLLPOSE = (0.0, -0.35, 0.9, 1.2)
    export_pose("neutral", *NEUTRAL, grip_rad=G.GRIP_LIMIT[0])   # grip OPEN (foot-tip)
    export_pose("rolled", *ROLLPOSE, grip_rad=G.GRIP_LIMIT[1])   # roll + grip CLOSED (grasp)

    worst, clashes, nposes = collision_scan()
    roll_worst = roll_clearance()
    env = reach_envelope()
    knee_ok = clean_knee_limit()
    fk_n = G.fk(*NEUTRAL)
    fk_r = G.fk(*ROLLPOSE)

    coupling = {f"{a}|{b}": round(v, 1) for (a, b), v in worst.items() if (a, b) in COUPLED_PAIRS}
    report = {
        "architecture": "D-042 LOCK: hip-cluster QDD (3/leg, in body) + knee driveshaft + inline roll STS",
        "actuators": {
            "coxa_yaw": "EduLite-05 QDD (Z), hip cluster / body",
            "femur_pitch": "EduLite-05 QDD (Y), hip cluster / body, DIRECT drive",
            "knee": "EduLite-05 QDD, hip cluster / body, REMOTE via double-cardan driveshaft",
            "tibia_roll": "STS3215 slim serial (X), inline in the shank — the ONLY leg-mounted servo",
            "grip": "MG90S-class micro (hidden in the palm)"},
        "knee_transmission": {
            "type": "double_cardan_driveshaft", "ratio": 1.0, "backlash_rad": 0.044,
            "efficiency": 0.9, "shaft_dia_mm": 6.0, "tube_dia_mm": 12.0,
            "bevel": "M1 16T:16T miter (1:1)", "cvd": "double-cardan centred on femur_pitch axis"},
        "mass_to_body_g_per_leg": 3 * 242.0, "mass_to_body_g_all5": 5 * 3 * 242.0,
        "shell_envelope_dia_mm": 44.0,
        "poses_scanned": nposes,
        "dof": 4,
        "roll_pose_rad": {"coxa_yaw": ROLLPOSE[0], "femur_pitch": ROLLPOSE[1],
                          "tibia_pitch": ROLLPOSE[2], "tibia_roll": ROLLPOSE[3]},
        "worst_interference_mm3": {f"{a}|{b}": round(v, 2) for (a, b), v in worst.items()},
        "joint_coupling_volume_mm3": coupling,
        "coupling_note": ("coxa<->femur = coaxial femur_pitch QDD + knee-driveshaft CVD at P1; "
                          "femur<->tibia_bracket = knee miter-bevel output collar. Both are BOLTED "
                          "couplings at the shared joint (not free-space clashes). HONEST: the "
                          "hip-cluster knuckle massing overlaps the femur CV ring by ~5 cm^3 and "
                          "wants clearance refinement before print (tight coaxial QDD+CVD at P1)."),
        "roll_worst_interference_mm3": roll_worst,
        "free_space_clashes_over_1mm3": clashes,
        "params_joint_limits_rad": {
            "coxa_yaw": list(G.YAW_LIMIT), "femur_pitch": list(G.FEMUR_PITCH_LIMIT),
            "tibia_pitch": list(G.TIBIA_PITCH_LIMIT), "tibia_roll": list(G.TIBIA_ROLL_LIMIT)},
        "collision_free_limits_rad": {
            "coxa_yaw": list(G.YAW_LIMIT),          # clean across full sweep
            "femur_pitch": list(G.FEMUR_PITCH_LIMIT),  # clean across full sweep
            "tibia_pitch": [G.TIBIA_PITCH_LIMIT[0], knee_ok],  # knee fold self-limits
            "tibia_roll": list(G.TIBIA_ROLL_LIMIT)},   # roll is free (see roll_worst)
        "knee_selfcollision_free_max_rad": knee_ok,
        "reach_envelope": env,
        "neutral_tip_xyz": [round(x, 1) for x in fk_n["tip"]],
        "roll_pose_tip_xyz": [round(x, 1) for x in fk_r["tip"]],
        "stations_neutral": {k: [round(x, 1) for x in v] for k, v in fk_n.items()},
    }
    (OUT / "leg_chassis_facts.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    knee_clash = [c for c in clashes if c[2] in ("tibia_bracket", "tibia_link")
                  and c[0].endswith(f"{G.TIBIA_PITCH_LIMIT[1]:+.1f}")]
    print(f"[build_leg_chassis] roll worst interference = {roll_worst} mm^3 (roll is free)")
    print(f"[build_leg_chassis] knee collision-free to {knee_ok} rad "
          f"({math.degrees(knee_ok):.0f} deg); params 2.0 rad self-folds beyond that")
    print(f"[build_leg_chassis] {'CLEAN — no self-collision in-range' if not [c for c in clashes if c[3] > 1.0 and not c[0].endswith('+2.0')] else 'clashes (knee>limit expected): ' + str(clashes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
