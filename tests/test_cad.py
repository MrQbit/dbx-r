"""G2 gate — CAD parts generate, pass mesh QA, and the interference check works
(ROBOTS_SPEC.md §4.5, §8). Runs under scripts/cadpy (build123d present).

Seed coverage: the registered parts (coupons + one structural part per robot).
The full part set grows here as parts are authored; every one must clear QA.
"""

from __future__ import annotations

import trimesh
import pytest

from common.cad_lib.registry import parts_for, all_robots
from common.cad_lib.export import export_part_stl
from common.export.qa import check_mesh
from common.cad_lib.interference import pair_interference_volume


@pytest.mark.parametrize("robot", all_robots())
def test_registered_parts_pass_qa(robot, tmp_path):
    mods = parts_for(robot)
    assert mods, f"{robot} has no registered parts"
    for mod in mods:
        meta = mod.META
        stl = export_part_stl(mod.part(), tmp_path / f"{meta.name}.stl")
        report = check_mesh(trimesh.load(stl), meta.name, meta.min_wall_mm)
        assert report.passed, f"{robot}/{meta.name} failed QA: {report.failures}"
        assert report.watertight and report.fits_envelope


def test_part_meta_contract():
    for robot in all_robots():
        for mod in parts_for(robot):
            m = mod.META
            assert m.material in ("PETG", "PLA", "TPU")
            assert m.qty >= 1
            assert len(m.orientation_quat) == 4


def test_interference_detects_overlap_and_clearance(tmp_path):
    from bdx_a.cad.parts import knee_link
    stl = export_part_stl(knee_link.part(), tmp_path / "k.stl")
    mesh = trimesh.load(stl)

    overlap = mesh.copy()
    overlap.apply_translation([5.0, 0.0, 0.0])   # slid 5 mm along a 96 mm link
    assert pair_interference_volume(mesh, overlap) > 0.05, "overlap must be detected"

    apart = mesh.copy()
    apart.apply_translation([500.0, 0.0, 0.0])   # far away
    assert pair_interference_volume(mesh, apart) <= 0.05, "disjoint must read clean"
