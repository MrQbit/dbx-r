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
    # D-032: at x1.2 (Jetson-carrier fit) EduLite runs at ~1.28x continuous ratio (78%
    # util) with 2.1x peak headroom — its ceiling. Below this the build must not exceed
    # ~6kg. (Was 1.64x at 272mm; the x1.2 upscale spent the margin to fit the electronics.)
    assert result.continuous_ratio >= 1.25
