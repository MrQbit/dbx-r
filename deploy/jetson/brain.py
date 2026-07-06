#!/usr/bin/env python3
"""PROJECT DUET — on-robot brain (Jetson Orin Nano). One runtime, two robots.

Two concurrent loops:
  1. LOCOMOTION (control-rate, ~50 Hz): read IMU + joint states over CAN -> build the
     policy observation -> ONNX actor -> joint position targets -> CAN motor commands.
  2. INTERACTION (event-driven): mic -> faster-whisper STT -> a small response policy
     -> the robot's VOICE (Rocky = neural clone dual-track; BDX = droidspeak) -> speaker.

Hardware-specific bits (CAN framing for Robstride/EduLite, obs term ordering, mic/
speaker device ids) are marked TODO — they match your wiring. The software path
(policy inference + STT + TTS) is real and runs offline on the Jetson.

Usage:  python brain.py --robot rocky   |   python brain.py --robot bdx
"""
from __future__ import annotations

import argparse
import threading
import time

import numpy as np
import onnxruntime as ort

# Shared expressive state (thread-safe enough for a single writer). The interaction
# loop sets the emotion; the locomotion + expressive loops read it. This is Disney's
# architecture: the RL policy owns the gait; emotion drives ADDITIVE head/gaze offsets
# + ears + eyes ON TOP — no retrain (the head joints are already in the 14-DOF policy;
# we just add a small offset to their targets at runtime).
_STATE = {"emotion": "neutral"}


