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
2. **Export the policy** on the DGX (in the Isaac container):
   ```
   isaaclab.sh -p deploy/jetson/export_policy.py \
     --checkpoint logs/rsl_rl/rocky_flat/<run>/model_5999.pt --out rocky.onnx
   ```
   (BDX: point at its run + `--out bdx.onnx`.)
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
- **Real & offline now:** ONNX policy inference, faster-whisper STT, both voices.
- **TODO (matches your wiring):** the CAN framing for Robstride/EduLite in
  `brain.py::MotorBus` (MIT-mode position frames), the exact policy observation term
  order (must mirror the Isaac env's `policy` obs group), and mic/speaker device ids.
- **Reconcile before powering motors:** the 48 V motor bus vs the 3S battery
  (`docs/BOM.md` §3 ⚠).
