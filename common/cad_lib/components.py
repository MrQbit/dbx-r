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
    "led_channel",   # recessed strip/ring seat for hidden LEDs (no exposed emitter)
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
# NVIDIA stack retained (operator: "stay on Nvidia"): Orin Nano 8GB on a COMPACT
# carrier (reComputer J401-class ~90x63 vs the 100x80 dev kit) — keeps USB/Ethernet/
# CSI out of the box, no custom PCB, smaller footprint (D-015).
JETSON = Component("jetson_orin_nano", "compute", (90.0, 63.0, 30.0), 90.0, "tray",
                   ("usb", "eth", "i2c", "i2s", "gpio", "ribbon"), 4.0,
                   "NVIDIA Orin Nano 8GB on compact carrier; ribbon = CSI cam")
BATTERY = Component("battery_6s", "power", (85.0, 40.0, 25.0), 280.0, "bay",
                    ("xt60",), 2.0, "6S Li-ion pack for the 48V-class QDD motors (D-022)")
# QDD actuator: Robstride EduLite 05 (1.8/6 N·m, backdrivable, CAN, Ø41.5 PCD, 242 g).
# BDX-A uses it on every joint (BDX-R exactly, D-007). ROCKY-5 (D-042 LOCK) uses it on
# the 3 weight-bearing leg joints per limb — coxa_yaw, femur_pitch, KNEE — ALL mounted in
# the HIP CLUSTER inside the BODY (mass off the moving leg). The knee QDD drives the knee
# REMOTELY through the double-cardan driveshaft (see params knee.transmission) so no motor
# rides the femur/tibia.
SERVO = Component("robstride_edulite05", "actuator", (46.0, 46.0, 44.0), 242.0, "pocket",
                  ("canbus",), 2.0, "Robstride EduLite 05 QDD (1.8/6 N·m), CAN; Ø41.5 PCD; hip-cluster on ROCKY")
# ROCKY-5 tibia_roll actuator (D-042): the ONLY servo that rides the moving leg — a slim
# Feetech STS3215 EMBEDDED INLINE in the shank (45.2x24.7x35, TTL, 12V, position control,
# low load). Its 24.7-thin body slots INTO the shank; only the output horn crosses the
# roll axis. SERVO_PITCH (STS3250) is retained for reference but UNUSED on ROCKY under
# D-042 (the pitch/knee joints are the hip-cluster QDD above).
SERVO_PITCH = Component("feetech_sts3250", "actuator", (45.2, 24.7, 35.0), 74.0, "pocket",
                        ("ttl",), 2.0, "Feetech STS3250 slim serial servo (~4.9/2.4 N·m), TTL; UNUSED on ROCKY post-D-042")
SERVO_YR = Component("feetech_sts3215", "actuator", (45.2, 24.7, 35.0), 55.0, "pocket",
                     ("ttl",), 2.0, "Feetech STS3215 slim serial servo (~2.9 N·m stall), TTL; ROCKY tibia_roll (inline shank)")
# ROCKY-5 GRIP actuator (D-028): the 3 fingers per hand are low-load -> a small
# metal-gear micro servo (all 5 hands), NOT a leg QDD.
GRIP_SERVO = Component("grip_micro", "actuator", (22.8, 12.2, 28.5), 13.4, "pocket",
                       ("pwm",), 1.5, "MG90S-class micro servo; drives one 3-finger hand")
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

# Rocky manipulator hand (D-008, D-027, D-038): the REAL split assembly — now a SLIM
# 2+1 hand: slim palm with 2 fused primary fingers (the walking tip) + 1 opposing
# thumb + a hidden micro-servo drive crank. mass_g is the printed assembly (palm 66.6
# + thumb 7.8 + drive crank 2.0 ≈ 76 g @100% infill, per docs/reports/mass_rocky.md);
# the grip micro-servo is the separate grip servo. Far lighter than the old Ø108
# 3-finger crown hand (179 g).
GRIP_HAND = Component("grip_hand_2plus1", "actuator", (95.0, 60.0, 90.0), 76.4, "pocket",
                      (), 1.5, "2+1 grip hand (slim palm+2 primaries+thumb+drive crank), one per manipulator leg (D-038)")

# ROCKY-5 breathing crown (D-024): ONE micro-servo turns the scroll cam that
# drives all five carapace petals radially (slow ~0.25 Hz breathing only — a
# hobby servo cannot do the 3 mm @ 22 Hz speech ripple; that is LED-only).
BREATH_SERVO = Component("breath_servo_mg90s", "actuator", (22.8, 12.2, 28.5), 13.4, "pocket",
                         ("pwm",), 2.0, "MG90S-class micro metal-gear servo; drives the carapace scroll cam")

