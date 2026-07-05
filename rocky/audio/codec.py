"""ROCKY-5 chord codec (ROBOTS_SPEC.md §7).

A-minor pentatonic x2 octaves = 10 pitches. A glyph = a 2-4 note chord + a
duration in {120,240,480} ms; tokens map to glyphs via a SHA-1 index (so the
mapping is deterministic and content-addressed). Reserved motifs: greeting
(ascending triad), query (rising fifth), alarm (repeated wide interval), and the
fixed 4-note "Amaze" figure. Decode recovers glyphs from audio by FFT energy at
the 10 known pitch frequencies — the round-trip target is >=99% at SNR 20 dB.
"""

from __future__ import annotations

import hashlib

import numpy as np

from rocky.audio.synth import SR, render, PARTIAL_AMPS

# A-minor pentatonic (A C D E G), two octaves, ~G2..G4 register.
PITCHES = np.array([110.00, 130.81, 146.83, 164.81, 196.00,     # A2 C3 D3 E3 G3
                    220.00, 261.63, 293.66, 329.63, 392.00])    # A3 C4 D4 E4 G4
DURATIONS = (120.0, 240.0, 480.0)


# Harmonic-collision graph: pitch j collides with i if f_j sits on one of i's
# inharmonic partials (k*f_i, k=2..4). We never put a colliding pair in one chord,
# so every chord is harmonically independent and the acoustic round-trip is exact
# (octaves like A2/A3 AND 3rd-partial hits like A2->E4, C3->G4 are all covered).
def _build_collisions():
    n = len(PITCHES)
    col = {i: set() for i in range(n)}
    for i in range(n):
        for k in (2, 3, 4):
            hf = PITCHES[i] * k * (1 + 0.003 * (k - 1))
            for j in range(n):
                if i != j and abs(PITCHES[j] - hf) < 0.03 * hf:
                    col[i].add(j); col[j].add(i)
    return col


COLLIDES = _build_collisions()


def token_to_glyph(token: str):
    """Deterministic token -> (pitch-index tuple, duration_ms) via SHA-1.
    Avoids harmonically-colliding pitches within a chord (see COLLIDES)."""
    h = hashlib.sha1(token.encode()).digest()
    size = 2 + h[0] % 3                          # 2..4 notes
    idxs: list[int] = []
    i = 1
    while len(idxs) < size and i < len(h):
        c = h[i] % len(PITCHES)
        if c not in idxs and not (COLLIDES[c] & set(idxs)):
            idxs.append(c)
        i += 1
    dur = DURATIONS[h[6] % 3]
    return tuple(sorted(idxs)), dur


# Reserved motifs — fixed glyph sequences (pitch-index tuples + duration).
MOTIFS = {
    "greeting": [((0, 2, 4), 240.0)],                       # ascending A-D-G triad
    "query":    [((0, 3), 240.0)],                          # rising fifth A2->E3
    "alarm":    [((0, 4), 120.0)] * 3,                      # repeated wide interval x3
    "amaze":    [((5,), 120.0), ((7,), 120.0),             # fixed 4-note figure
                 ((9,), 120.0), ((5, 9), 240.0)],
}


def _glyph_freqs(idxs) -> list[float]:
    return [float(PITCHES[i]) for i in idxs]


def encode(tokens) -> list:
    """Tokens (or a reserved motif name) -> list of (freqs, dur_ms) glyphs."""
    glyphs = []
    for tok in tokens:
        if tok in MOTIFS:
            glyphs += [(_glyph_freqs(idx), d) for idx, d in MOTIFS[tok]]
        else:
            idx, dur = token_to_glyph(tok)
            glyphs.append((_glyph_freqs(idx), dur))
    return glyphs


def encode_to_audio(tokens, gap_ms: float = 180.0):
    return render(encode(tokens), gap_ms=gap_ms)


def _segments(audio, sr, gap_ms):
    """Non-silent runs, merged across sub-gap dips, tiny fragments dropped."""
    frame = int(0.01 * sr)
    rms = np.array([np.sqrt(np.mean(audio[i:i + frame] ** 2))
                    for i in range(0, len(audio) - frame, frame)])
    # smooth to avoid noise-driven splits
    k = 5
    rms = np.convolve(rms, np.ones(k) / k, mode="same")
    thr = 0.12 * (rms.max() + 1e-9)
    active = rms > thr
    segs, s = [], None
    for i, a in enumerate(active):
        if a and s is None:
            s = i
        elif not a and s is not None:
            segs.append([s * frame, i * frame]); s = None
    if s is not None:
        segs.append([s * frame, len(audio)])
    # merge segments separated by less than half a gap (spurious splits)
    merge_gap = int(0.5 * gap_ms / 1000 * sr)
    merged = []
    for seg in segs:
        if merged and seg[0] - merged[-1][1] < merge_gap:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)
    min_len = int(0.06 * sr)
    return [(a, b) for a, b in merged if b - a >= min_len]


def decode(audio: np.ndarray, gap_ms: float = 180.0, sr: int = SR):
    """Recover glyphs (pitch-index tuple, duration_ms) from audio. For each glyph
    window, measure FFT energy at the 10 pitch fundamentals, then detect notes
    GREEDILY low->high, subtracting each detected note's harmonic contribution so
    an octave's fundamental isn't confused with a lower note's 2nd partial."""
    glyphs = []
    for a, b in _segments(audio, sr, gap_ms):
        seg = audio[a:b]
        # Zero-pad the FFT so low pitches (A2=110 Hz) get bins finer than their
        # detection band; use a min absolute band width (>=5 Hz) too.
        nfft = max(1 << 15, 1 << int(len(seg) - 1).bit_length())
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=nfft))
        freqs = np.fft.rfftfreq(nfft, 1 / sr)

        def peak_energy(f0):
            bw = max(0.02 * f0, 5.0)
            band = np.abs(freqs - f0) < bw
            if not band.any():
                return 0.0
            # a real fundamental is a PEAK above the local baseline; a leakage tail
            # from an adjacent pitch is a slope (peak ~ baseline) -> suppressed.
            shoulder = (np.abs(freqs - f0) >= bw) & (np.abs(freqs - f0) < 2.5 * bw)
            base = spec[shoulder].mean() if shoulder.any() else 0.0
            return max(spec[band].max() - base, 0.0)

        energy = np.array([peak_energy(f0) for f0 in PITCHES])
        emax = energy.max() + 1e-9
        residual = energy.astype(float).copy()
        detected = []
        for i in np.argsort(PITCHES):          # low -> high
            # a colliding lower note already detected means energy here is its
            # harmonic (the encoder never co-places colliding pitches)
            if COLLIDES[i] & set(detected):
                continue
            if residual[i] > 0.28 * emax and energy[i] > 0.20 * emax:
                detected.append(int(i))
                # subtract this note's inharmonic partials from higher pitch bands
                for k, amp in zip((2, 3, 4), PARTIAL_AMPS[1:]):
                    hf = PITCHES[i] * k * (1 + 0.003 * (k - 1))
                    for j in range(len(PITCHES)):
                        if abs(PITCHES[j] - hf) < 0.03 * hf:
                            residual[j] -= amp * energy[i]
        present = tuple(sorted(detected))[:4]
        dur = min(DURATIONS, key=lambda d: abs(d - len(seg) / sr * 1000))
        glyphs.append((present, dur))
    return glyphs
