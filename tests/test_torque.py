"""G1 gate — torque PASS at design-target mass (ROBOTS_SPEC.md §3.3, §4).

Test-first. The check runs at `design_target_kg`; the final CAD-mass re-check
lives with G2 once mass properties exist.
"""

from __future__ import annotations

from common.params import load_params
from common.cad_lib.torque import check_bdx_a, check_rocky


def test_bdx_a_torque_passes_at_target():
    result = check_bdx_a(load_params("bdx_a"))
    assert result.continuous_pass, (
        f"continuous margin failed: {result.continuous_ratio:.2f}× "
        f"(need {result.continuous_required:.3f} N·m)"
    )
    assert result.stall_pass
    assert result.passed


def test_rocky_torque_passes_by_construction():
    result = check_rocky(load_params("rocky"))
    assert result.passed
    # §4: femur worst case is comfortably inside continuous torque.
    assert result.continuous_ratio >= 1.8


def test_bdx_a_mass_ceiling_is_documented_and_below_budget():
    """The continuous criterion caps usable mass; the ceiling must be a real
    number below the 2.6 kg budget so the report can warn about it (D-002)."""
    params = load_params("bdx_a")
    result = check_bdx_a(params)
    assert result.max_mass_for_pass_kg < params["mass_budget_kg"]
    assert result.max_mass_for_pass_kg > params["design_target_kg"]
