"""MuJoCo settle test (ROBOTS_SPEC.md §5 G3).

Plant the robot at its default pose (feet exactly on the floor, computed from
geom geometry so there's no initial jam), hold the default joint targets with the
PD actuators, simulate 5 s, and report:
  * |base linear velocity|  (must be < 0.05 m/s)
  * max SELF-collision penetration (robot-robot only; must be <= 1 mm)

Floor contact penetration is normal resting contact and is excluded — the spec's
1 mm bound is on self-collision.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import mujoco

from common.description_gen.model import RobotModel
from common.description_gen.mjcf import to_mjcf


@dataclass
class SettleResult:
    base_lin_vel: float
    self_pen_mm: float
    base_z: float
    n_contacts: int
    n_foot_contacts: int

    def ok(self, max_vel=0.05, max_pen_mm=1.0) -> bool:
        return self.base_lin_vel < max_vel and self.self_pen_mm <= max_pen_mm


def _lowest_world_z(mj, data) -> float:
    """Minimum world z over all non-floor geom bounding-box corners."""
    floor = mujoco.mj_name2id(mj, mujoco.mjtObj.mjOBJ_GEOM, "floor")
    signs = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    lo = np.inf
    for g in range(mj.ngeom):
        if g == floor:
            continue
        pos = data.geom_xpos[g]
        mat = data.geom_xmat[g].reshape(3, 3)
        size = mj.geom_size[g]
        corners = pos + (signs * size) @ mat.T
        lo = min(lo, corners[:, 2].min())
    return float(lo)


def run_settle(model: RobotModel, seconds: float = 5.0) -> SettleResult:
    xml = to_mjcf(model)
    mj = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(mj)
    floor = mujoco.mj_name2id(mj, mujoco.mjtObj.mjOBJ_GEOM, "floor")

    # Set joint angles + actuator targets to the default pose.
    for j in model.actuated_joints:
        jid = mujoco.mj_name2id(mj, mujoco.mjtObj.mjOBJ_JOINT, j.name)
        data.qpos[mj.jnt_qposadr[jid]] = model.default_q.get(j.name, 0.0)
        aid = mujoco.mj_name2id(mj, mujoco.mjtObj.mjOBJ_ACTUATOR, j.name)
        data.ctrl[aid] = model.default_q.get(j.name, 0.0)

    # Plant: shift base so the lowest geom point kisses the floor (+0.5 mm).
    mujoco.mj_forward(mj, data)
    data.qpos[2] += -_lowest_world_z(mj, data) + 0.0005
    mujoco.mj_forward(mj, data)

    for _ in range(int(seconds / mj.opt.timestep)):
        mujoco.mj_step(mj, data)

    self_pen = 0.0
    n_foot = 0
    for i in range(data.ncon):
        c = data.contact[i]
        is_floor = floor in (c.geom1, c.geom2)
        if is_floor:
            n_foot += 1
        elif c.dist < 0:
            self_pen = max(self_pen, -c.dist)
    return SettleResult(
        base_lin_vel=float(np.linalg.norm(data.qvel[0:3])),
        self_pen_mm=self_pen * 1000.0,
        base_z=float(data.qpos[2]),
        n_contacts=int(data.ncon),
        n_foot_contacts=n_foot,
    )
