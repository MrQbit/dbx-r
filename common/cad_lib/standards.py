"""Single source of truth for CAD fits, inserts, bearings, walls, and material
densities. Every CAD part imports from here; these constants are NEVER re-typed
elsewhere (ROBOTS_SPEC.md §4.5.2, Appendix A.4).

The one sanctioned human edit during the weekend is tuning a clearance value in
this file after printing the coupon plate (WEEKEND_RUNBOOK.md, Printing step 2),
followed by `make regen-cad`.
"""

from __future__ import annotations

# --- Fits (Appendix A.4): millimetres PER SIDE -----------------------------
FIT_PRESS_MM = 0.10   # press-fit (bearings, dowels)
FIT_SLIDE_MM = 0.20   # sliding fit (servo body drop-in)
FIT_LOOSE_MM = 0.35   # loose/clearance fit

# --- Threaded inserts (Appendix A.4) ---------------------------------------
# M3 brass heat-set boss: hole diameter x boss depth.
M3_INSERT_HOLE_DIA_MM = 4.0
M3_INSERT_BOSS_DEPTH_MM = 5.8
# Shell fasteners are M2 (self-tapping into printed bosses).
M2_INSERT_HOLE_DIA_MM = 1.7  # self-tap pilot for M2 into plastic

# --- Bearings --------------------------------------------------------------
# 625ZZ (5 x 16 x 5 mm) at passive pivots.
BEARING_625ZZ_ID_MM = 5.0
BEARING_625ZZ_OD_MM = 16.0
BEARING_625ZZ_W_MM = 5.0

# --- Walls & fillets (Appendix A.4 / §8) -----------------------------------
MIN_WALL_STRUCTURAL_MM = 2.4
MIN_WALL_COSMETIC_MM = 1.6
MIN_FILLET_LOADPATH_MM = 2.0  # R2 minimum on load paths

# --- Material densities (g/cm^3, §5) ---------------------------------------
DENSITY_PETG = 1.27
DENSITY_PLA = 1.24
DENSITY_TPU = 1.21

# --- Servo mass model (§5): STS3215 as a rigid box -------------------------
SERVO_MASS_G = 60.0
SERVO_BOX_L_MM = 45.2
SERVO_BOX_W_MM = 24.0
SERVO_BOX_H_MM = 32.0

# --- Print envelope (§8): Bambu P2S safe build volume ----------------------
PRINT_ENVELOPE_MM = (250.0, 250.0, 250.0)

# --- QA tolerances (§4.5 / §5) ---------------------------------------------
INTERFERENCE_TOL_MM = 0.05   # trimesh boolean interference check (G2)
COLLISION_PENETRATION_TOL_MM = 1.0  # settle test (G3)


def fit(kind: str) -> float:
    """Return the per-side clearance in mm for 'press' | 'slide' | 'loose'."""
    table = {"press": FIT_PRESS_MM, "slide": FIT_SLIDE_MM, "loose": FIT_LOOSE_MM}
    if kind not in table:
        raise KeyError(f"unknown fit {kind!r}; expected one of {sorted(table)}")
    return table[kind]


def density(material: str) -> float:
    """Return density (g/cm^3) for 'PETG' | 'PLA' | 'TPU'."""
    table = {"PETG": DENSITY_PETG, "PLA": DENSITY_PLA, "TPU": DENSITY_TPU}
    key = material.upper()
    if key not in table:
        raise KeyError(f"unknown material {material!r}; expected one of {sorted(table)}")
    return table[key]
