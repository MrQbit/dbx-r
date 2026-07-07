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
M4_INSERT_HOLE_DIA_MM = 5.5  # M4 clearance (servo flange bolts)

# --- Robstride EduLite 05 mounting (datasheet, D-022) ----------------------
# Round QDD: Ø46 housing rim, Ø38.5 pilot, mounts on a Ø41.5 PCD bolt circle with
# M3+M4 at 30deg; output is a Ø24 collar around a Ø19 interface.
# RETAINED for BDX-A (adopted from BDX-R, Robstride, D-007) and for the ROCKY hand-
# mount bolt flange (tibia tip <-> grip_palm — a plain Ø41.5 PCD bolt circle, not a
# servo). ROCKY's 20 LEG joints moved off the QDD to the slim Feetech STS servos
# below (D-041), so the leg parts now cut STS_* pockets, not EDULITE_* cups.
EDULITE_HOUSING_DIA_MM = 46.0
EDULITE_PILOT_DIA_MM = 38.5
EDULITE_PCD_MM = 41.5
EDULITE_OUTPUT_COLLAR_DIA_MM = 24.0
EDULITE_OUTPUT_IFACE_DIA_MM = 19.0
EDULITE_HEIGHT_MM = 44.0

# --- Feetech STS3215 / STS3250 slim serial-bus servo (datasheet, D-041) -----
# ROCKY-5's 20 LEG joints (operator-approved "slim all 20"): a slim rectangular
# serial servo EMBEDDED INLINE in the links (body lies ALONG the strut, only the
# output horn crosses the joint) — replaces the fat external Ø54 EduLite cups so
# the legs get visibly slimmer. Both models share ONE body; only mass/torque differ:
#   * STS3250 — 10 PITCH joints (femur_pitch + knee/tibia_pitch, weight-bearing):
#               ~4.9 N·m stall / ~2.4 N·m sustained, 74 g.
#   * STS3215 — 10 YAW/ROLL joints (coxa_yaw + tibia_roll, low load): ~2.9 N·m, 55 g.
# Body 45.2 (L, along the link) x 24.7 (W, the SLIM lateral dim) x 35 (H, the output-
# axis direction; horn on the +H face). Position-controlled (NOT backdrivable), 12 V,
# TTL serial bus. Mount = 4 case-screw bosses + the output spline horn (the real
# double-support servo bracket: horn one side, a 625ZZ idler on the far side).
STS_BODY_L_MM = 45.2          # length — lies ALONG the link
STS_BODY_W_MM = 24.7          # SLIM width (lateral) — the whole slimming point
STS_BODY_H_MM = 35.0          # height = output-axis direction (horn on this face)
STS_OUTPUT_OFF_MM = 13.5      # output-spline offset from body centre along L (toward the joint)
STS_HORN_DIA_MM = 24.0        # output-horn disc Ø (the driven coupling caps this)
STS_HORN_PROTRUDE_MM = 6.0    # horn disc height proud of the case face
STS_SPLINE_DIA_MM = 8.0       # output spline / centre-screw Ø
STS_SCREW_HOLE_DIA_MM = 2.7   # M2.5 case-screw clearance
STS_SCREW_PITCH_L_MM = 35.0   # 4-screw rectangle spacing along L
STS_SCREW_PITCH_W_MM = 16.0   # ... and along W
STS3250_MASS_G = 74.0
STS3215_MASS_G = 55.0

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

# --- Servo box (§5): Robstride EduLite-05 as a rigid box -------------------
# ROCKY-5's actuator (D-013). Mirrors components.SERVO (52 x 52 x 34, 242 g) so
# the fit-test coupon slide-fit pocket matches the servo the robot actually uses
# (was the legacy STS3215 45.2 x 24 x 32 — D-020). components.py stays the single
# source of truth for CAD provisions; these constants only feed the coupon plate
# (D-019).
SERVO_MASS_G = 242.0
SERVO_BOX_L_MM = 52.0
SERVO_BOX_W_MM = 52.0
SERVO_BOX_H_MM = 34.0

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
