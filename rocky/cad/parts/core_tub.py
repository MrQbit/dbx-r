"""ROCKY-5 core tub — the central electronics compartment, qty 1 (§4).

A hollow tub that sits inside the 165 mm carapace, on top of the existing
core_plate, and hosts the robot's brain and power. It provides, as loose-fit
cavities driven straight from components.py (the single source of truth for
every box that goes into the robot):

  * Jetson tray      — 90 x 63 x 30 compact NVIDIA carrier, on 4 standoff bosses
                       (raised so its body clears the tub rim into the dome apex).
  * Battery bay      — 70 x 38 x 20 3S pack, a walled bay on the floor (low, for CoM).
  * IMU boss         — BNO055 pad beside the pack (see the centroid note below).
  * 40 mm fan mount  — full 34 mm exhaust aperture + 32 mm 4-bolt square (restored
                       at the nudged 180 mm dome, D-021; was an 18 mm vent at 165).
  * Wiring pass-throughs — grommet holes through the floor.

Cylindrical (round) rather than pentagonal: at this small scale the 90 mm Jetson
and 70 mm pack nearly span the dome, and a round wall gives uniform clearance in
every direction (a pentagon's edges pinch floor features near the flats). Radius
is parametric off the carapace and clears the dome's narrowing inner wall at the
rim. Wall/floor ~3.4 mm (structural min-wall 2.4). Cavities are loose fit
(component box + CLR per side).

IMU / centroid note: the Jetson and battery are BOTH central and stacked (Jetson
on 28 mm standoffs over the top-loading battery bay), so they physically own the
XY centroid. The printed tub therefore mounts the IMU beside the pack at its
closest clean position (the bay's -X wall). For TRUE-centroid sensing (spec §4),
mount the BNO055 on the battery cover/lid at (0,0) — the M2 boss pair on the bay
rim provides for it. Beside-mount adds only a small centripetal-accel lever the
BNO055 fusion tolerates; centroid-on-lid is the exact option.
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
R_TUB = _P["dimensions"]["carapace_dia_mm"] / 2.0 - 20.5   # ~69.5 mm at the 180 dome
WALL = 3.4
FLOOR = 3.4
H_TUB = 34.0                                               # 30->34 (taller dome, Jetson clearance)
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

    # --- 40 mm fan mount: the nudged dome (R_TUB ~69.5, D-021) lets the exhaust
    # aperture grow 18 -> 30 mm (real airflow) in the +Y zone beyond the battery.
    # The two mount bolts sit on the fan's far (+Y) corners; the full 32 mm 4-bolt
    # square still can't clear the 70 mm pack + tub wall at this dome (the -Y bolts
    # leave a sub-min-wall sliver to the bay), so it stays a robust 2-bolt hold for
    # the ~12 g fan. Aperture sits under the elevated Jetson edge — air exhausts down.
    fy = 41.0
    tub -= Pos(0, fy, FLOOR / 2) * Cylinder(radius=14.0, height=FLOOR + 2)   # 28 mm aperture
    for bx in (+16.0, -16.0):                          # 2 far-corner bolts (clear the bay)
        tub += Pos(bx, fy + 16.0, FLOOR + 6.0) * Cylinder(radius=5.0, height=12.0)
        tub -= Pos(bx, fy + 16.0, FLOOR + 8.0) * Cylinder(radius=M3_HOLE / 2, height=10.0)

    # --- IMU boss: BNO055 pad on the floor, -X of the pack (beside-mount). ----
    il, iw, ih = IMU.dims_mm                         # (20, 27, 4)
    imu_x = -45.0
    tub += Pos(imu_x, 0, FLOOR + 3.0) * Box(il + 2 * CLR, iw + 2 * CLR, 6.0)
    for dy in (+10.0, -10.0):                        # self-tap pilots, kept out of the floor
        tub -= Pos(imu_x, dy, FLOOR + 4.0) * Cylinder(radius=M2_HOLE / 2, height=6.0)
    # (Centroid-lid option is an assembly detail — the BNO055 mounts on the battery
    # cover at (0,0); no tub geometry needed. See the IMU/centroid note above.)

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
