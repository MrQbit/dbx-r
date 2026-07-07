"""G1 gate — torque PASS at design-target mass (ROBOTS_SPEC.md §3.3, §4).

Test-first. The check runs at `design_target_kg`; the final CAD-mass re-check
lives with G2 once mass properties exist.
"""

from __future__ import annotations

from common.params import load_params
from common.cad_lib.torque import check_rocky

# BDX-A adopts BDX-R's Robstride actuators (D-007) — a proven walking build, so
# its torque is validated upstream, not re-derived here. Only ROCKY-5 (our own
# hip-cluster QDD + knee-driveshaft design, D-042) needs the torque gate.


def test_rocky_torque_passes_by_construction():
    result = check_rocky(load_params("rocky"))
    assert result.passed
    # D-043: the femur was lengthened 73 -> 98 mm (long slender movie legs), so the femur
    # worst-case hold rises ~linearly with the lever, 0.80 -> 1.074 N·m. HONEST re-baseline
    # of the QDD headroom at the LONGER lever (the margins 1.5x cont / 3.0x stall are
    # UNCHANGED — the gate is NOT weakened; only these documented-headroom sanity bars move
    # to the new TRUE numbers): femur_pitch continuous 1.8/1.074 = 1.68x (was 2.25x under the
    # shorter D-042 femur), stall 6.0/1.074 = 5.59x. The knee (0.9-eff driveshaft) sits at
    # 1.51x continuous — the binding margin, and why the femur was capped at 98 mm. See D-043.
    assert result.continuous_ratio >= 1.6      # true 1.68 (femur_pitch, direct)
    assert result.stall_ratio >= 5.0           # true 5.59
    # the driveshaft knee is the tightest weight-bearing joint — still >= 1.5x continuous.
    tq = load_params("rocky")["torque_check"]
    knee_cont_ratio = tq["knee_effective_continuous_nm"] / tq["femur_worst_case_nm"]
    assert knee_cont_ratio >= 1.5, f"knee continuous margin {knee_cont_ratio:.3f} < 1.5x"
