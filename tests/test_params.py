"""G1 gate — params complete & frozen (ROBOTS_SPEC.md §10).

Test-first: these assertions exist before the params are declared "done".
Zero TODO markers, DOF counts/ordering/IDs exactly as the spec mandates.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.params import load_params, bdx_a_dof, rocky_dof, params_path

# 10 legs (IDs 1-10) then the active 3-DOF neck (IDs 11-13, D-005).
BDX_A_LEG_ORDER = [
    "l_hip_yaw", "l_hip_roll", "l_hip_pitch", "l_knee", "l_ankle_pitch",
    "r_hip_yaw", "r_hip_roll", "r_hip_pitch", "r_knee", "r_ankle_pitch",
]
BDX_A_NECK_ORDER = ["head_pitch1", "head_pitch2", "head_yaw"]
BDX_A_DOF_ORDER = BDX_A_LEG_ORDER + BDX_A_NECK_ORDER


@pytest.mark.parametrize("robot", ["bdx_a", "rocky"])
def test_no_todo_markers(robot):
    text = params_path(robot).read_text()
    assert "TODO" not in text, f"{robot} params.yaml still contains a TODO"


def test_bdx_a_dof_order_and_ids():
    dof = bdx_a_dof(load_params("bdx_a"))
    assert [d["name"] for d in dof] == BDX_A_DOF_ORDER, "DOF order is law (§3.3, D-005)"
    # IDs 1..13 in declared order; obs order == action order == servo ID order.
    assert [d["servo_id"] for d in dof] == list(range(1, 14))
    assert [d["name"] for d in dof[:10]] == BDX_A_LEG_ORDER  # legs unchanged, 1-10


def test_bdx_a_limits_match_spec():
    dof = {d["name"]: d["limit_rad"] for d in bdx_a_dof(load_params("bdx_a"))}
    assert dof["l_hip_yaw"] == [-0.6, 0.6]
    assert dof["l_hip_pitch"] == [-1.6, 0.6]
    assert dof["l_knee"] == [0.0, 2.2]
    assert dof["l_ankle_pitch"] == [-1.0, 1.0]


def test_rocky_expands_to_15_dof():
    dof = rocky_dof(load_params("rocky"))
    assert len(dof) == 15
    # Servo IDs = 3i+1, 3i+2, 3i+3 for i in 0..4 -> a contiguous 1..15.
    assert sorted(d["servo_id"] for d in dof) == list(range(1, 16))
    assert dof[0]["name"] == "leg0_coxa_yaw"
    assert dof[-1]["name"] == "leg4_tibia_pitch"


def test_shared_battery_pack():
    a = load_params("bdx_a")["battery"]
    r = load_params("rocky")["battery"]
    assert a["bay_mm"] == r["bay_mm"] == [70, 38, 20]
    assert a["cells"] == r["cells"] == 3
