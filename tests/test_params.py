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


def test_rocky_expands_to_25_dof():
    dof = rocky_dof(load_params("rocky"))
    # 20 leg joints (4 per limb after the D-039 tibia_roll) + 5 grip manipulators —
    # EVERY limb is a 3-finger hand (D-028) with a wrist-roll (D-039).
    assert len(dof) == 25
    assert sorted(d["servo_id"] for d in dof) == list(range(1, 26))
    assert dof[0]["name"] == "leg0_coxa_yaw"
    # Each limb now contributes 4 joints in order; the 4th is the wrist roll.
    assert dof[3]["name"] == "leg0_tibia_roll"
    assert dof[3]["servo_id"] == 4
    assert dof[19]["name"] == "leg4_tibia_roll"     # last leg joint (servo id 20)
    assert dof[19]["servo_id"] == 20
    rolls = [d["name"] for d in dof if d["name"].endswith("_tibia_roll")]
    assert rolls == [f"leg{i}_tibia_roll" for i in range(5)]
    grips = [d["name"] for d in dof if d["name"].endswith("_grip")]
    assert grips == ["leg0_grip", "leg1_grip", "leg2_grip", "leg3_grip", "leg4_grip"]
    assert [d["servo_id"] for d in dof if d["name"].endswith("_grip")] == [21, 22, 23, 24, 25]
