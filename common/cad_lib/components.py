"""Physical component registry — the single source of truth for everything that
goes INTO the robots (ROBOTS_SPEC.md §3.5, §4, + integration requirements from
the operator: wiring, cooling, sensors, cameras, wireless charging).

Every real component is declared once with its bounding box, mass, the routing/
provision it needs (pocket, tray, vent, cable channel, coil pocket, ...), and
where it lives. Two things read this registry:

  * CAD  — generates the mounts/slots/channels/vents that host each component
           (so the printed robot actually fits the hardware you source).
  * Description — lumps component masses into the right links, so the trained
           robot's inertias match the built robot ("train what you print").

Dimensions are nominal for easily-sourced modules; tune a number here and both
the CAD provision and the description mass update together. Qi charging is 15 W
(operator decision), active 40 mm fan cooling, full sensor provisioning.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Provision kinds the CAD layer knows how to realise around a component.
PROVISIONS = {
    "tray",          # bolt-down board tray with standoffs + connector clearance
    "pocket",        # captive box pocket (slide/loose fit)
    "bay",           # large compartment (battery) with foam tolerance
    "coil_pocket",   # shallow round pocket for a wireless coil + alignment ring
    "vent",          # louvered opening for airflow
    "fan_mount",     # square fan bolt pattern + finger guard
    "cable_channel", # routed conduit / grommet pass-through
    "window",        # sensor aperture (camera / ToF line of sight)
    "flush_pad",     # surface pad flush-mounted (foot FSR)
    "boss",          # threaded-insert boss cluster
}


@dataclass(frozen=True)
class Component:
    name: str
    category: str                 # compute|power|actuator|sensor|cooling|charging|audio|connector
    dims_mm: tuple[float, float, float]
    mass_g: float
    provision: str                # one of PROVISIONS
    connectors: tuple[str, ...] = ()   # usb|i2c|i2s|gpio|xt30|barrel|ribbon|dupont
    clearance_mm: float = 2.0     # extra keep-out around the box (wiring/airflow)
    note: str = ""

    def __post_init__(self):
        assert self.provision in PROVISIONS, f"bad provision {self.provision!r}"


@dataclass(frozen=True)
class Placement:
    component: Component
    host: str                     # which CAD part/shell hosts it
    pos_mm: tuple[float, float, float]   # nominal position in the robot base frame
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)
    qty: int = 1
    note: str = ""


# --------------------------------------------------------------------------- #
# Shared component catalogue (nominal sourceable modules)
# --------------------------------------------------------------------------- #
JETSON = Component("jetson_orin_nano", "compute", (100.0, 80.0, 30.0), 100.0, "tray",
                   ("usb", "barrel", "i2c", "i2s", "gpio", "ribbon"), 4.0,
                   "Orin Nano 8GB on compact carrier; ribbon = CSI cam")
BATTERY = Component("battery_3s", "power", (70.0, 38.0, 20.0), 150.0, "bay",
                    ("xt30",), 2.0, "3S Li-ion >=2600 mAh + BMS (params §3.2)")
# Shared actuator across BOTH robots (D-010): Robstride QDD motor — proven on
# BDX-R, reused on ROCKY-5 to simplify sourcing/firmware/wiring/spares. Much
# heavier than a hobby servo (~230 g vs 60 g) — drives Rocky's mass/size up.
SERVO = Component("robstride_rs00", "actuator", (48.0, 48.0, 32.0), 230.0, "pocket",
                  ("canbus",), 2.0, "Robstride QDD motor (RS00-class), CAN bus")
BUCK = Component("buck_5v5a", "power", (43.0, 21.0, 14.0), 15.0, "tray",
                 ("dupont",), 2.0, "5V/5A to Jetson barrel")
INA219 = Component("ina219", "sensor", (26.0, 20.0, 4.0), 5.0, "tray",
                   ("i2c",), 1.5, "servo-rail current monitor")
IMU = Component("bno055", "sensor", (20.0, 27.0, 4.0), 3.0, "boss",
                ("i2c",), 1.0, "IMU at CoM/centroid, +X forward (params §3.5)")
FAN = Component("fan_40mm", "cooling", (40.0, 40.0, 10.0), 12.0, "fan_mount",
                ("dupont",), 3.0, "active Jetson cooling (operator decision)")
BUS_ADAPTER = Component("waveshare_bus_adapter", "connector", (50.0, 30.0, 15.0), 20.0, "tray",
                        ("usb", "dupont"), 2.0, "USB->TTL servo bus, /dev/ttyUSB0")
ESTOP = Component("estop_switch", "power", (22.0, 22.0, 28.0), 15.0, "pocket",
                  ("xt30",), 2.0, "physical servo-rail cutoff; must be reachable")

# Wireless charging (Qi 15 W) — operator decision.
QI_RX = Component("qi_rx_15w", "charging", (55.0, 40.0, 5.0), 15.0, "coil_pocket",
                  ("dupont",), 2.0, "Qi 15W receiver coil+PCB on robot underside")
QI_TX = Component("qi_tx_15w", "charging", (60.0, 60.0, 12.0), 40.0, "coil_pocket",
                  ("barrel",), 3.0, "Qi 15W transmitter housed in the charging base")

# Sensors / cameras (physical provisions; vision is a v1 software non-goal).
DEPTH_CAM = Component("depth_cam", "sensor", (90.0, 25.0, 25.0), 72.0, "window",
                      ("usb",), 3.0, "RealSense-class front depth camera")
CSI_CAM = Component("csi_cam", "sensor", (25.0, 24.0, 9.0), 5.0, "window",
                    ("ribbon",), 2.0, "Jetson CSI ribbon camera")
TOF = Component("tof_vl53l0x", "sensor", (13.0, 11.0, 3.0), 2.0, "window",
                ("i2c",), 1.0, "ToF distance sensor")
FOOT_FSR = Component("foot_fsr", "sensor", (16.0, 16.0, 1.5), 2.0, "flush_pad",
                     ("dupont",), 0.5, "foot contact / force pad under TPU sole")

# Rocky audio (§4, §7).
AUDIO_DRIVER = Component("driver_40mm", "audio", (40.0, 40.0, 22.0), 25.0, "vent",
                         ("dupont",), 3.0, "40mm full-range behind skirt grilles")
AUDIO_AMP = Component("max98357a", "audio", (17.0, 13.0, 3.0), 2.0, "tray",
                      ("i2s",), 1.5, "I2S mono amp")

# Rocky front-leg manipulator (D-008): 3 triangular stony fingers + grip linkage.
GRIP_HAND = Component("grip_hand_3finger", "actuator", (46.0, 46.0, 26.0), 30.0, "pocket",
                      (), 1.5, "3-finger grip hand-foot on the 2 front legs")

# BDX-A head expression details (movie-accuracy — backlit eyes + antennae).
EYE_LED = Component("eye_led", "sensor", (12.0, 12.0, 6.0), 4.0, "window",
                    ("gpio",), 1.0, "backlit WS2812 behind a translucent eye lens")
ANTENNA = Component("antenna", "sensor", (4.0, 4.0, 90.0), 6.0, "boss",
                    ("gpio",), 1.0, "signature BD antenna; hinged (v2: 1 servo to flick)")


def _common_core(robot_base: str, torso_z: float) -> list[Placement]:
    """Compute/power/cooling/charging common to both robots, hosted in the core."""
    return [
        Placement(JETSON, robot_base, (0.0, 0.0, torso_z), note="tray over vents"),
        Placement(FAN, robot_base, (0.0, 0.0, torso_z + 0.0), note="draws over Jetson heatsink"),
        Placement(BATTERY, robot_base, (0.0, 0.0, torso_z - 25.0), note="low for CoM"),
        Placement(BUCK, robot_base, (35.0, 0.0, torso_z), note="power tray"),
        Placement(INA219, robot_base, (35.0, 20.0, torso_z)),
        Placement(BUS_ADAPTER, robot_base, (-35.0, 0.0, torso_z)),
        Placement(ESTOP, robot_base, (0.0, -40.0, torso_z), note="rear, reachable"),
        Placement(IMU, robot_base, (0.0, 0.0, torso_z - 10.0), note="near CoM"),
        Placement(QI_RX, robot_base, (0.0, 0.0, torso_z - 35.0), rpy=(0, 0, 0),
                  note="underside coil, faces down to the dock"),
    ]


# --------------------------------------------------------------------------- #
# Per-robot placements
# --------------------------------------------------------------------------- #
def bdx_a_components() -> list[Placement]:
    p = _common_core("base_link", torso_z=60.0)
    # 14 servos = BDX-R exactly (D-007): 10 legs (IDs 1-10) + 4-DOF head
    # (Neck_Pitch/Head_Pitch/Head_Yaw/Head_Roll, IDs 11-14). Robstride actuators.
    for sid in range(1, 15):
        host = "bdx_a_head" if sid >= 11 else f"bdx_a_joint_{sid}"
        p.append(Placement(SERVO, host, (0, 0, 0), qty=1, note=f"servo id {sid}"))
    # BDX has a face: eyes + cameras + antennae live in the actuated head.
    p += [
        Placement(EYE_LED, "bdx_a_head", (30.0, 18.0, 0.0), qty=2, note="two backlit eye lenses"),
        Placement(DEPTH_CAM, "bdx_a_head", (32.0, 0.0, -6.0), note="visor, forward depth"),
        Placement(CSI_CAM, "bdx_a_head", (33.0, 0.0, -18.0), note="secondary low cam"),
        Placement(ANTENNA, "bdx_a_head", (-10.0, 20.0, 25.0), qty=2, note="signature BD antennae"),
        Placement(TOF, "base_link", (35.0, 30.0, 70.0), qty=2, note="front-corner obstacle"),
        Placement(FOOT_FSR, "bdx_a_foot", (15.0, 0.0, -10.0), qty=2, note="one per foot"),
    ]
    return p


def rocky_components() -> list[Placement]:
    p = _common_core("base_link", torso_z=30.0)
    # 17 servos: 15 limb joints (IDs 1-15) + 2 front-leg grips (IDs 16-17, D-008).
    for sid in range(1, 18):
        host = "rocky_grip" if sid >= 16 else f"rocky_joint_{sid}"
        p.append(Placement(SERVO, host, (0, 0, 0), qty=1, note=f"servo id {sid}"))
    for leg in (1, 4):
        p.append(Placement(GRIP_HAND, f"rocky_leg{leg}_hand", (0, 0, 0), note=f"3-finger hand leg {leg}"))
    # ROCKY HAS NO FACE, NO EYES, NO FRONT (D-006). Sensing is by sound (audio)
    # plus fully SYMMETRIC, hidden ToF — no camera, nothing that implies a heading.
    p += [
        Placement(AUDIO_DRIVER, "base_link", (0.0, 0.0, 10.0), note="behind skirt grilles"),
        Placement(AUDIO_AMP, "base_link", (20.0, 0.0, 20.0)),
        Placement(TOF, "base_link", (72.0, 0.0, 15.0), qty=5, note="hidden, one per 72deg sector"),
        Placement(FOOT_FSR, "rocky_foot", (0.0, 0.0, -9.0), qty=5, note="one per foot"),
    ]
    return p


def components_for(robot: str) -> list[Placement]:
    return {"bdx_a": bdx_a_components, "rocky": rocky_components}[robot]()


def charging_base_components() -> list[Placement]:
    """The dock: Qi transmitter + a barrel-jack input; robot parks its RX over it."""
    return [Placement(QI_TX, "charging_base", (0.0, 0.0, 6.0), note="TX coil under the pad")]


def integrated_mass_g(robot: str) -> float:
    return sum(pl.component.mass_g * pl.qty for pl in components_for(robot))
