"""BDX-A adoption gate — validate the exact vendored BDX-R model (D-007).

BDX-A is BDX-R unchanged, so the meaningful check is that the upstream model
loads and matches the DOF contract our params record. Skips (not fails) when the
upstream hasn't been fetched, so the suite runs on a bare checkout.
"""

from __future__ import annotations

import pytest

from common.params import load_params
from common.description_gen import bdxr

pytestmark = pytest.mark.skipif(not bdxr.is_available(),
                                reason="BDX-R not fetched (scripts/fetch_upstream.sh)")


def _model():
    import mujoco
    return mujoco.MjModel.from_xml_path(str(bdxr.mjcf_path(full=True)))


def test_bdxr_model_loads_with_14_dof():
    import mujoco
    mj = _model()
    hinges = [i for i in range(mj.njnt) if mj.jnt_type[i] == mujoco.mjtJoint.mjJNT_HINGE]
    assert len(hinges) == 14, "BDX-R full model is 10 legs + 4-DOF head"
    names = [mujoco.mj_id2name(mj, mujoco.mjtObj.mjOBJ_JOINT, i) for i in hinges]
    assert names == bdxr.BDXR_JOINTS


def test_params_record_matches_upstream():
    dof = load_params("bdx_a")["dof"]
    assert [d["name"] for d in dof] == bdxr.BDXR_JOINTS
    assert [d["servo_id"] for d in dof] == list(range(1, 15))


def test_bdxr_masses_positive():
    mj = _model()
    # Every body (except world) has positive mass — a sane, trainable model.
    assert all(mj.body_mass[i] > 0 for i in range(1, mj.nbody))
    assert mj.nq == 21  # 7 (free base) + 14 hinges
