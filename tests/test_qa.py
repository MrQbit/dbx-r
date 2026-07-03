"""G2 mesh-QA checks (ROBOTS_SPEC.md §8). Runs in the host venv (trimesh only).

Test-first: known-good and known-bad meshes exercise every QA rule before any
real part is generated, so QA failures are caught here, never at the slicer.
"""

from __future__ import annotations

import numpy as np
import trimesh

from common.export.qa import check_mesh
from common.cad_lib.standards import MIN_WALL_STRUCTURAL_MM


def test_good_box_passes():
    m = trimesh.creation.box((30, 20, 10))
    r = check_mesh(m, "good_box", MIN_WALL_STRUCTURAL_MM)
    assert r.passed, r.failures
    assert r.watertight and r.volume_mm3 > 0 and r.fits_envelope


def test_oversize_box_fails_envelope():
    m = trimesh.creation.box((300, 20, 10))  # 300 mm > 250 mm envelope
    r = check_mesh(m, "oversize", MIN_WALL_STRUCTURAL_MM)
    assert not r.passed
    assert not r.fits_envelope
    assert any("envelope" in f for f in r.failures)


def test_open_mesh_fails_watertight():
    m = trimesh.creation.box((30, 20, 10))
    m.update_faces(np.arange(len(m.faces)) != 0)  # drop one face -> a hole
    r = check_mesh(m, "open", MIN_WALL_STRUCTURAL_MM)
    assert not r.passed
    assert not r.watertight
    assert any("watertight" in f for f in r.failures)


def test_thin_plate_fails_min_wall():
    # 1.0 mm thick plate is below the 2.4 mm structural minimum.
    m = trimesh.creation.box((40, 40, 1.0))
    r = check_mesh(m, "thin_plate", MIN_WALL_STRUCTURAL_MM)
    assert r.min_wall_mm is not None
    assert not r.min_wall_ok
    assert any("min wall" in f for f in r.failures)


def test_thick_block_passes_min_wall():
    m = trimesh.creation.box((40, 40, 8.0))  # 8 mm >> 2.4 mm
    r = check_mesh(m, "thick", MIN_WALL_STRUCTURAL_MM)
    assert r.min_wall_ok, f"min_wall={r.min_wall_mm}"
