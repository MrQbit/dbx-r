"""ROCKY-5 movie-accurate reference gait — hand-authored (for imitation learning).

Rocky (Project Hail Mary) moves deliberately on five radial legs. This encodes a
pentapod WAVE gait (spec §6.3: 5 oscillators, phase offsets 2πi/5): each leg lifts
and swings forward in turn while the others stay planted. Duty factor 0.8 keeps
4 of 5 legs down at all times (stable, heavy-Eridian look). The two front
manipulator legs (1 & 4) keep their grips open while walking.

The RL policy is rewarded for tracking this reference (the "ghost") — it supplies
the gait STYLE; the policy adds balance/dynamics. Pure numpy so it renders on the
host and feeds the Isaac imitation reward.
"""

from __future__ import annotations

import numpy as np

DUTY = 0.8                       # fraction of the cycle a leg is planted (4/5 legs down)
STANCE_FEMUR = 0.6               # default planted pose (matches the builder stance)
STANCE_TIBIA = 1.0
COXA_SWEEP = 0.18                # protraction/retraction amplitude (rad)
LIFT_FEMUR = 0.45                # how much the femur raises during swing
FOLD_TIBIA = 0.55                # how much the tibia folds during swing


def _leg_phase(theta: float):
    """One leg's joint targets at its local phase theta in [0,1):
    stance (planted, retracting to push) then a lift-and-swing-forward."""
    if theta < DUTY:                                   # stance
        s = theta / DUTY
        coxa = COXA_SWEEP * (0.5 - s)                  # sweep back (push body forward)
        return coxa, STANCE_FEMUR, STANCE_TIBIA
    s = (theta - DUTY) / (1.0 - DUTY)                  # swing 0->1
    lift = np.sin(np.pi * s)                           # 0->1->0 (raise then plant)
    coxa = -COXA_SWEEP * 0.5 + COXA_SWEEP * s          # swing forward
    femur = STANCE_FEMUR - LIFT_FEMUR * lift           # raise the foot
    tibia = STANCE_TIBIA - FOLD_TIBIA * lift           # fold the shank
    return coxa, femur, tibia


def reference(phase: float, limb_count: int = 5, grip_legs=(1, 4)) -> dict:
    """Joint-name -> target angle at global gait phase in [0,1)."""
    out = {}
    for i in range(limb_count):
        theta = (phase + i / limb_count) % 1.0
        coxa, femur, tibia = _leg_phase(theta)
        out[f"leg{i}_coxa_yaw"] = coxa
        out[f"leg{i}_femur_pitch"] = femur
        out[f"leg{i}_tibia_pitch"] = tibia
    for leg in grip_legs:
        out[f"leg{leg}_grip"] = 0.0                    # grips open while walking
    return out


def reference_array(phase: float, joint_names) -> np.ndarray:
    """Reference targets as an array in the given joint order (for the RL reward)."""
    ref = reference(phase)
    return np.array([ref.get(n, 0.0) for n in joint_names], dtype=np.float32)
