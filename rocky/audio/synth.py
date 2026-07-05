"""ROCKY-5 chord-voice synthesizer (ROBOTS_SPEC.md §7).

Rocky (Project Hail Mary) speaks in musical chords. Additive synth: partials
[1, .5, .33, .2] with +0.3%/partial inharmonicity, ADSR 30/80/0.7/150 ms,
vibrato 5 Hz ±6 cents, 22.05 kHz mono, register ~G2-G4.
"""

from __future__ import annotations

import numpy as np

SR = 22050
PARTIAL_AMPS = np.array([1.0, 0.5, 0.33, 0.2])
INHARMONICITY = 0.003          # +0.3% per partial
VIBRATO_HZ = 5.0
VIBRATO_CENTS = 6.0
ADSR_MS = (30.0, 80.0, 0.7, 150.0)   # attack, decay, sustain-level, release


def _adsr(n: int, sr: int = SR) -> np.ndarray:
    a, d, s, r = ADSR_MS
    note_ms = n / sr * 1000
    # Scale A/D/R down if they'd exceed the note, always leaving a sustain plateau
    # (~15%) so a note reads as a clean on/off, not a fade-to-zero mid-note.
    total = a + d + r
    if total > note_ms * 0.85:
        a, d, r = (x * note_ms * 0.85 / total for x in (a, d, r))
    a_n, d_n, r_n = (max(int(x * sr / 1000), 1) for x in (a, d, r))
    sus_n = max(n - a_n - d_n - r_n, 1)
    env = np.concatenate([
        np.linspace(0, 1, a_n),
        np.linspace(1, s, d_n),
        np.full(sus_n, s),
        np.linspace(s, 0, r_n),
    ])
    return np.resize(env, n)


def note(freq: float, dur_ms: float, sr: int = SR) -> np.ndarray:
    """One additive-synth note with inharmonic partials + vibrato + ADSR."""
    n = int(dur_ms * sr / 1000)
    t = np.arange(n) / sr
    vib = (2 ** (VIBRATO_CENTS / 1200)) ** np.sin(2 * np.pi * VIBRATO_HZ * t)
    sig = np.zeros(n)
    for k, amp in enumerate(PARTIAL_AMPS, start=1):
        pf = freq * k * (1 + INHARMONICITY * (k - 1))
        sig += amp * np.sin(2 * np.pi * pf * vib * t)
    sig *= _adsr(n, sr)
    return sig / (np.abs(sig).max() + 1e-9)


def chord(freqs, dur_ms: float, sr: int = SR) -> np.ndarray:
    """Sum of notes at the given frequencies, normalised."""
    mix = sum(note(f, dur_ms, sr) for f in freqs)
    return mix / (np.abs(mix).max() + 1e-9)


def render(glyphs, gap_ms: float = 180.0, sr: int = SR) -> np.ndarray:
    """Render a sequence of (freqs, dur_ms) glyphs separated by silent gaps."""
    gap = np.zeros(int(gap_ms * sr / 1000))
    parts = []
    for freqs, dur in glyphs:
        parts.append(chord(freqs, dur, sr))
        parts.append(gap)
    return np.concatenate(parts) if parts else np.zeros(0)
