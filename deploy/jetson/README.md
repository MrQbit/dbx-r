# PROJECT DUET — Jetson deployment

Run each robot's brain on its **NVIDIA Jetson Orin Nano** (see `docs/BOM.md` for the
compute stack). The trained RL policy runs as ONNX; STT + voice run offline.

## Pipeline

```
[DGX]  train (Isaac Lab) ──▶ export_policy.py ──▶ rocky.onnx / bdx.onnx
                                                        │  scp
                                                        ▼
[Jetson]  setup_common.sh ─▶ setup_{rocky,bdx}.sh ─▶ brain.py --robot <r>
                                                        │
              ┌─────────────────────────────────────────┴───────────────┐
        LOCOMOTION loop (~50 Hz)                    INTERACTION loop
        IMU+CAN ▶ obs ▶ ONNX ▶ CAN motors     mic ▶ faster-whisper ▶ voice ▶ speaker
```

## Steps
1. **Flash** JetPack 6 (Orin Nano), boot, `sudo` enabled.
2. **Export the policy + obs spec** on the DGX (in the Isaac container):
   ```
   isaaclab.sh -p deploy/jetson/export_policy.py \
     --checkpoint logs/rsl_rl/rocky_flat/<run>/model_5999.pt --out rocky.onnx
   isaaclab.sh -p deploy/jetson/dump_obs_spec.py \
     --task Duet-Rocky-Imitate-Rough-v0 --out rocky_obs_spec.json
   ```
   The `*_obs_spec.json` pins the **exact observation term order + dims** so `brain.py`
   builds the on-robot obs identically to training — the #1 "runs but walks wrong"
   guard. Copy it next to the `.onnx` on the Jetson. (BDX: its run + task, `bdx.*`.)
3. **On the Jetson:**
   ```
   ./setup_common.sh
   ./setup_rocky.sh          # or ./setup_bdx.sh
   ```
4. **Copy assets** from the repo to `~/duet/` (the setup scripts print the exact
   paths): the robot's code, the exported `.onnx`, and — for Rocky — the reference
   audio + prebuilt `reference/voice_cache/`.
5. **Run:** `python ~/duet/deploy/jetson/brain.py --robot rocky` (or `bdx`).

## Voice per robot
- **ROCKY-5** — translated neural clone: YourTTS live (faster-than-real-time on Orin
  Nano) + XTTS phrase cache (instant common lines, built offline on the DGX) + the
  quiet Eridian chord bed. Text is Rocky-transformed first.
- **BDX-A** — droidspeak: a pure-numpy beep/boop synth with an emotion map (no model
  download), triggered by the interaction loop's intent.

## What's real vs TODO
- **Real & offline now:** ONNX policy inference, faster-whisper STT, both voices,
  **MIT-mode CAN framing** (`MotorBus`, D-025), **BNO055 IMU** read, and the
  **obs vector assembled from `*_obs_spec.json`** (exact trained order).
- **VERIFY before energising:** the MIT frame ranges (`P/V/KP/KD/T_*` in `brain.py`)
  are motor-generic — confirm against the **EduLite-05 / Robstride manual**; and the
  CAN `arbitration_id` = motor id mapping (params `servo_ids`).
- **TODO (your wiring):** mic/speaker device ids; VAD gating; the velocity-command
  source (`_STATE["cmd"]`) if you want voice-driven walking.
- **Power:** 6S pack (`docs/BOM.md` §3, D-022) — resolved.
