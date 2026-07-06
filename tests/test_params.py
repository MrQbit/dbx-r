"""G1 gate — params complete & frozen (ROBOTS_SPEC.md §10).

Test-first: these assertions exist before the params are declared "done".
Zero TODO markers, DOF counts/ordering/IDs exactly as the spec mandates.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.params import load_params, rocky_dof, params_path

# BDX-A is adopted verbatim from BDX-R (D-007); its DOF are validated against the
# upstream model in test_bdxr.py, not here.


@pytest.mark.parametrize("robot", ["bdx_a", "rocky"])
def test_no_todo_markers(robot):
    text = params_path(robot).read_text()
    assert "TODO" not in text, f"{robot} params.yaml still contains a TODO"


def test_rocky_expands_to_20_dof():
    dof = rocky_dof(load_params("rocky"))
    # 15 leg joints + 5 grip manipulators — EVERY limb is a 3-finger hand (D-028).
    assert len(dof) == 20
    assert sorted(d["servo_id"] for d in dof) == list(range(1, 21))
    assert dof[0]["name"] == "leg0_coxa_yaw"
    assert dof[14]["name"] == "leg4_tibia_pitch"   # last leg joint
    grips = [d["name"] for d in dof if d["name"].endswith("_grip")]
    assert grips == ["leg0_grip", "leg1_grip", "leg2_grip", "leg3_grip", "leg4_grip"]