# ROCKY-5 hidden lighting (D-024) — Rocky has NO face, so light hides in the seams
# (Eridian-stone glow), never as an exposed emitter. WS2812 addressable (one data
# line + level shifter drives the whole chain; speech ripple modulates brightness).
SEAM_LED = Component("seam_led_ws2812", "sensor", (50.0, 5.0, 2.0), 3.0, "led_channel",
                     ("gpio",), 1.0, "WS2812 strip in the hub ring, backlights one crown petal seam")
GRILLE_LED = Component("grille_led_ws2812", "sensor", (30.0, 5.0, 2.0), 2.0, "led_channel",
                       ("gpio",), 1.0, "WS2812 backlight behind a skirt sound grille (reuses the grille aperture)")

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
    # 25 DOF (D-039): 20 limb joints (IDs 1-20 — 4 per limb: coxa_yaw, femur_pitch,
    # tibia_pitch/knee, tibia_roll) + 5 grip micro-servos (IDs 21-25). D-042 LOCK actuator
    # map: the 3 WEIGHT-BEARING joints per limb (coxa_yaw, femur_pitch, KNEE) are EduLite
    # QDD (SERVO) housed in the per-limb HIP CLUSTER inside the body — so their 242 g each
    # lumps into the BODY, NOT the moving leg (light distal leg, heavy body). Only
    # tibia_roll rides the leg — the slim STS3215 (SERVO_YR). Grips = GRIP_SERVO (D-028).
    for sid in range(1, 21):
        i = (sid - 1) // 4                           # limb index 0..4
        offset = ((sid - 1) % 4) + 1                 # 1=coxa_yaw 2=femur_pitch 3=tibia_pitch/knee 4=tibia_roll
        if offset in (1, 2, 3):                       # 3 QDD in the hip cluster (in the BODY)
            note = f"leg {i} {'coxa_yaw' if offset==1 else 'femur_pitch' if offset==2 else 'knee(remote driveshaft)'} QDD id {sid}"
            p.append(Placement(SERVO, f"rocky_hip_cluster_{i}", (0, 0, 0), qty=1, note=note))
        else:                                         # tibia_roll STS3215 rides the shank
            p.append(Placement(SERVO_YR, f"rocky_shank_{i}", (0, 0, 0), qty=1, note=f"leg {i} tibia_roll STS id {sid}"))
    for k, sid in enumerate(range(21, 26)):
        p.append(Placement(GRIP_SERVO, f"rocky_leg{k}_grip", (0, 0, 0), qty=1, note=f"grip servo id {sid}"))
    for leg in (0, 1, 2, 3, 4):
        p.append(Placement(GRIP_HAND, f"rocky_leg{leg}_hand", (0, 0, 0), note=f"2+1 hand leg {leg}"))
    # ROCKY HAS NO FACE, NO EYES, NO FRONT (D-006). Sensing is by sound (audio)
    # plus fully SYMMETRIC, hidden ToF — no camera, nothing that implies a heading.
    p += [
        Placement(AUDIO_DRIVER, "base_link", (0.0, 0.0, 10.0), note="behind skirt grilles"),
        Placement(AUDIO_AMP, "base_link", (20.0, 0.0, 20.0)),
        Placement(TOF, "base_link", (72.0, 0.0, 15.0), qty=5, note="hidden, one per 72deg sector"),
        Placement(FOOT_FSR, "rocky_foot", (0.0, 0.0, -9.0), qty=5, note="one per foot"),
        # Expressive TOP (D-024): breathing crown mechanism + hidden seam/grille glow.
        Placement(BREATH_SERVO, "carapace_hub", (0.0, 0.0, 50.0),
                  note="central scroll-cam servo; slow breathing only (not speech)"),
        Placement(SEAM_LED, "carapace_hub", (59.0, 0.0, 56.0), qty=5,
                  note="WS2812 arc per petal seam; glows as the petals breathe/on speech"),
        Placement(GRILLE_LED, "base_link", (72.0, 0.0, 10.0), qty=5,
                  note="WS2812 behind each of the 5 skirt sound grilles (hidden backlight)"),
    ]
    return p


def components_for(robot: str) -> list[Placement]:
    return {"bdx_a": bdx_a_components, "rocky": rocky_components}[robot]()


def charging_base_components() -> list[Placement]:
    """The dock: Qi transmitter + a barrel-jack input; robot parks its RX over it."""
    return [Placement(QI_TX, "charging_base", (0.0, 0.0, 6.0), note="TX coil under the pad")]


def integrated_mass_g(robot: str) -> float:
    return sum(pl.component.mass_g * pl.qty for pl in components_for(robot))
