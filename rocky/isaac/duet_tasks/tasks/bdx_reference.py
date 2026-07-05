"""BDX-A bipedal reference gait — hand-authored (Isaac imitation reward).

A simple, robust bipedal walk cadence: the two legs are 180 deg out of phase; each
leg swings its hip fore/aft, lifts the knee during swing, and keeps the foot level
with an ankle counter-rotation. Used with a MODEST reward weight so it shapes the
walking rhythm/character without over-constraining the terrain policy. Pure numpy.
"""

from __future__ import annotations

import numpy as np

SIDES = ("Left", "Right")
KNEE_CROUCH = 0.4                 # natural bent-knee stance
HIP_SWING = 0.35                  # fore-aft hip amplitude
KNEE_LIFT = 0.5                   # extra knee flex during swing
DUTY = 0.6


def _leg(theta: float):
    """One leg's (hip_pitch, knee, ankle) at local phase theta in [0,1)."""
    hip_pitch = HIP_SWING * np.sin(2 * np.pi * theta)          # fore-aft swing
    if theta < DUTY:                                           # stance
        swing = 0.0
    else:                                                      # swing: lift
        s = (theta - DUTY) / (1.0 - DUTY)
        swing = np.sin(np.pi * s)                              # 0->1->0
    knee = KNEE_CROUCH + KNEE_LIFT * swing
    ankle = -0.5 * hip_pitch - 0.2 * swing                     # keep foot roughly level
    return hip_pitch, knee, ankle


def reference(phase: float) -> dict:
    """Joint-name -> target angle at global gait phase in [0,1)."""
    out = {}
    for k, side in enumerate(SIDES):
        theta = (phase + 0.5 * k) % 1.0                        # legs 180 deg apart
        hip_pitch, knee, ankle = _leg(theta)
        out[f"{side}_Hip_Pitch"] = hip_pitch
        out[f"{side}_Knee"] = knee
        out[f"{side}_Ankle"] = ankle
        out[f"{side}_Hip_Yaw"] = 0.0
        out[f"{side}_Hip_Roll"] = 0.0
    for h in ("Neck_Pitch", "Head_Pitch", "Head_Yaw", "Head_Roll"):
        out[h] = 0.0                                           # head held level
    return out
