"""G3 gate — descriptions load + settle (ROBOTS_SPEC.md §5, §10).

Runs in the host venv (yourdfpy + mujoco, both aarch64-native). The USD leg of
the pipeline is validated in the isaac container stage, not here.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import yourdfpy
import mujoco

from common.params import load_params, bdx_a_dof, rocky_dof
from common.description_gen.builders import build
from common.description_gen.urdf import to_urdf
from common.description_gen.mjcf import to_mjcf
from common.description_gen.settle import run_settle

ROBOTS = ["bdx_a", "rocky"]
EXPECTED_DOF = {"bdx_a": 10, "rocky": 15}


@pytest.mark.parametrize("robot", ROBOTS)
def test_urdf_loads_in_yourdfpy(robot):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f"{robot}.urdf"
        p.write_text(to_urdf(build(robot)))
        u = yourdfpy.URDF.load(str(p))
        actuated = [j for j in u.robot.joints if j.type == "revolute"]
        assert len(actuated) == EXPECTED_DOF[robot]


@pytest.mark.parametrize("robot", ROBOTS)
def test_mjcf_loads_in_mujoco(robot):
    mj = mujoco.MjModel.from_xml_string(to_mjcf(build(robot)))
    assert mj.nu == EXPECTED_DOF[robot]        # one actuator per DOF
    assert mj.njnt >= EXPECTED_DOF[robot] + 1  # + free joint


@pytest.mark.parametrize("robot", ROBOTS)
def test_inertias_positive_definite_and_near_uniform(robot):
    m = build(robot)
    for link in m.links.values():
        eig = np.linalg.eigvalsh(link.inertia().matrix())
        assert np.all(eig > 0), f"{robot}/{link.name} inertia not positive-definite"
        # Within 10x of the bounding-box uniform-density estimate (§5).
        est = link.uniform_estimate_inertia()
        for got, ref in ((link.inertia().ixx, est.ixx),
                         (link.inertia().iyy, est.iyy),
                         (link.inertia().izz, est.izz)):
            assert 0.1 <= got / ref <= 10.0, f"{robot}/{link.name} inertia off uniform est"


@pytest.mark.parametrize("robot", ROBOTS)
def test_joint_tree_matches_params(robot):
    m = build(robot)
    dof = bdx_a_dof(load_params("bdx_a")) if robot == "bdx_a" else rocky_dof(load_params("rocky"))
    model_names = {j.name for j in m.actuated_joints}
    for d in dof:
        assert d["name"] in model_names, f"missing joint {d['name']}"
        j = next(j for j in m.actuated_joints if j.name == d["name"])
        assert j.servo_id == d["servo_id"]
        assert [j.lower, j.upper] == d["limit_rad"]


@pytest.mark.parametrize("robot", ROBOTS)
def test_settle_5s(robot):
    r = run_settle(build(robot))
    assert r.base_lin_vel < 0.05, f"{robot} base drifting at {r.base_lin_vel:.3f} m/s"
    assert r.self_pen_mm <= 1.0, f"{robot} self-collision penetration {r.self_pen_mm:.2f} mm"
    assert r.n_foot_contacts >= 2
