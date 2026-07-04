"""Build RobotModels from params.yaml (ROBOTS_SPEC.md §3, §4).

Masses are engineering estimates (servo 60 g + printed structure per link) that
sum below the design-target mass; they set inertias and the settle dynamics.
Real per-link CAD masses replace them as parts are authored. Geometry (link
lengths, joint spacing, limits, servo IDs) is law from params.yaml.
"""

from __future__ import annotations

import math

from common.params import load_params
from common.description_gen.model import Joint, Link, RobotModel, Shape

MM = 0.001


def _revolute(model, name, parent, child, xyz, axis, limit, servo, sid, rpy=(0, 0, 0)):
    lo, hi = limit
    model.add_joint(Joint(
        name=name, jtype="revolute", parent=parent, child=child,
        origin_xyz=xyz, origin_rpy=rpy, axis=axis, lower=lo, upper=hi,
        effort=servo["effort_clamp_nm"], velocity=servo["vel_clamp_rad_s"], servo_id=sid,
    ))


# --------------------------------------------------------------------------- #
# BDX-A (biped, 10 DOF)
# --------------------------------------------------------------------------- #
def build_bdx_a() -> RobotModel:
    p = load_params("bdx_a")
    d = p["dimensions"]
    servo = p["servo"]
    thigh = d["thigh_mm"] * MM
    shin = d["shin_mm"] * MM
    half_hip = d["hip_yaw_spacing_mm"] * MM / 2.0
    foot_l, foot_w = d["foot_length_mm"] * MM, d["foot_width_mm"] * MM

    m = RobotModel(name="bdx_a", root="base_link")
    # Torso + static head + battery/electronics lumped into the floating base.
    # Sits ABOVE the hip origins (com raised, bottom at z=0) so it doesn't overlap
    # the hip-roll links hanging below at z ~ -0.04.
    m.add_link(Link("base_link", mass=0.60,
                    shape=Shape("box", (0.07, 0.10, 0.12)), com=(0.0, 0.0, 0.06)))

    limits = {j["name"]: j["limit_rad"] for j in p["dof"]}
    ids = {j["name"]: j["servo_id"] for j in p["dof"]}

    def leg(side, sign):
        y = sign * half_hip
        hy, hr = f"{side}_hip_yaw", f"{side}_hip_roll"
        hp, kn, an = f"{side}_hip_pitch", f"{side}_knee", f"{side}_ankle_pitch"
        # Small servo-block links for yaw/roll.
        m.add_link(Link(f"{side}_hipyaw_link", 0.08, Shape("box", (0.035, 0.035, 0.035))))
        m.add_link(Link(f"{side}_hiproll_link", 0.08, Shape("box", (0.035, 0.035, 0.035))))
        m.add_link(Link(f"{side}_thigh", 0.13, Shape("box", (0.03, 0.035, thigh)),
                        com=(0, 0, -thigh / 2)))
        m.add_link(Link(f"{side}_shin", 0.11, Shape("box", (0.03, 0.03, shin)),
                        com=(0, 0, -shin / 2)))
        m.add_link(Link(f"{side}_foot", 0.06, Shape("box", (foot_l, foot_w, 0.02)),
                        com=(0.015, 0, -0.01)))
        _revolute(m, hy, "base_link", f"{side}_hipyaw_link", (0.0, y, -0.02), (0, 0, 1), limits[hy], servo, ids[hy])
        _revolute(m, hr, f"{side}_hipyaw_link", f"{side}_hiproll_link", (0, 0, -0.02), (1, 0, 0), limits[hr], servo, ids[hr])
        _revolute(m, hp, f"{side}_hiproll_link", f"{side}_thigh", (0, 0, -0.02), (0, 1, 0), limits[hp], servo, ids[hp])
        _revolute(m, kn, f"{side}_thigh", f"{side}_shin", (0, 0, -thigh), (0, 1, 0), limits[kn], servo, ids[kn])
        _revolute(m, an, f"{side}_shin", f"{side}_foot", (0, 0, -shin), (0, 1, 0), limits[an], servo, ids[an])
        # Statically-stable symmetric crouch: hip_pitch + knee + ankle == 0 (foot flat).
        m.default_q.update({hp: -0.3, kn: 0.6, an: -0.3})

    leg("l", +1)
    leg("r", -1)

    # Base height so the crouched feet rest on the floor (sagittal FK, angles sum 0).
    zc = math.cos(0.3)
    ankle_drop = 0.02 + 0.02 + 0.02 + thigh * zc + shin * zc  # hip stack + segments
    m.default_base_height = ankle_drop + 0.02  # + foot half-height
    return m


