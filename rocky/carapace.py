"""ROCKY-5 carapace kinematics — the 5-plate "breathing" + speech-resonance shell.

Rocky's carapace is a segmented pentagonal iris: 5 rock plates around a central
core that translate radially (θ_i = 72°·i) to breathe, and micro-jitter when he
speaks (the plates act like a speaker cone). Per the operator's derivation:

    P_deformed = P_base + r_i · ( A_breath·f_cycle(t) + A_speech·sin(ω_speech·t) )
    r_i = [cos θ_i, sin θ_i, 0]

This drives the sim/animation deformation AND, on the physical robot, the target
radial position of each plate. Breathing rate rises with arousal; speech jitter is
gated on while the chord voice plays (rocky/audio) — ties the shell to persona.py.
"""

from __future__ import annotations

import math

N_PLATES = 5
A_BREATH_MM = 20.0        # deep-breath radial expansion (spec 15-25 mm)
A_SPEECH_MM = 3.0         # speech micro-jitter (spec 2-4 mm)
OMEGA_SPEECH_HZ = 22.0    # chattering resonance (spec 15-30 Hz)
BREATH_PERIOD_S = 4.0     # resting breath cycle


def plate_azimuth(i: int) -> float:
    """Radial azimuth θ_i of plate i (rad)."""
    return math.radians(72.0 * (i % N_PLATES))


def radial_unit(i: int):
    """r_i = [cos θ_i, sin θ_i, 0]."""
    th = plate_azimuth(i)
    return (math.cos(th), math.sin(th), 0.0)


def breath_curve(phase: float) -> float:
    """f_cycle(t): asymmetric breath in [0,1] -> [0,1], FAST inhale, SLOW deflate."""
    p = phase % 1.0
    inhale = 0.3                                   # 30% of cycle expanding
    if p < inhale:
        return math.sin((p / inhale) * (math.pi / 2))          # 0->1 fast
    return math.cos(((p - inhale) / (1 - inhale)) * (math.pi / 2))  # 1->0 slow


def plate_displacement_mm(i: int, t: float, *, breathing: bool = True,
                          speaking: bool = False, arousal: float = 0.3) -> float:
    """Radial outward displacement (mm) of plate i at time t. Arousal speeds the
    breath (agitated Rocky breathes faster/deeper); speaking adds the jitter."""
    disp = 0.0
    if breathing:
        period = BREATH_PERIOD_S * (1.0 - 0.5 * arousal)       # faster when aroused
        amp = A_BREATH_MM * (0.6 + 0.4 * arousal)              # deeper when aroused
        disp += amp * breath_curve(t / period)
    if speaking:
        disp += A_SPEECH_MM * math.sin(2 * math.pi * OMEGA_SPEECH_HZ * t)
    return disp


def plate_offset(i: int, t: float, **kw):
    """3D offset vector (mm) applied to every vertex of plate i (P_base -> P_deformed)."""
    d = plate_displacement_mm(i, t, **kw)
    rx, ry, rz = radial_unit(i)
    return (rx * d, ry * d, rz * d)


def deform(vertices, i: int, t: float, **kw):
    """Apply the plate-i radial offset to an (N,3) vertex array (numpy or list)."""
    import numpy as np
    ox, oy, oz = plate_offset(i, t, **kw)
    return np.asarray(vertices, dtype=float) + np.array([ox, oy, oz])
