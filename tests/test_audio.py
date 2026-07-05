"""G7 audio — ROCKY-5 chord voice (ROBOTS_SPEC.md §7).

The synth + codec + motifs are complete and tested. The blind FFT-decode
round-trip (>=99% at SNR 20 dB) is IN PROGRESS — ADSR fades + octave-harmonic
overlap make blind segmentation hard; marked xfail until refined.
"""

from __future__ import annotations

import numpy as np
import pytest

from rocky.audio import synth
from rocky.audio.codec import encode, decode, token_to_glyph, encode_to_audio, MOTIFS, PITCHES


def test_synth_note_is_finite_and_normalised():
    a = synth.note(220.0, 240.0)
    assert a.shape[0] == int(240 * synth.SR / 1000)
    assert np.all(np.isfinite(a)) and np.abs(a).max() <= 1.0 + 1e-6


def test_pentatonic_is_ten_pitches():
    assert len(PITCHES) == 10                      # A-minor pentatonic x2 octaves


def test_token_to_glyph_is_deterministic_and_valid():
    for tok in ["hello", "rocky", "grace"]:
        idx, dur = token_to_glyph(tok)
        assert token_to_glyph(tok) == (idx, dur)   # deterministic (SHA-1)
        assert 2 <= len(idx) <= 4                   # 2-4 note chord
        assert dur in (120.0, 240.0, 480.0)


def test_motifs_render_to_audio():
    for name in ("greeting", "query", "alarm", "amaze"):
        a = encode_to_audio([name])
        assert len(a) > 0 and np.abs(a).max() > 0.1


def test_decode_roundtrip_99pct_at_snr20():
    """§7 target: encode -> synth -> +noise(SNR 20 dB) -> FFT-decode recovers the
    chords >= 99%. Averaged over several messages (peak-vs-leakage + harmonic-aware
    detection; encoder avoids harmonically-colliding pitches within a chord)."""
    import random
    import string
    total = match = 0
    for seed in range(10):
        rng = np.random.RandomState(seed)
        r2 = random.Random(seed)
        tokens = ["".join(r2.choices(string.ascii_lowercase, k=r2.randint(3, 7)))
                  for _ in range(12)]
        ref = [token_to_glyph(t) for t in tokens]
        audio = encode_to_audio(tokens)
        p = np.mean(audio ** 2)
        noise = rng.randn(len(audio))
        noise *= np.sqrt(p / 10 ** (20 / 10) / np.mean(noise ** 2))
        dec = decode(audio + noise)
        n = min(len(ref), len(dec))
        match += sum(set(ref[i][0]) == set(dec[i][0]) for i in range(n))
        total += len(ref)
    assert match / total >= 0.99, f"round-trip {100 * match / total:.1f}% < 99%"
