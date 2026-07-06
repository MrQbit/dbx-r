"""BDX-A persona / expressive layer — the 2 EAR (antenna) actuators + emotion.

The real Disney BDX and Kayden Knapik's BDX-R are 16 DOF: 14 locomotion + 2 ear
actuators. The ears are a DECOUPLED expressive channel — driven here by emotion,
NOT by the locomotion RL policy (they carry ~no load and are unrelated to gait, so
adding them needs no retrain). This is how Disney gives BDX "personality": the
locomotion policy owns the gait; the ears (+ head/gaze offsets, LED eyes) are
animated on top.

Ear parts are adopted from the upstream BDX-R meshes (Left_Ear / Right_Ear /
Right_Ear_Motor). Drive with two small low-load servos (see docs/BOM.md).
"""

from __future__ import annotations

import math

# Ear joint sign convention: + = perk up/forward, - = droop back. Range ~[-0.6, 0.9] rad.
EAR_UP = 0.8
EAR_DOWN = -0.5


def ear_pose(emotion: str, t: float) -> tuple[float, float]:
    """(left_ear, right_ear) target angles (rad) at time t for the given emotion.
    Symmetric by default; alarmed/curious add asymmetry + motion (the 'alive' tell)."""
    if emotion == "happy" or emotion == "excited":
        wig = 0.15 * math.sin(2 * math.pi * 3.0 * t)         # perked + fast wiggle
        return EAR_UP + wig, EAR_UP - wig
    if emotion == "curious":
        tilt = 0.25 * math.sin(2 * math.pi * 0.8 * t)        # one ear cocks, slow scan
        return EAR_UP * 0.7 + tilt, EAR_UP * 0.4 - tilt
    if emotion == "alarmed":
        twitch = 0.3 * math.sin(2 * math.pi * 9.0 * t)       # fast twitch (startled)
        return EAR_UP + twitch, EAR_UP - twitch
    if emotion == "sad":
        return EAR_DOWN, EAR_DOWN                             # drooped
    # neutral: slight idle sway (never perfectly still)
    idle = 0.05 * math.sin(2 * math.pi * 0.4 * t)
    return 0.2 + idle, 0.2 - idle


# Emotion -> also a head/gaze/torso OFFSET hint (the #3 expressive-offset layer will
# add these ON TOP of the locomotion policy's head joints — additive, still no retrain).
HEAD_OFFSET = {
    "happy":   dict(head_pitch=-0.15, head_yaw=0.0),         # chin up
    "curious": dict(head_pitch=0.05,  head_yaw=0.2),         # head cock
    "alarmed": dict(head_pitch=-0.1,  head_yaw=0.0),         # alert
    "sad":     dict(head_pitch=0.25,  head_yaw=0.0),         # head down
    "neutral": dict(head_pitch=0.0,   head_yaw=0.0),
}


def eye_state(emotion: str) -> dict:
    """LED eyes (not motors) — color + brightness, mirroring Disney's show functions."""
    return {
        "happy":   dict(color=(0, 180, 255), brightness=1.0),
        "curious": dict(color=(0, 255, 200), brightness=0.8),
        "alarmed": dict(color=(255, 40, 0),  brightness=1.0),
        "sad":     dict(color=(40, 60, 120), brightness=0.5),
        "neutral": dict(color=(0, 200, 255), brightness=0.7),
    }.get(emotion, dict(color=(0, 200, 255), brightness=0.7))
