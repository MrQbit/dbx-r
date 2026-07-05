"""ROCKY-5 persona / behavior model (Project Hail Mary, synthesized from the
operator's behavioral spec + movie BTS research — docs/ingest/rocky-movie-reference.md).

Rocky has no face — ALL emotion is body + sound. This maps a small
(arousal, valence) emotional state to:
  * joint JITTER/vibration (the "never perfectly still", tapping/chattering)
  * gait modulation (tempo, lift, sway)
  * voice params (pitch up when agitated, down when grave; triple-repeat when excited)
  * a gesture library (tap, sway, retract, scan-tilt, trace, dormant rock-dome)
and formats dialogue in Rocky's literal Eridian-translated syntax
(", question!" / ", statement!", simplified lexicon).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Emotion:
    arousal: float          # 0 (calm/still) .. 1 (agitated/fast)
    valence: float          # -1 (distress) .. +1 (delight)
    gesture: str            # default body gesture for this state


# Named states from the spec (excitement=tap/sway, distress=retract/chatter, ...).
EMOTIONS = {
    "neutral":  Emotion(0.25, 0.0, "idle_sway"),
    "excited":  Emotion(0.90, 0.8, "hand_tap"),      # rapid tapping, carapace sway
    "agree":    Emotion(0.55, 0.6, "hand_tap"),
    "curious":  Emotion(0.35, 0.3, "scan_tilt"),     # hold still, tilt toward subject
    "solemn":   Emotion(0.20, -0.3, "idle_sway"),    # grave/sincere -> slow, low
    "distress": Emotion(0.95, -0.9, "retract"),      # retract limbs, chatter
    "dormant":  Emotion(0.02, 0.0, "rock_dome"),     # withdraw all limbs -> a rock
}


# --- emotion -> motion (joint jitter / vibration) --------------------------
# The three spec §3 micro-motion profiles, as explicit generators:

def wrist_tap(t: float, freq: float = 10.0, amp: float = 0.06) -> float:
    """Excitement/affirmation: fast (8-12 Hz) RECTIFIED oscillation on the grounded
    end-effectors — 3-pronged fingers rapidly tapping a surface."""
    return amp * abs(math.sin(2 * math.pi * freq * t))


def scan_tilt(t: float, omega_slow: float = 1.0, amp: float = 0.12) -> float:
    """Echolocation scanning: a slow sinusoidal tilt of the chassis toward the
    region of interest (translation velocity held at zero)."""
    return amp * math.sin(omega_slow * t)


def agitate_noise(rng, sigma: float = 0.05, n: int = 15) -> "list[float]":
    """Agitation/alarm: Gaussian noise (sigma~0.05 rad) across all 15 leg joints
    simultaneously — a full-body structural vibration (chattering stone)."""
    return [float(x) for x in rng.normal(0.0, sigma, n)]


def jitter(state: str, t: float, joint_index: int, is_wrist: bool = False) -> float:
    """Per-joint vibration to ADD to the gait targets (rad), dispatched to the spec
    profile for the state: excited/agree -> wrist tap on end-effectors; distress ->
    broadband tremor (use agitate_noise for the true Gaussian); else arousal-scaled
    tremor. Dormant is nearly still."""
    e = EMOTIONS[state]
    if state in ("excited", "agree") and is_wrist:
        return wrist_tap(t, freq=8.0 + 4.0 * e.arousal)
    freq = 2.0 + 14.0 * e.arousal              # ~2 Hz calm .. ~16 Hz agitated chatter
    amp = (0.05 if state == "distress" else 0.01 + 0.04 * e.arousal)
    return amp * math.sin(2 * math.pi * freq * t + joint_index * 1.7)


def gait_mod(state: str) -> dict:
    """Emotion -> gait modulation multipliers (feed rocky_reference tempo/lift)."""
    e = EMOTIONS[state]
    return {
        "tempo_scale": 0.6 + 1.1 * e.arousal,          # slow when calm, quick when excited
        "lift_scale": 0.7 + 0.5 * max(e.valence, 0),   # bigger, sharper steps when up
        "sway": 0.04 + 0.05 * e.arousal,               # lateral carapace rock
    }


def voice_params(state: str) -> dict:
    """Emotion -> chord-voice params (agitation raises pitch/brightness; delight
    triple-repeats — the 'Amaze amaze amaze')."""
    e = EMOTIONS[state]
    return {
        "pitch_semitones": round(7 * e.arousal * (1 if e.valence >= 0 else 0.6)
                                 - 4 * max(-e.valence, 0)),   # up=agitated, down=grave
        "brightness": 0.4 + 0.6 * e.arousal,
        "repeat": 3 if (e.arousal > 0.7 and e.valence > 0.5) else 1,
    }


# --- dialogue: Rocky's literal Eridian-translated syntax --------------------
_LEXICON = {                                   # simplified/literal substitutions
    "humans": "leaky space blobs", "human": "leaky space blob",
    "spaceship": "ship", "understand": "understand",
}
_STOPWORDS = {"the", "a", "an", "is", "are", "am", "to", "of"}   # dropped (literal)


def say(text: str, tag: str = "statement", literal: bool = True) -> str:
    """Format an utterance in Rocky's translated syntax: strip articles/copula,
    apply the lexicon, and append the mandatory context tag (', question!'/', statement!').
    tag in {'question','statement'}."""
    words = text.strip().rstrip(".!?").split()
    out = []
    for w in words:
        lw = w.lower()
        if literal and lw in _STOPWORDS:
            continue
        out.append(_LEXICON.get(lw, w))
    body = " ".join(out)
    punct = "?" if tag == "question" else "!"
    return f"{body}, {tag}{punct}"
