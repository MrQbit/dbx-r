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


# BDX-A is BDX-R, adopted verbatim (D-007) — no hand-built biped here. Its model
# is the vendored upstream (common.description_gen.bdxr). Only ROCKY-5 below is
# our own params-driven design.


# --------------------------------------------------------------------------- #
# ROCKY-5 (pentaradial, 15 DOF + 2 front-leg grips)
# --------------------------------------------------------------------------- #
def build_rocky() -> RobotModel:
    p = load_params("rocky")
    d = p["dimensions"]
    servo = p["servo"]                    # EduLite QDD (coxa_yaw/femur_pitch/knee), D-042
    servo_roll = p.get("servo_roll", servo)  # STS3215 inline roll (mixed actuator model)
    grip_servo = p.get("grip_servo", servo)  # grip micro
    coxa = d["coxa_mm"] * MM
    femur = d["femur_mm"] * MM
    tibia = d["tibia_mm"] * MM
    mount_r = d["carapace_dia_mm"] * MM / 2 - 0.028  # coxa mount radius (matches core_plate)

    # D-042 LOCK — MASS IN THE BODY, light distal leg. All 3 weight-bearing leg QDD per
    # limb live in the HIP CLUSTER: the coxa_yaw QDD is body-fixed (lumped into base_link,
    # +5x0.242 kg), and the femur_pitch + knee QDD ride the near-hip COXA link (they yaw
    # with the leg but sit at the body). The femur (slim Ø12-shaft wrap) and tibia links
    # carry NO motor — only the shaft/bevel + the light STS3215 roll — so the moving leg is
    # light and the description inertias match the built robot ("train what you print").
    KG_QDD = 0.242
    m = RobotModel(name="rocky", root="base_link")
    m.add_link(Link("base_link", mass=1.15 + 5 * KG_QDD,       # body + 5 coxa_yaw QDD
                    shape=Shape("cylinder", (d["carapace_dia_mm"] * MM / 2, 0.07)),
                    com=(0, 0, 0.0)))

    foot_r = d["foot_dia_mm"] * MM / 2
    man = p.get("manipulators") or {"legs": [], "servo_ids": [], "grip_limit_rad": [0.0, 0.0]}
    grip_ids = dict(zip(man["legs"], man["servo_ids"]))

    tmpl = {t["suffix"]: t for t in p["dof_template"]}
    for i in range(p["limb_count"]):
        ang = math.radians(i * p["limb_angle_deg"])
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = mount_r * ca, mount_r * sa
        coxa_l, fem_l = f"leg{i}_coxa", f"leg{i}_femur"
        # D-039: the tibia is now TWO links — a proximal bracket that carries the
        # inline roll actuator, and a distal shank (+hand) that ROLLS about the leg
        # long axis. `tib_l` (the distal shank) keeps the old name so the hand/foot
        # child joints below still attach to it.
        tprox_l, tib_l = f"leg{i}_tibia_prox", f"leg{i}_tibia"
        cyaw, fpit = f"leg{i}_coxa_yaw", f"leg{i}_femur_pitch"
        tpit, troll = f"leg{i}_tibia_pitch", f"leg{i}_tibia_roll"
        # The coxa_yaw joint already rotates the limb frame by `ang`, so in the
        # LOCAL femur/tibia frame the tangential pitch axis is simply +Y.
        pitch_axis = (0.0, 1.0, 0.0)
        roll_axis = (1.0, 0.0, 0.0)                # the leg long axis (wrist roll)
        roll_off = 0.054                           # knee -> roll axis (STS body + coupling)
        tib_dist = tibia - roll_off                # shank length past the roll axis
        # D-042: the coxa link IS the hip cluster — it carries the femur_pitch + knee QDD
        # (2 x 0.242 kg, near the hip axis). The femur is the SLIM shaft wrap (shaft +
        # bevel, no motor -> light). tibia_prox carries only the light STS3215 roll servo;
        # the shank is a bare slim wrist.
        m.add_link(Link(coxa_l, 0.10 + 2 * KG_QDD, Shape("box", (coxa, 0.05, 0.05)), com=(coxa / 2, 0, 0)))
        m.add_link(Link(fem_l, 0.06, Shape("box", (femur, 0.030, 0.030)), com=(femur / 2, 0, 0)))
        m.add_link(Link(tprox_l, 0.11, Shape("box", (roll_off, 0.04, 0.04)), com=(roll_off / 2, 0, 0)))
        m.add_link(Link(tib_l, 0.06, Shape("box", (tib_dist, 0.03, 0.03)), com=(tib_dist / 2, 0, 0)))
        _revolute(m, cyaw, "base_link", coxa_l, (cx, cy, 0.0), (0, 0, 1),
                  tmpl["coxa_yaw"]["limit_rad"], servo, 4 * i + 1, rpy=(0, 0, ang))
        _revolute(m, fpit, coxa_l, fem_l, (coxa, 0, 0), pitch_axis,
                  tmpl["femur_pitch"]["limit_rad"], servo, 4 * i + 2)
        # Knee is QDD via the driveshaft (same effort/vel model as the direct QDD).
        _revolute(m, tpit, fem_l, tprox_l, (femur, 0, 0), pitch_axis,
                  tmpl["tibia_pitch"]["limit_rad"], servo, 4 * i + 3)
        # tibia_roll rides the leg — the slim STS3215 (mixed actuator model, D-042).
        _revolute(m, troll, tprox_l, tib_l, (roll_off, 0, 0), roll_axis,
                  tmpl["tibia_roll"]["limit_rad"], servo_roll, 4 * i + 4)

        if i in grip_ids:
            # Hand-foot (D-008): a flat palm (ground contact, same height as the
            # sphere feet) + a driven 3-finger grip. grip=0 -> flat foot to stand.
            palm, fing = f"leg{i}_palm", f"leg{i}_finger"
            m.add_link(Link(palm, 0.03, Shape("box", (0.04, 0.04, 2 * foot_r))))
            m.add_link(Link(fing, 0.02, Shape("box", (0.028, 0.03, 0.008)), com=(0.014, 0, 0)))
            m.add_joint(Joint(f"leg{i}_wrist_fixed", "fixed", tib_l, palm, (tib_dist, 0, 0)))
            _revolute(m, f"leg{i}_grip", palm, fing, (0.018, 0, 0.006), (0, 1, 0),
                      man["grip_limit_rad"], grip_servo, grip_ids[i])
            m.default_q[f"leg{i}_grip"] = 0.0
        else:
            foot_l = f"leg{i}_foot"   # TPU hemispherical foot (Ø18) at the tibia tip
            m.add_link(Link(foot_l, 0.02, Shape("sphere", (foot_r,))))
            m.add_joint(Joint(f"leg{i}_ankle_fixed", "fixed", tib_l, foot_l, (tib_dist, 0, 0)))

        # Sprawled stance. In the limb frame the femur extends +X and pitches
        # about the tangential axis; a POSITIVE angle rotates +X toward -Z (down).
        fp, tp = 0.6, 1.0
        m.default_q.update({cyaw: 0.0, fpit: fp, tpit: tp, troll: 0.0})

    # Foot height below the coxa from the limb FK (radial plane).
    foot_drop = femur * math.sin(0.6) + tibia * math.sin(0.6 + 1.0)
    m.default_base_height = foot_drop + 0.03
    return m


def build(robot: str) -> RobotModel:
    # BDX-A is adopted verbatim from BDX-R (D-007) — its model is the vendored
    # upstream, loaded via common.description_gen.bdxr, NOT built here. Only ROCKY-5
    # is our own params-driven design.
    if robot == "bdx_a":
        raise ValueError("BDX-A uses the vendored BDX-R model — see common.description_gen.bdxr")
    return {"rocky": build_rocky}[robot]()
