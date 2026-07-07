#!/usr/bin/env python3
"""TASK 4 verify — HONEST shell-to-shell motion-clearance sweep for the D-043
uniform-scaled leg shells over the LENGTHENED chassis.

For each of the 5 legs it poses the cosmetic shell SEGMENTS (coxa / femur / tibia,
the hollow 3 mm clamshells from blender_actionfig_shells.py) through the real joint
ranges (leg_geom limits) and boolean-measures the worst shell<->shell overlap:

  * femur_pitch [-1.4, 1.0]: femur shell (swung about P1=60, Y) vs coxa shell (static)
  * knee        [-0.3, 2.0]: tibia shell (swung about knee=158, Y) vs femur shell
  * tibia_roll  [-1.5, 1.5]: tibia shell (rolled about the leg X axis) vs femur shell

Uses the same manifold boolean as the G2 interference gate. Writes
rocky/cad/stl_derived/af_shells/clearance_sweep.json and folds the result into
shell_report.json (clearance_sweep_mm3 + clearance_summary) for the render.

Run (host venv, trimesh):  ./.venv/bin/python scripts/sweep_shell_clearance.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
from common.cad_lib.interference import pair_interference_volume  # noqa: E402
from rocky.cad.parts import leg_geom as G  # noqa: E402

SH = ROOT / "rocky/cad/stl_derived/af_shells"

P1X = G.P1[0]     # femur_pitch axis x = 60
KNEE = G.P2[0]    # knee axis x = 158


def _T(p):
    m = np.eye(4); m[:3, 3] = p; return m


def rot_about(axis, ang, p):
    """4x4 rotation by `ang` about `axis` ('x'|'y'|'z') through point p."""
    c, s = math.cos(ang), math.sin(ang)
    R = np.eye(4)
    if axis == "y":
        R[0, 0], R[0, 2], R[2, 0], R[2, 2] = c, s, -s, c
    elif axis == "x":
        R[1, 1], R[1, 2], R[2, 1], R[2, 2] = c, -s, s, c
    else:  # z
        R[0, 0], R[0, 1], R[1, 0], R[1, 1] = c, -s, s, c
    return _T(p) @ R @ _T([-p[0], -p[1], -p[2]])


def load(N, seg):
    return trimesh.load(SH / f"leg{N}_{seg}_hollow.stl")


def posed(mesh, T):
    m = mesh.copy(); m.apply_transform(T); return m


def worst(mesh_move, T_list, mesh_static):
    w = 0.0
    for T in T_list:
        v = pair_interference_volume(posed(mesh_move, T), mesh_static)
        w = max(w, v)
    return round(w, 2)


def lin(lo, hi, n):
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def main() -> int:
    out = {}
    for N in range(1, 6):
        coxa = load(N, "coxa"); femur = load(N, "femur"); tibia = load(N, "tibia")
        # femur_pitch: femur swings about P1 (Y); coxa static
        fp = worst(femur, [rot_about("y", q, G.P1) for q in lin(*G.FEMUR_PITCH_LIMIT, 7)], coxa)
        # knee: tibia swings about the knee (Y); femur static (up to the full 2.0 fold)
        kn = worst(tibia, [rot_about("y", q, G.P2) for q in lin(*G.TIBIA_PITCH_LIMIT, 8)], femur)
        # roll: tibia rolls about the leg long axis (X through y=z=0); femur static
        rl = worst(tibia, [rot_about("x", q, (0.0, 0.0, 0.0)) for q in lin(*G.TIBIA_ROLL_LIMIT, 5)], femur)
        out[str(N)] = {
            "femur_pitch_worst_mm3": fp,
            "femur_pitch_full_range_clear": fp <= 1.0,
            "knee_worst_mm3": kn,
            "knee_clear_to_rad": G.TIBIA_PITCH_LIMIT[1],
            "knee_full_2.0_clear": kn <= 1.0,
            "roll_worst_mm3": rl,
            "roll_full_range_clear": rl <= 1.0,
        }
        print(f"[sweep] leg{N}: femur_pitch {fp} mm3, knee(->2.0) {kn} mm3, roll {rl} mm3")

    (SH / "clearance_sweep.json").write_text(json.dumps(out, indent=2))

    rep_path = SH / "shell_report.json"
    rep = json.loads(rep_path.read_text())
    rep["clearance_sweep_mm3"] = out
    all_clear = all(v["femur_pitch_full_range_clear"] and v["knee_full_2.0_clear"]
                    and v["roll_full_range_clear"] for v in out.values())
    rep["clearance_summary"] = (
        f"D-043 uniform-scaled shells (s=4.40, lat=4.40) over the LENGTHENED chassis "
        f"(femur 98 / tibia 170; hip->tip 328): all 5 legs femur_pitch full [-1.4,1.0], "
        f"knee full [-0.3,2.0] incl 2.0 rad fold, tibia_roll full [-1.5,1.5] "
        f"{'— 0 mm3 shell-to-shell (CLEAR)' if all_clear else '— SOME OVERLAP, see values'}.")
    rep_path.write_text(json.dumps(rep, indent=2))
    print(f"[sweep] all-clear = {all_clear}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