# --------------------------------------------------------------------------- #
# ROCKY-5 (pentaradial, 15 DOF)
# --------------------------------------------------------------------------- #
def build_rocky() -> RobotModel:
    p = load_params("rocky")
    d = p["dimensions"]
    servo = p["servo"]
    coxa = d["coxa_mm"] * MM
    femur = d["femur_mm"] * MM
    tibia = d["tibia_mm"] * MM
    mount_r = d["carapace_dia_mm"] * MM / 2 - 0.028  # coxa mount radius (matches core_plate)

    m = RobotModel(name="rocky", root="base_link")
    m.add_link(Link("base_link", mass=0.70,
                    shape=Shape("cylinder", (d["carapace_dia_mm"] * MM / 2, 0.06)),
                    com=(0, 0, 0.0)))

    tmpl = {t["suffix"]: t for t in p["dof_template"]}
    for i in range(p["limb_count"]):
        ang = math.radians(i * p["limb_angle_deg"])
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = mount_r * ca, mount_r * sa
        coxa_l, fem_l, tib_l = f"leg{i}_coxa", f"leg{i}_femur", f"leg{i}_tibia"
        cyaw, fpit, tpit = f"leg{i}_coxa_yaw", f"leg{i}_femur_pitch", f"leg{i}_tibia_pitch"
        # The coxa_yaw joint already rotates the limb frame by `ang`, so in the
        # LOCAL femur/tibia frame the tangential pitch axis is simply +Y.
        pitch_axis = (0.0, 1.0, 0.0)
        m.add_link(Link(coxa_l, 0.09, Shape("box", (coxa, 0.03, 0.03)), com=(coxa / 2, 0, 0)))
        m.add_link(Link(fem_l, 0.10, Shape("box", (femur, 0.028, 0.028)), com=(femur / 2, 0, 0)))
        m.add_link(Link(tib_l, 0.07, Shape("box", (tibia, 0.024, 0.024)), com=(tibia / 2, 0, 0)))
        # TPU 95A hemispherical foot (Ø18 mm) at the tibia tip — the clean contact.
        foot_l = f"leg{i}_foot"
        foot_r = d["foot_dia_mm"] * MM / 2
        m.add_link(Link(foot_l, 0.02, Shape("sphere", (foot_r,))))
        _revolute(m, cyaw, "base_link", coxa_l, (cx, cy, 0.0), (0, 0, 1),
                  tmpl["coxa_yaw"]["limit_rad"], servo, 3 * i + 1, rpy=(0, 0, ang))
        _revolute(m, fpit, coxa_l, fem_l, (coxa, 0, 0), pitch_axis,
                  tmpl["femur_pitch"]["limit_rad"], servo, 3 * i + 2)
        _revolute(m, tpit, fem_l, tib_l, (femur, 0, 0), pitch_axis,
                  tmpl["tibia_pitch"]["limit_rad"], servo, 3 * i + 3)
        m.add_joint(Joint(f"leg{i}_ankle_fixed", "fixed", tib_l, foot_l, (tibia, 0, 0)))
        # Sprawled stance. In the limb frame the femur extends +X and pitches
        # about the tangential axis; a POSITIVE angle rotates +X toward -Z (down).
        fp, tp = 0.6, 1.0
        m.default_q.update({cyaw: 0.0, fpit: fp, tpit: tp})

    # Foot height below the coxa from the limb FK (radial plane).
    foot_drop = femur * math.sin(0.6) + tibia * math.sin(0.6 + 1.0)
    m.default_base_height = foot_drop + 0.03
    return m


def build(robot: str) -> RobotModel:
    return {"bdx_a": build_bdx_a, "rocky": build_rocky}[robot]()
