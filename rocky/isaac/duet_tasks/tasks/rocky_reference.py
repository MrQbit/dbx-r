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

DUTY = 0.6                       # fraction of the cycle a leg is planted (3/5 down = stable)
STANCE_FEMUR = 0.6               # default planted pose (matches the builder stance)
STANCE_TIBIA = 1.0
COXA_SWEEP = 0.35                # protraction/retraction amplitude (rad) — clear stride
LIFT_FEMUR = 0.75                # how much the femur raises during swing (visible high step)
FOLD_TIBIA = 0.7                 # how much the tibia folds during swing


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


# Movie note (Scanlan/Ortiz): Rocky's gait is deliberately SYNCOPATED — "one's
# moving slightly different than the other", never perfectly still, and the whole
# body ROCKS toward the planted side when a leg lifts. Early clean crab/spider
# gaits read as "scary" and were rejected. So we perturb the even 72° offsets
# (fixed per-leg desync) and vary lift height slightly per leg.
PHASE_DESYNC = (0.00, 0.06, -0.04, 0.05, -0.03)       # break the perfect wave
LIFT_VARY = (1.0, 0.9, 1.08, 0.94, 1.05)              # per-leg lift variation


def reference(phase: float, limb_count: int = 5, grip_legs=(1, 4)) -> dict:
    """Joint-name -> target angle at global gait phase in [0,1). Syncopated wave."""
    out = {}
    for i in range(limb_count):
        theta = (phase + i / limb_count + PHASE_DESYNC[i % 5]) % 1.0
        coxa, femur, tibia = _leg_phase(theta)
        # per-leg lift variation (desync the depth too)
        femur = STANCE_FEMUR - (STANCE_FEMUR - femur) * LIFT_VARY[i % 5]
        tibia = STANCE_TIBIA - (STANCE_TIBIA - tibia) * LIFT_VARY[i % 5]
        out[f"leg{i}_coxa_yaw"] = coxa
        out[f"leg{i}_femur_pitch"] = femur
        out[f"leg{i}_tibia_pitch"] = tibia
    for leg in grip_legs:
        out[f"leg{leg}_grip"] = 0.0                    # grips open while walking
    return out


def body_roll(phase: float, limb_count: int = 5) -> float:
    """Lateral body roll (rad) toward the planted side — the signature 'rock when
    a leg lifts'. Sum each leg's lift weighted by its radial direction's y-comp."""
    import math
    roll = 0.0
    for i in range(limb_count):
        theta = (phase + i / limb_count + PHASE_DESYNC[i % 5]) % 1.0
        lift = math.sin(math.pi * (theta - DUTY) / (1 - DUTY)) if theta >= DUTY else 0.0
        ang = 2 * math.pi * i / limb_count
        roll += 0.06 * lift * math.sin(ang)            # rock away from the lifting leg
    return roll


def reference_array(phase: float, joint_names) -> np.ndarray:
    """Reference targets as an array in the given joint order (for the RL reward)."""
    ref = reference(phase)
    return np.array([ref.get(n, 0.0) for n in joint_names], dtype=np.float32)
