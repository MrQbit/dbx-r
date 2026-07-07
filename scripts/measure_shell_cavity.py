#!/usr/bin/env python3
"""D-044 fit verify — does the LOCKED slim chassis fit inside the craggy figure-surface
cavity, now that the fat Ø52 clearance core is GONE?

Honest solid test (host venv, trimesh): sample the real neutral chassis (frame+servos,
docs/build_plan/leg_chassis_neutral_*.stl — the SAME meshes the ghost render draws) and,
for each leg segment, measure the signed distance of every chassis point to that segment's
SOLID cosmetic shell. Inside is positive; a chassis point needs signed_distance >= WALL
(3 mm) to have a full cosmetic wall around it.

  clearance_min_mm = min signed distance over chassis pts in the segment's x-range - WALL
     >= 0  : chassis fits with a full >=3 mm cosmetic wall (CLEAR)
     <0..-3: chassis inside the craggy skin but the wall is locally thinner than 3 mm
     < -3  : chassis pokes THROUGH the cosmetic outer surface (real clash -> needs relief)

Writes af_shells/cavity_fit.json and folds it into shell_report.json (cavity_fit_measured).
Run:  ./.venv/bin/python scripts/measure_shell_cavity.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
SH = ROOT / "rocky/cad/stl_derived/af_shells"
BP = ROOT / "docs/build_plan"
WALL = 3.0

# chassis body-station x-ranges (leg_geom): hip 0, femur_pitch 60, knee 158, tip 328.
# The cosmetic sheaths the SLIM LINK mid-bodies; the servo housings / hip-cluster QDD /
# knee+roll brackets are the bulbous stone KNUCKLES at the joint stations (Rocky canon
# D-029) — external, locally relieved, NOT buried in the slim shell. So the fit that
# matters is over each segment's LINK mid-body (between the joint knuckles), profiled
# from the real neutral chassis STL:
#   coxa   x0-60  = ALL hip-cluster QDD knuckle (no slim link) -> cosmetic is a collar
#   femur  x92-132 = the Ø12 driveshaft mid-span (servo knuckle at P1 x40-90 excluded)
#   tibia  x168-250 = the shank mid (knee bracket <168, roll-servo bracket >250 excluded)
LINK_X = {"coxa": (8.0, 46.0), "femur": (92.0, 132.0), "tibia": (168.0, 250.0)}
# whole-segment (incl. joint knuckles) kept for the honest full-context number
SEG_X = {"coxa": (-5.0, 60.0), "femur": (60.0, 158.0), "tibia": (158.0, 340.0)}


def chassis_points():
    parts = []
    for p in ("frame", "servos"):
        f = BP / f"leg_chassis_neutral_{p}.stl"
        m = trimesh.load(f, force="mesh")
        parts.append(m)
    ch = trimesh.util.concatenate(parts)
    # dense surface sample + the raw vertices (captures both the skin and corners)
    pts = np.vstack([ch.sample(20000), ch.vertices])
    return pts


def _fit(shell, sel):
    """signed-distance stats of chassis pts `sel` vs the cosmetic solid `shell`."""
    if len(sel) == 0:
        return {"note": "no chassis pts in x-range"}
    sd = trimesh.proximity.signed_distance(shell, sel)  # + inside the skin
    clr = sd - WALL                                     # margin to a full 3 mm wall
    return {
        "chassis_pts": int(len(sel)),
        "min_wall_clearance_mm": round(float(clr.min()), 1),   # <0 => wall <3mm there
        "median_wall_clearance_mm": round(float(np.median(clr)), 1),
        "pct_wall_under_3mm": round(100 * float((clr < 0).mean()), 1),
        "pct_chassis_pierces_skin": round(100 * float((sd < 0).mean()), 2),
        "full_3mm_wall_everywhere": bool(clr.min() >= 0.0),
    }


def main() -> int:
    pts = chassis_points()
    out = {}
    worst_link = 1e9
    for N in range(1, 6):
        legrow = {}
        for seg in SEG_X:
            shell = trimesh.load(SH / f"leg{N}_{seg}_solid.stl", force="mesh")
            x0, x1 = SEG_X[seg]
            lx0, lx1 = LINK_X[seg]
            full = _fit(shell, pts[(pts[:, 0] >= x0) & (pts[:, 0] < x1)])
            link = _fit(shell, pts[(pts[:, 0] >= lx0) & (pts[:, 0] < lx1)])
            legrow[seg] = {"link_midbody": link, "whole_segment_incl_knuckles": full}
            if seg != "coxa" and "min_wall_clearance_mm" in link:
                worst_link = min(worst_link, link["min_wall_clearance_mm"])
        out[str(N)] = legrow
        print(f"[cavity] leg{N} LINK mid-body: " + "  ".join(
            f"{s} min_wall {legrow[s]['link_midbody'].get('min_wall_clearance_mm','-')}mm"
            f"/pierce {legrow[s]['link_midbody'].get('pct_chassis_pierces_skin','-')}%"
            for s in ("femur", "tibia")))

    (SH / "cavity_fit.json").write_text(json.dumps(out, indent=2))
    rep_path = SH / "shell_report.json"
    rep = json.loads(rep_path.read_text())
    rep["cavity_fit_measured"] = out
    rep["cavity_fit_note"] = (
        "D-044: fat clearance core REMOVED; shell = craggy figure surface hollowed 3 mm "
        "inward. Signed-distance fit of the real neutral chassis (frame+servos) vs each "
        "SOLID cosmetic shell. LINK_MIDBODY = the slim shank/driveshaft between joints "
        "(the fit that matters); WHOLE_SEGMENT also counts the servo/QDD/bracket blocks "
        "at the joint stations = the bulbous stone KNUCKLES (D-029), external + locally "
        "relieved, not enclosed by the slim shell. min_wall_clearance = min chassis depth "
        "inside the skin - 3 mm; <0 = wall locally <3 mm; pct_pierces_skin>0 = chassis "
        "proud of the cosmetic there.")
    rep_path.write_text(json.dumps(rep, indent=2))
    print(f"[cavity] worst LINK-midbody min_wall_clearance (femur+tibia) = {round(worst_link,1)} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
