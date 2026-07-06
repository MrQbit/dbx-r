# PROJECT DUET — Purchasable Bill of Materials

What to **buy** and what to **build** for each robot. Prices are rough (USD, mid-2026),
sourced from Seeed/Waveshare/Robstride/Amazon-class vendors. Quantities are per robot.

> **Compute-carrier decision (the key "buy vs build" question):** you do **NOT** need
> a custom carrier. Use the **Orin Nano module + a compact off-the-shelf carrier**
> (Option A). A custom carrier (Option B) only buys you ~20 mm and costs a PCB spin —
> not worth it unless space gets truly critical.

---

## 1. Compute stack (NVIDIA — per operator)

### Option A — RECOMMENDED (buy, no build)
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| **NVIDIA Jetson Orin Nano 8 GB module** (900-13767-0040-000) | 1 | 250 | The SoM (SODIMM), ~70×45 mm |
| **Seeed reComputer J401 carrier** (or Waveshare Nano carrier) | 1 | 75 | ~90×63 mm; USB-A×4, GbE, 2×CSI, 40-pin GPIO, M.2 — **out of the box, no soldering** |
| NVMe M.2 2242/2280 SSD 256 GB | 1 | 30 | OS + models (XTTS ~1.8 GB, YourTTS 0.4 GB, Whisper) |
| Active heatsink+fan for Orin Nano | 1 | 20 | Included with some carriers |
| **Subtotal** | | **~375** | plug-and-play |

### Option B — custom carrier (build; only if you must save ~20 mm)
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| Orin Nano 8 GB module | 1 | 250 | same SoM |
| **Custom carrier PCB** (you design + fab) | 1 | 60 + design time | 4-layer, ~70×50 mm; breakout: 1×USB, 1×UART (servo bus), I2S (audio), I2C (IMU), CSI (cam), power. JLCPCB-class fab ~$30 + assembly. **Requires KiCad design + the Orin Nano design guide (NVIDIA DG-09502) + a 260-pin SODIMM connector.** |
| 260-pin SODIMM connector | 1 | 8 | for the module |
| **Subtotal** | | **~320 + your PCB effort** | smaller, but a real electronics project |

**Verdict:** Option A. The reComputer J401 gives you everything with zero PCB work; the
robot's carapace was already sized (D-015) around its ~90×63 footprint.

---

## 2. Actuators

### ROCKY-5 — Robstride **EduLite 05** (D-013)
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| **Robstride EduLite 05** QDD (6 N·m peak / 1.8 rated, 9:1, CAN) | **17** | 80 ea = **1360** | 15 leg (3/leg × 5) + 2 front grips. 48 V, ~242 g. **Verify mm dims from the datasheet before finalizing the leg pockets (spec assumes ~52×52×34).** |

### BDX-A — Robstride (higher torque; EduLite can NOT drive it — hips need 42 N·m)
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| **Robstride 01** QDD (17 N·m peak / 6 rated) — hips/knees | 8 | 140 ea = 1120 | Hip Yaw/Roll/Pitch + Knee ×2 |
| **Robstride 00** QDD (14 N·m peak / 5 rated) — ankles + head | 6 | 120 ea = 720 | 2 ankles + 4 head |
| **Subtotal BDX actuators** | 14 | **~1840** | matches BDX-R's 42/12 N·m spec |

---

## 3. Power (D-022 — resolved)
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| **6S Li-ion pack ≥3500 mAh + BMS, XT60** | 1 | 55 | **22.2 V nominal** — within EduLite's 15–60 V window (rated 48 V). Rocky's worst case is 0.8 N·m so it needs nowhere near 48 V; 6S is the practical pick (lighter/cheaper/safer than a 13S/48 V pack). For **max rated** servo performance, a **12–13S (44–48 V)** pack drops in. Fixes the old 3S/12 V under-volt. |
| Buck 5 V/5 A (to Jetson) | 1 | 12 | powers the carrier |
| INA219 current/voltage monitor | 1 | 5 | telemetry |
| E-stop switch (latching, 22 mm) | 1 | 10 | safety |

---

## 4. Sensing
| Part | Qty | ~$ | Notes | Both/robot |
|---|---|---|---|---|
| BNO055 IMU (9-DOF, I2C) | 1 | 25 | at centroid | both |
| CSI camera (IMX219, ribbon) | 1 | 15 | Jetson CSI | both |
| RealSense-class depth cam (optional, front) | 1 | 250 | perception v2 | both |
| VL53L0X ToF (I2C) | 3–5 | 5 ea | edge/obstacle | both |
| Foot FSR (16 mm) | 5 (Rocky) / 2 (BDX) | 3 ea | contact | both |

---

## 5. Audio
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| MAX98357A I2S amp | 1 | 6 | both robots |
| 40 mm full-range speaker (4–8 Ω) | 1 | 8 | Rocky chord/translated voice; BDX droidspeak |

Voice software (no extra hardware): **Rocky** = neural clone (YourTTS live + XTTS
cache) + Eridian chord bed; **BDX** = droidspeak beep/boop synth. STT = faster-whisper.

---

## 6. Wireless charging (both)
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| Qi 15 W RX coil + module (on robot) | 1 | 15 | in the belly (CAD provision) |
| Qi 15 W TX pad (dock) | 1 | 40 | the charging base |

---

## 7. Comms / wiring
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| Waveshare USB-CAN or CAN-FD adapter | 1 | 20 | Jetson ↔ Robstride/EduLite CAN bus |
| CAN wiring, JST/Dupont, silicone wire, heat-shrink | lot | 25 | daisy-chain the motors |

---

## 8. Structure / print
| Part | Qty | ~$ | Notes |
|---|---|---|---|
| PLA filament (carapace / body) | ~1 kg | 20 | Bambu P2S |
| TPU filament (feet, grips) | ~0.25 kg | 12 | external spool |
| M3 heat-set inserts + M3 bolts | lot | 15 | motor + panel mounts |
| Bearings (limb pivots, if used) | ~15 | 20 | optional |

---

## Rough per-robot totals
| | Compute | Actuators | Power+sense+audio+misc | **Total** |
|---|---|---|---|---|
| **ROCKY-5** (EduLite-05 ×17) | ~375 | ~1360 | ~250 | **~$2,000** |
| **BDX-A** (Robstride ×14) | ~375 | ~1840 | ~250 | **~$2,500** |

**Biggest open item to resolve before buying:** the **motor bus voltage** — the QDD
motors are 48 V-class but the spec's battery is 3S/12 V. Decide on a 6S+ pack or a
boost converter (⚠ in §3). Everything else is order-and-assemble.