# ----------------------------------------------------------------------------- #
class Policy:
    """ONNX locomotion policy (exported via export_policy.py)."""

    def __init__(self, onnx_path: str):
        self.sess = ort.InferenceSession(onnx_path,
                                         providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name

    def act(self, obs: np.ndarray) -> np.ndarray:
        return self.sess.run(None, {self.inp: obs[None].astype(np.float32)})[0][0]


# --- Robstride/EduLite MIT-mode CAN framing ---------------------------------
# QDD motors (Robstride RS/EduLite) accept an 8-byte MIT control frame packing a
# position target + feed-forward vel/kp/kd/torque. Ranges are MOTOR-SPECIFIC —
# VERIFY against the EduLite-05 / Robstride manual before energising (D-025).
P_MIN, P_MAX = -12.5, 12.5      # rad
V_MIN, V_MAX = -44.0, 44.0      # rad/s
KP_MIN, KP_MAX = 0.0, 500.0
KD_MIN, KD_MAX = 0.0, 5.0
T_MIN, T_MAX = -17.0, 17.0      # N·m (EduLite peak 6; keep headroom in the range)


def _f2u(x, lo, hi, bits):
    x = min(max(x, lo), hi)
    return int((x - lo) * ((1 << bits) - 1) / (hi - lo))


def _u2f(u, lo, hi, bits):
    return u * (hi - lo) / ((1 << bits) - 1) + lo


class MotorBus:
    """Robstride / EduLite CAN bus, MIT position mode. can_id = motor id (params
    servo_ids). kp/kd default to the params PD gains (40 / 2)."""

    def __init__(self, channel="can0", n_joints=17, ids=None, kp=40.0, kd=2.0):
        import can
        self.can = can
        self.bus = can.interface.Bus(channel=channel, interface="socketcan")
        self.n = n_joints
        self.ids = ids or list(range(1, n_joints + 1))
        self.kp, self.kd = kp, kd
        self.pos = np.zeros(n_joints)
        self.vel = np.zeros(n_joints)

    def _frame(self, pos):
        p = _f2u(pos, P_MIN, P_MAX, 16)
        v = _f2u(0.0, V_MIN, V_MAX, 12)
        kp = _f2u(self.kp, KP_MIN, KP_MAX, 12)
        kd = _f2u(self.kd, KD_MIN, KD_MAX, 12)
        t = _f2u(0.0, T_MIN, T_MAX, 12)
        return bytes([p >> 8, p & 0xFF, v >> 4, ((v & 0xF) << 4) | (kp >> 8),
                      kp & 0xFF, kd >> 4, ((kd & 0xF) << 4) | (t >> 8), t & 0xFF])

    def command(self, targets: np.ndarray):
        for i, mid in enumerate(self.ids):
            self.bus.send(self.can.Message(arbitration_id=mid, is_extended_id=False,
                                           data=self._frame(float(targets[i]))))

    def read_state(self):
        # Non-blocking drain of feedback frames (id | pos16 | vel12 | torque12).
        while True:
            msg = self.bus.recv(timeout=0.0)
            if msg is None:
                break
            mid = msg.arbitration_id & 0xFF
            if mid in self.ids and len(msg.data) >= 5:
                j = self.ids.index(mid)
                d = msg.data
                self.pos[j] = _u2f((d[0] << 8) | d[1], P_MIN, P_MAX, 16)
                self.vel[j] = _u2f((d[2] << 4) | (d[3] >> 4), V_MIN, V_MAX, 12)
        return self.pos, self.vel


class IMU:
    """BNO055 over I2C: body angular velocity (rad/s) + gravity direction (unit)."""

    def __init__(self):
        import board, adafruit_bno055
        self.s = adafruit_bno055.BNO055_I2C(board.I2C())

    def read(self):
        gx, gy, gz = self.s.gyro or (0, 0, 0)
        grav = self.s.gravity or (0, 0, -9.81)
        g = np.array(grav, dtype=np.float32)
        n = np.linalg.norm(g) or 1.0
        return np.array([gx, gy, gz], dtype=np.float32), g / n     # ang_vel, projected_gravity


def build_obs(spec, imu_data, cmd, joint_pos, default, joint_vel, last_action, scan):
    """Assemble the policy obs in the EXACT term order the env used. `spec` is the
    ordered list of (name, dim) dumped by export_policy.py (obs_spec.json) — the ONE
    source of truth; the fallbacks below only apply if a term isn't wired yet."""
    ang_vel, proj_g = imu_data
    src = {
        "base_ang_vel": ang_vel,
        "projected_gravity": proj_g,
        "velocity_commands": np.asarray(cmd, dtype=np.float32),
        "joint_pos": (joint_pos - default),        # relative to default (Isaac convention)
        "joint_pos_rel": (joint_pos - default),
        "joint_vel": joint_vel,
        "joint_vel_rel": joint_vel,
        "actions": last_action,
        "height_scan": scan,
    }
    parts = []
    for name, dim in spec:
        v = src.get(name)
        parts.append(np.asarray(v, dtype=np.float32) if v is not None else np.zeros(dim, np.float32))
    return np.concatenate(parts)


def locomotion_loop(cfg, stop):
    import json, os
    pol = Policy(cfg["policy"])
    # obs_spec.json (dumped next to the .onnx by export_policy.py) pins the exact term
    # order + dims so the on-robot obs matches training. Falls back to the canonical
    # Isaac velocity order if absent (VERIFY against the env if you rely on it).
    spec_path = cfg["policy"].replace(".onnx", "_obs_spec.json")
    if os.path.exists(spec_path):
        spec = [(t["name"], t["dim"]) for t in json.load(open(spec_path))["terms"]]
    else:
        n = cfg["n_joints"]
        spec = [("base_ang_vel", 3), ("projected_gravity", 3), ("velocity_commands", 3),
                ("joint_pos", n), ("joint_vel", n), ("actions", n),
                ("height_scan", cfg["obs_dim"] - (9 + 3 * n))]
        print(f"[locomotion] no obs_spec.json — using canonical order; VERIFY vs env")
    try:
        bus = MotorBus(n_joints=cfg["n_joints"], kp=cfg.get("kp", 40.0), kd=cfg.get("kd", 2.0))
    except Exception as e:
        print(f"[locomotion] no CAN bus ({e}); running policy dry (no motor output)")
        bus = None
    try:
        imu = IMU()
    except Exception as e:
        print(f"[locomotion] no IMU ({e}); using zeros")
        imu = None
    dt = 1.0 / cfg["rate_hz"]
    default = np.array(cfg["default_pos"], dtype=np.float32)
    n = cfg["n_joints"]
    last_action = np.zeros(n, dtype=np.float32)
    scan_dim = next((d for nm, d in spec if nm == "height_scan"), 0)
    while not stop.is_set():
        t0 = time.time()
        jp, jv = bus.read_state() if bus else (default.copy(), np.zeros(n, np.float32))
        imu_data = imu.read() if imu else (np.zeros(3, np.float32), np.array([0, 0, -1], np.float32))
        cmd = _STATE.get("cmd", (0.0, 0.0, 0.0))          # vx, vy, wz from the interaction layer
        obs = build_obs(spec, imu_data, cmd, jp, default, jv, last_action,
                        np.zeros(scan_dim, np.float32))
        action = pol.act(obs)
        last_action = action
        targets = default + cfg["action_scale"] * action
        # EXPRESSIVE OFFSET (Disney's method): add emotion-driven head pitch/yaw ON TOP
        # of the policy's head-joint targets. Additive, tiny, runtime -> no retrain.
        hi = cfg.get("head_idx")
        if hi:
            from bdx import persona
            off = persona.HEAD_OFFSET.get(_STATE["emotion"], persona.HEAD_OFFSET["neutral"])
            targets[hi["pitch"]] += off["head_pitch"]
            targets[hi["yaw"]] += off["head_yaw"]
        if bus:
            bus.command(targets)
        time.sleep(max(0, dt - (time.time() - t0)))


def expressive_loop(cfg, stop):
    """BDX only: continuously drive the 2 ears + LED eyes from the current emotion
    (always animating — 'if BDX stops moving it stops working'). Decoupled channel."""
    from bdx import persona
    while not stop.is_set():
        emo = _STATE["emotion"]
        l, r = persona.ear_pose(emo, time.time())          # -> 2 ear-servo targets (rad)
        eyes = persona.eye_state(emo)                      # -> LED color/brightness
        # TODO: ear_bus.command(l, r); led.set(**eyes)
        time.sleep(0.03)


# ----------------------------------------------------------------------------- #
def interaction_loop(cfg, stop):
    from faster_whisper import WhisperModel
    stt = WhisperModel("tiny.en", device="cuda", compute_type="int8")
    speak = cfg["voice"]()                       # robot-specific voice callable
    import sounddevice as sd
    print("[interaction] listening (say something)...")
    while not stop.is_set():
        # TODO: VAD-gated capture; here a fixed 4s window
        audio = sd.rec(int(4 * 16000), samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        segs, _ = stt.transcribe(audio[:, 0], language="en")
        text = " ".join(s.text for s in segs).strip()
        if text:
            print(f"[heard] {text}")
            speak(text)                          # -> speaker


# --- robot voices ------------------------------------------------------------ #
def rocky_voice():
    """Neural Rocky clone (YourTTS live + XTTS cache) + Eridian chord bed."""
    import sys, os, tempfile
    sys.path.insert(0, os.path.expanduser("~/duet"))
    from rocky.audio import neural_tts as nt
    import sounddevice as sd, soundfile as sf

    def say(text):
        eng = nt.speak(text, tempfile.mktemp(suffix=".wav"))     # transform + clone (+cache)
        dual = nt.dual_track(eng, tempfile.mktemp(suffix=".wav"))
        a, sr = sf.read(dual)
        sd.play(a, sr); sd.wait()
    return say


def bdx_voice():
    """BDX droidspeak — beep/boop sound effects + the 2-ear/LED-eye EXPRESSIVE
    channel (bdx.persona), all driven by the same emotion. Ears/eyes are decoupled
    from the locomotion policy (no retrain — see D-017)."""
    import sys, os, time as _t
    sys.path.insert(0, os.path.expanduser("~/duet"))
    from bdx.audio import droidspeak as ds
    from bdx import persona
    import sounddevice as sd
    from rocky.audio.synth import SR

    def _drive_ears_eyes(emo, dur):
        # TODO: 2 small ear servos (CAN/PWM) + LED eye strip. Here we just compute
        # the targets so the wiring is a drop-in (bdx.persona is the source of truth).
        eyes = persona.eye_state(emo)                      # -> LED color/brightness
        t0 = _t.time()
        while _t.time() - t0 < dur:
            l, r = persona.ear_pose(emo, _t.time())        # -> 2 ear-servo targets (rad)
            # ear_bus.command(l, r); led.set(**eyes)
            _t.sleep(0.03)

    def say(text):
        emo = "happy" if any(w in text.lower() for w in ("yes", "good", "amaze")) else \
              "alarmed" if any(w in text.lower() for w in ("no", "stop", "danger")) else "curious"
        _STATE["emotion"] = emo               # feeds the locomotion head-offset + ears/eyes
        a = ds.emote(emo, seed=len(text))
        sd.play(a, SR); sd.wait()
        _STATE["emotion"] = "neutral"          # settle back
    return say


ROBOTS = {
    "rocky": dict(policy="rocky.onnx", n_joints=17, obs_dim=250, rate_hz=50,
                  action_scale=0.25, default_pos=[0.0, 0.6, 1.0] * 5 + [0.0, 0.0],
                  voice=rocky_voice),
    # head_idx: action indices of the head joints for the expressive offset. TODO:
    # verify against the URDF joint order (Neck_Pitch, Head_Pitch, Head_Yaw, Head_Roll).
    "bdx": dict(policy="bdx.onnx", n_joints=14, obs_dim=250, rate_hz=50,
                action_scale=0.25, default_pos=[0.0] * 14, voice=bdx_voice,
                head_idx={"pitch": 11, "yaw": 12}, expressive=True),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", choices=list(ROBOTS), required=True)
    ap.add_argument("--no-voice", action="store_true")
    args = ap.parse_args()
    cfg = ROBOTS[args.robot]
    stop = threading.Event()
    threads = [threading.Thread(target=locomotion_loop, args=(cfg, stop), daemon=True)]
    if cfg.get("expressive"):                # BDX: continuous ear/eye animation
        threads.append(threading.Thread(target=expressive_loop, args=(cfg, stop), daemon=True))
    if not args.no_voice:
        threads.append(threading.Thread(target=interaction_loop, args=(cfg, stop), daemon=True))
    for t in threads:
        t.start()
    print(f"[brain] {args.robot} running (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
