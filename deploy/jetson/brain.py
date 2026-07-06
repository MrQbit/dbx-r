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


# ----------------------------------------------------------------------------- #
class Policy:
    """ONNX locomotion policy (exported via export_policy.py)."""

    def __init__(self, onnx_path: str):
        self.sess = ort.InferenceSession(onnx_path,
                                         providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name

    def act(self, obs: np.ndarray) -> np.ndarray:
        return self.sess.run(None, {self.inp: obs[None].astype(np.float32)})[0][0]


class MotorBus:
    """Robstride / EduLite CAN bus. TODO: fill in the vendor CAN framing."""

    def __init__(self, channel="can0", n_joints=17):
        import can
        self.bus = can.interface.Bus(channel=channel, interface="socketcan")
        self.n = n_joints

    def read_state(self):
        # TODO: request + parse joint pos/vel frames -> arrays
        return np.zeros(self.n), np.zeros(self.n)

    def command(self, targets: np.ndarray):
        # TODO: pack MIT-mode position targets (kp/kd from params) into CAN frames
        pass


def locomotion_loop(cfg, stop):
    pol = Policy(cfg["policy"])
    try:
        bus = MotorBus(n_joints=cfg["n_joints"])
    except Exception as e:
        print(f"[locomotion] no CAN bus ({e}); running policy dry (no motor output)")
        bus = None
    dt = 1.0 / cfg["rate_hz"]
    default = np.array(cfg["default_pos"], dtype=np.float32)
    while not stop.is_set():
        t0 = time.time()
        # TODO: assemble obs in the SAME term order as the Isaac env's policy group
        # (base ang vel, projected gravity, velocity cmd, joint pos-default, joint vel,
        #  last action, height scan). For now: zeros -> policy holds default-ish.
        obs = np.zeros(cfg["obs_dim"], dtype=np.float32)
        action = pol.act(obs)
        targets = default + cfg["action_scale"] * action
        if bus:
            bus.command(targets)
        time.sleep(max(0, dt - (time.time() - t0)))


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
    """BDX droidspeak — beep/boop sound effects mapped from the intent/emotion."""
    import sys, os
    sys.path.insert(0, os.path.expanduser("~/duet"))
    from bdx.audio import droidspeak as ds
    import sounddevice as sd
    from rocky.audio.synth import SR

    def say(text):
        # simple sentiment -> emotion; real system maps a response policy's intent
        emo = "happy" if any(w in text.lower() for w in ("yes", "good", "amaze")) else \
              "alarmed" if any(w in text.lower() for w in ("no", "stop", "danger")) else "curious"
        a = ds.emote(emo, seed=len(text))
        sd.play(a, SR); sd.wait()
    return say


ROBOTS = {
    "rocky": dict(policy="rocky.onnx", n_joints=17, obs_dim=250, rate_hz=50,
                  action_scale=0.25, default_pos=[0.0, 0.6, 1.0] * 5 + [0.0, 0.0],
                  voice=rocky_voice),
    "bdx": dict(policy="bdx.onnx", n_joints=14, obs_dim=250, rate_hz=50,
                action_scale=0.25, default_pos=[0.0] * 14, voice=bdx_voice),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", choices=list(ROBOTS), required=True)
    ap.add_argument("--no-voice", action="store_true")
    args = ap.parse_args()
    cfg = ROBOTS[args.robot]
    stop = threading.Event()
    threads = [threading.Thread(target=locomotion_loop, args=(cfg, stop), daemon=True)]
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
