#!/usr/bin/env python3
"""Render a robot's physics model to a PNG from the MJCF (headless, EGL).

A quick way to SEE the training/collision body (primitive geometry) in its
default planted pose — not the aesthetic shells. Also the basis for the periodic
eval videos we log to TensorBoard during G4 training.

Usage: MUJOCO_GL=egl python scripts/render_robot.py <robot> [out.png] [az el dist]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mujoco  # noqa: E402
from PIL import Image  # noqa: E402

from common.description_gen.builders import build  # noqa: E402
from common.description_gen.mjcf import to_mjcf  # noqa: E402
from common.description_gen.settle import _lowest_world_z  # noqa: E402

# ROCKY-5 renders from our params-driven model. BDX-A is the vendored BDX-R
# model (render it from third_party/bdx_r_mjlab directly, not build()).
VIEWS = {"rocky": (130, -30, 0.9)}


def render(robot: str, out: Path, az: float, el: float, dist: float) -> None:
    m = build(robot)
    mj = mujoco.MjModel.from_xml_string(to_mjcf(m))
    data = mujoco.MjData(mj)
    for j in m.actuated_joints:
        jid = mujoco.mj_name2id(mj, mujoco.mjtObj.mjOBJ_JOINT, j.name)
        data.qpos[mj.jnt_qposadr[jid]] = m.default_q.get(j.name, 0.0)
    mujoco.mj_forward(mj, data)
    data.qpos[2] += -_lowest_world_z(mj, data) + 0.001
    mujoco.mj_forward(mj, data)

    ren = mujoco.Renderer(mj, 900, 1200)
    cam = mujoco.MjvCamera()
    cam.azimuth, cam.elevation, cam.distance = az, el, dist
    cam.lookat[:] = [0, 0, data.qpos[2] * 0.55]
    ren.update_scene(data, cam)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(ren.render()).save(out)
    print(f"[render] {robot}: {out} ({len(m.actuated_joints)} DOF)")


def main() -> int:
    robot = sys.argv[1] if len(sys.argv) > 1 else "rocky"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"docs/reports/{robot}_view.png")
    az, el, dist = VIEWS.get(robot, (135, -15, 1.0))
    if len(sys.argv) > 5:
        az, el, dist = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
    render(robot, out, az, el, dist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
