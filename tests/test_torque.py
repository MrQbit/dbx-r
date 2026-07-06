"""G1 gate — torque PASS at design-target mass (ROBOTS_SPEC.md §3.3, §4).

Test-first. The check runs at `design_target_kg`; the final CAD-mass re-check
lives with G2 once mass properties exist.
"""

from __future__ import annotations

from common.params import load_params
from common.cad_lib.torque import check_rocky

# BDX-A adopts BDX-R's Robstride actuators (D-007) — a proven walking build, so
# its torque is validated upstream, not re-derived here. Only ROCKY-5 (our own
# STS3215 design) needs the torque gate.


def test_rocky_torque_passes_by_construction():
    result = check_rocky(load_params("rocky"))
    assert result.passed
    # D-034: reconciled to the official sculpt (73mm femur) -> hold ~0.80 N·m ->
    # EduLite is comfortable again at ~2.25x continuous ratio (7x peak headroom).
    assert result.continuous_ratio >= 1.5
