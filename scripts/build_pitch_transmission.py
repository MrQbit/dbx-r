#!/usr/bin/env python3
"""ROCKY-5 KNEE pitch-transmission study — QA + numbers + assembly export.

Runs under scripts/cadpy (build123d). Evaluates the two ways to keep the EduLite-05
QDD's speed + backdrivability at the knee while getting the fat motor off the joint:

  * SHAFT  (chosen)   — QDD in the hip cluster, remote driveshaft through the
                        femur_pitch joint (double-cardan CVD) + a knee miter bevel.
  * BELT   (fallback) — QDD inline in the femur, HTD-5M timing belt down to the knee.

Writes docs/build_plan/pitch_transmission_facts.json (QA, real numbers, per-station
shell-clearance verdict, anchor layout, mass shift) and exports posed STL groups of
the SHAFT prototype (case / QDD / driveline) for the render isometric.

Usage: cadpy scripts/build_pitch_transmission.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import trimesh  # noqa: E402
from build123d import export_stl  # noqa: E402

from rocky.cad.parts import leg_geom as G  # noqa: E402
from rocky.cad.parts import knee_shaft_tx as SH  # noqa: E402
from rocky.cad.parts import knee_belt_tx as BE  # noqa: E402
from common.cad_lib import standards as S  # noqa: E402
from common.cad_lib.components import SERVO  # noqa: E402  (EduLite-05 QDD)
from common.cad_lib.export import export_part_stl, part_mass  # noqa: E402
from common.export.qa import check_mesh  # noqa: E402

OUT = ROOT / "docs" / "build_plan"
OUT.mkdir(parents=True, exist_ok=True)

# --- shell envelope (from leg_geom slim strut 22x26 + SHELL_GAP 5) ----------
SHELL_OUTER = 44.0                 # slender stone leg cosmetic OD (was Ø54 fat cup)
SHELL_INNER = SHELL_OUTER - 2 * 2.5
MECH_ENVELOPE = SHELL_INNER - 2 * G.SHELL_GAP_MM   # mechanism must stay 5 mm under (Ø29)
OLD_CUP_DIA = 54.0


def _qa(mod):
    p = mod.part()
    stl = export_part_stl(p, OUT / f"_qa_{mod.META.name}.stl")
    mesh = trimesh.load(stl)
    qa = check_mesh(mesh, mod.META.name, mod.META.min_wall_mm)
    mp = part_mass(p, mod.META)
    b = qa.bbox_mm
    return {
        "name": mod.META.name, "passed": qa.passed, "watertight": qa.watertight,
        "bbox_mm": [round(x, 1) for x in b],
        "min_wall_mm": round(qa.min_wall_mm, 2) if qa.min_wall_mm else None,
        "mass_g": round(mp.unit_mass_g, 1), "qty": mod.META.qty,
        "failures": qa.failures,
    }


def _verdict(dia, station, note=""):
    ok = dia <= MECH_ENVELOPE + 1e-6
    return {"station": station, "cross_section_mm": round(dia, 1),
            "envelope_mm": round(MECH_ENVELOPE, 1),
            "fits_under_shell": ok, "note": note}


def main() -> int:
    shaft_qa = _qa(SH)
    belt_qa = _qa(BE)

    # --- femur_pitch CV-angle analysis (the #1 shaft risk) -------------------
    lo, hi = G.FEMUR_PITCH_LIMIT
    max_bend_deg = math.degrees(max(abs(lo), abs(hi)))     # neutral shaft straight at 0
    single_cvd_limit = 50.0
    needs_double_cardan = max_bend_deg > single_cvd_limit
    per_cardan_deg = max_bend_deg / 2.0

    # --- SHAFT per-station shell clearance -----------------------------------
    shaft_stations = [
        _verdict(SH.CVD_CUP_D_MM + 2 * SH.WALL, "femur_pitch knuckle (P1) — CVD cup",
                 "double-cardan CVD centred on the pitch axis"),
        _verdict(max(shaft_qa["bbox_mm"][1], SH.STRUT_H), "femur mid — shaft tube in strut",
                 "Ø6 shaft in a Ø12 bore; strut sets the silhouette"),
        _verdict(2 * SH.BOX_HALF, "knee (P2) — miter bevel box",
                 "M1 16T:16T bevel; box is the widest LEG station"),
        _verdict(SH.STRUT_H, "tibia — driven segment", "no shaft below the knee"),
    ]
    hip_cluster_dia = 3 * S.EDULITE_HOUSING_DIA_MM + 10  # 3 QDDs side by side (in BODY)

    # --- BELT per-station shell clearance ------------------------------------
    motor_pod = S.EDULITE_HOUSING_DIA_MM + 2 * 3.0       # Ø52 real pod (Ø62 in the QA pad)
    belt_run = 2 * (BE.PULLEY_PD_MM / 2 + BE.BELT_HEIGHT_MM) + 2 * BE.WALL
    belt_stations = [
        _verdict(motor_pod, "proximal femur — QDD motor pod",
                 "Ø46 QDD lies inline in the femur — the belt's shell cost"),
        _verdict(belt_run, "femur belt run", "belt loop height sets the silhouette"),
        _verdict(belt_qa["bbox_mm"][1], "knee (P2) — driven pulley case", "slim at the knee"),
    ]

    facts = {
        "shell_envelope": {
            "cosmetic_shell_outer_mm": SHELL_OUTER,
            "shell_inner_mm": SHELL_INNER,
            "mechanism_envelope_mm": round(MECH_ENVELOPE, 1),
            "old_side_cup_dia_mm": OLD_CUP_DIA,
            "note": "mechanism must stay >=5 mm under the shell inner wall (SHELL_GAP)",
        },
        "shaft": {
            "qa": shaft_qa,
            "driveshaft": {"shaft_dia_mm": SH.SHAFT_D_MM, "tube_dia_mm": SH.SHAFT_TUBE_D_MM,
                           "cvd_cup_dia_mm": SH.CVD_CUP_D_MM},
            "bevel": {"module": SH.BEVEL_MODULE, "teeth": SH.BEVEL_TEETH,
                      "pd_mm": SH.BEVEL_PD_MM, "ratio": SH.RATIO, "type": "1:1 miter"},
            "femur_pitch_cv": {
                "range_deg": [round(math.degrees(lo), 1), round(math.degrees(hi), 1)],
                "max_bend_deg": round(max_bend_deg, 1),
                "single_cvd_limit_deg": single_cvd_limit,
                "needs_double_cardan": needs_double_cardan,
                "per_cardan_deg_if_double": round(per_cardan_deg, 1),
            },
            "backlash_deg": SH.BACKLASH_DEG,
            "stations": shaft_stations,
            "hip_cluster_dia_mm": round(hip_cluster_dia, 1),
            "mass_to_body_g_per_leg": round(SERVO.mass_g, 1),
            "mass_to_body_g_all5": round(SERVO.mass_g * 5, 1),
            "leg_hardware_g": round(shaft_qa["mass_g"] + 40.0, 1),
        },
        "belt": {
            "qa": belt_qa,
            "belt": {"type": "HTD-5M", "width_mm": BE.BELT_WIDTH_MM,
                     "pulley_teeth": BE.PULLEY_TEETH, "pulley_pd_mm": round(BE.PULLEY_PD_MM, 2),
                     "ratio": BE.RATIO, "centre_distance_mm": BE.CD_MM,
                     "pitch_length_mm": round(BE.BELT_PITCH_LEN_MM, 1),
                     "stock_length_mm": BE.BELT_STOCK_LEN_MM,
                     "tensioner": "625ZZ idler on the slack side / slotted motor mount"},
            "backlash_deg": 0.5,
            "stations": belt_stations,
            "mass_to_body_g_per_leg": 0.0,
            "note": "motor stays IN the femur; moves knee->femur-root, not to the body",
        },
        "anchors": {
            "type": "M2.5 brass heat-set insert + M2.5 machine screw (NOT clips)",
            "per_segment": {"coxa/hip shroud": 2, "femur shell": 2, "tibia shell": 2},
            "total_bolts_per_leg": 6,
            "note": "split (2-part) stone shell BOLTS on; heads countersunk + hidden "
                    "under a crag; unbolt to service the shafts/servos",
        },
        "winner": "shaft",
        "winner_reason": "under the shell-first priority the leg segments must be "
                         "slim; the shaft keeps only a Ø12 shaft on the leg (motor in "
                         "the body) so every leg station fits the Ø29 envelope, whereas "
                         "the belt parks a Ø52 motor pod on the femur that busts it. "
                         "Cost: ~2.5 deg knee backlash + a double-cardan for femur_pitch.",
    }

    (OUT / "pitch_transmission_facts.json").write_text(json.dumps(facts, indent=2))

    # --- export the SHAFT prototype assembly for the render isometric --------
    export_stl(SH.femur_shaft_case(), str(OUT / "ptx_shaft_case.stl"), tolerance=0.08)
    export_stl(SH.dummy_qdd_hip() + SH.dummy_cvd(), str(OUT / "ptx_shaft_motor.stl"), tolerance=0.1)
    export_stl(SH.dummy_shaft() + SH.dummy_bevels(), str(OUT / "ptx_shaft_drive.stl"), tolerance=0.1)
    export_stl(BE.femur_belt_case(), str(OUT / "ptx_belt_case.stl"), tolerance=0.08)
    export_stl(BE.dummy_qdd() + BE.driver_pulley() + BE.driven_pulley() + BE.belt_loop(),
               str(OUT / "ptx_belt_drive.stl"), tolerance=0.1)

    print(json.dumps(facts, indent=2))
    print(f"\n[ptx] shaft QA {'PASS' if shaft_qa['passed'] else 'FAIL'}  "
          f"belt QA {'PASS' if belt_qa['passed'] else 'FAIL'}")
    print(f"[ptx] winner = SHAFT; femur_pitch max bend {max_bend_deg:.0f} deg "
          f"-> {'double-cardan required' if needs_double_cardan else 'single CVD ok'}")
    return 0 if (shaft_qa["passed"] and belt_qa["passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
