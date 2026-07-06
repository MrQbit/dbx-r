"""ROCKY-5 core tub — the central electronics compartment, qty 1 (§4).

A hollow tub that sits inside the 165 mm carapace, on top of the existing
core_plate, and hosts the robot's brain and power. It provides, as loose-fit
cavities driven straight from components.py (the single source of truth for
every box that goes into the robot):

  * Jetson tray      — 90 x 63 x 30 compact NVIDIA carrier, on 4 standoff bosses
                       (raised so its body clears the tub rim into the dome apex).
  * Battery bay      — 70 x 38 x 20 3S pack, a walled bay on the floor (low, for CoM).
  * IMU boss         — BNO055 pad (offset from centre; the battery bay owns it).
  * 40 mm fan mount  — floor exhaust vent + bolt bosses (draws air down past the
                       stack). See the packing note: only a 2-bolt (diagonal)
                       mount fits alongside the pack in this small dome.
  * Wiring pass-throughs — grommet holes through the floor.

Cylindrical (round) rather than pentagonal: at this small scale the 90 mm Jetson
and 70 mm pack nearly span the dome, and a round wall gives uniform clearance in
every direction (a pentagon's edges pinch floor features near the flats). Radius
is parametric off the carapace and clears the dome's narrowing inner wall at the
rim. Wall/floor ~3.4 mm (structural min-wall 2.4). Cavities are loose fit
(component box + CLR per side).
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Part

from common.cad_lib import standards as S
from common.cad_lib.components import JETSON, BATTERY, IMU, FAN
from common.cad_lib.part_meta import Insert, PartMeta
from common.params import load_params

_P = load_params("rocky")

# --- Tub shell (round, fits under the narrowing dome) -----------------------
# R=62 clears the dome inner wall (~65 mm at the 30 mm rim) with margin.
R_TUB = _P["dimensions"]["carapace_dia_mm"] / 2.0 - 20.5   # ~62 mm
WALL = 3.4
FLOOR = 3.4
H_TUB = 30.0
CLR = 1.0                                                  # loose cavity clearance per side

M3_HOLE = S.M3_INSERT_HOLE_DIA_MM + 2 * S.FIT_PRESS_MM
M2_HOLE = S.M2_INSERT_HOLE_DIA_MM


def _shell() -> Part:
    outer = Pos(0, 0, H_TUB / 2) * Cylinder(radius=R_TUB, height=H_TUB)
    inner = Pos(0, 0, FLOOR + (H_TUB + 2) / 2) * Cylinder(radius=R_TUB - WALL, height=H_TUB + 2)
    return outer - inner                                  # open-top tub, FLOOR-thick base


def core_tub() -> Part:
    tub = _shell()

    # --- Battery bay: a walled loose-fit bay on the floor (low, for CoM). ----
    bl, bw, bh = BATTERY.dims_mm                     # (70, 38, 20)
    in_x, in_y = bl + 2 * CLR, bw + 2 * CLR          # 72 (X) x 40 (Y)
    bay = (Pos(0, 0, FLOOR + bh / 2) *
           (Box(in_x + 2 * WALL, in_y + 2 * WALL, bh) - Box(in_x, in_y, bh + 2)))
    tub += bay

    # --- Jetson tray: 4 standoff bosses flanking the pack; lifted so the 90 mm
    # board clears the rim into the dome apex. -------------------------------
    jl, jw, jh = JETSON.dims_mm                      # (90, 63, 30)
    SH = 28.0
    jx, jy = 42.0, 25.0                              # ~84 x 50 mount pattern (clears the bay)
    for sx in (+jx, -jx):
        for sy in (+jy, -jy):
            tub += Pos(sx, sy, FLOOR + SH / 2) * Cylinder(radius=5.0, height=SH)
            tub -= Pos(sx, sy, FLOOR + SH - 8.0) * Cylinder(radius=M3_HOLE / 2, height=16.0)

    # --- 40 mm fan mount: floor exhaust vent + 2 diagonal bolt bosses in the
    # +Y free zone. The full 32 mm 4-bolt square doesn't fit beside the 70 mm
    # pack at this dome size (packing note) — a 2-bolt mount holds the 12 g fan.
    fy = 42.0
    tub -= Pos(0, fy, FLOOR / 2) * Cylinder(radius=9.0, height=FLOOR + 2)   # 18 mm exhaust vent
    for dx in (+16.0, -16.0):
        tub += Pos(dx, fy, FLOOR + 6.0) * Cylinder(radius=5.0, height=12.0)
        # Blind pilot: opens at the boss top, bottom stays above the floor.
        tub -= Pos(dx, fy, FLOOR + 8.0) * Cylinder(radius=M3_HOLE / 2, height=10.0)

    # --- IMU boss: BNO055 pad on the floor, -X of the pack. -----------------
    il, iw, ih = IMU.dims_mm                         # (20, 27, 4)
    imu_x = -45.0
    tub += Pos(imu_x, 0, FLOOR + 3.0) * Box(il + 2 * CLR, iw + 2 * CLR, 6.0)
    for dy in (+10.0, -10.0):                        # self-tap pilots, kept out of the floor
        tub -= Pos(imu_x, dy, FLOOR + 4.0) * Cylinder(radius=M2_HOLE / 2, height=6.0)

    # --- Wiring pass-throughs: grommet holes through the floor (-Y free zone).
    for px, py in ((0.0, -48.0), (28.0, -45.0), (-28.0, -45.0)):
        tub -= Pos(px, py, FLOOR / 2) * Cylinder(radius=4.0, height=FLOOR + 2)

    return tub


META = PartMeta(
    name="core_tub",
    material="PETG",
    qty=1,
    cosmetic=False,
    plate_group="rocky_structure",
    supports="tree",
    inserts=(Insert("m3_heatset", 4, "Jetson tray standoffs"),
             Insert("m2_selftap", 2, "IMU boss")),
    clearances={"jetson_tray": "loose", "battery_bay": "loose",
                "imu_boss": "slide", "fan_mount": "slide", "wiring": "loose"},
)


def part() -> Part:
    return core_tub()
