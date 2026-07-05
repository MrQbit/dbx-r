"""ROCKY-5 translated voice — the DUAL-TRACK output.

Rocky speaks native Eridian (musical chords); Grace's laptop translator speaks the
English on top. So our robot emits BOTH, mixed: the Eridian chord track sits
QUIETER, in the back; the English TTS rides LOUDER, on top — so a human can
actually interact with Rocky while still hearing his real voice underneath (as in
the film). Emotion drives pitch/brightness on both tracks (agitation -> up, grave
-> down); questions carry a rising "Question?" cluck.

Organic-ish timbre (breathy partials + noise) approximates the film's ocarina /
water-jug / whale / birdsong palette without breaking the codec's clean synth
(that stays in synth.py for the decode round-trip).
"""

from __future__ import annotations

import numpy as np

from rocky.audio.synth import SR, INHARMONICITY, _adsr
from rocky.audio.codec import PITCHES, token_to_glyph
from rocky.audio import tts
from rocky import persona

ERIDIAN_GAIN = 0.32          # back track — quiet
ENGLISH_GAIN = 1.0           # front track — clear
_PARTIALS = np.array([1.0, 0.5, 0.33, 0.22, 0.13])   # up to 5 (ocarina-ish)


def _organic_chord(freqs, dur_ms: float, brightness: float = 0.6,
                   breath: float = 0.08) -> np.ndarray:
    """A breathy additive chord: inharmonic partials + filtered breath noise +
    slow amplitude flutter (organic, not electronic)."""
    n = max(int(SR * dur_ms / 1000), 1)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    for f in freqs:
        for k, amp in enumerate(_PARTIALS, start=1):
            if k > 2 and brightness < (k - 2) / len(_PARTIALS):
                continue                                  # dim highs when un-bright
            fk = f * k * (1 + INHARMONICITY * (k - 1))
            out += (amp * brightness ** (k - 1)) * np.sin(2 * np.pi * fk * t)
    # breath: gentle band-ish noise shaped by the envelope
    rng = np.random.RandomState(int(sum(freqs)) % 2**31)
    noise = rng.randn(n).astype(np.float32)
    noise = np.convolve(noise, np.ones(8) / 8, mode="same")   # soften (low-pass-ish)
    out = out / (len(freqs) + 1e-6) + breath * noise
    flutter = 1.0 + 0.05 * np.sin(2 * np.pi * 5.5 * t)        # slow vibrato/flutter
    return (out * _adsr(n) * flutter).astype(np.float32)


def _chord_freqs(token: str, semitones: int) -> np.ndarray:
    idxs, _ = token_to_glyph(token)
    shift = 2 ** (semitones / 12.0)
    return PITCHES[list(idxs)] * shift


def question_cluck(semitones: int = 0) -> np.ndarray:
    """Fast rising chirp — Rocky's interrogative gesture (spec §2)."""
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f0 = 300 * 2 ** (semitones / 12.0)
    freq = f0 * (1 + 2.2 * (t / t[-1]))                       # rising glide
    phase = 2 * np.pi * np.cumsum(freq) / SR
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.7
    return (0.5 * np.sin(phase) * env).astype(np.float32)


def eridian_phrase(words, emotion: str = "neutral",
                   total_ms: float | None = None) -> np.ndarray:
    """Render one organic chord per word (deterministic via the codec), spanning
    total_ms if given (so it aligns under the English speech)."""
    vp = persona.voice_params(emotion)
    semis, bright = vp["pitch_semitones"], vp["brightness"]
    words = [w for w in words if w] or ["rocky"]
    per_ms = (total_ms / len(words)) if total_ms else 260.0
    segs = [_organic_chord(_chord_freqs(w, semis), per_ms, brightness=bright)
            for w in words]
    return np.concatenate(segs) if segs else np.zeros(0, dtype=np.float32)


def _fit(a: np.ndarray, n: int) -> np.ndarray:
    if len(a) >= n:
        return a[:n]
    return np.concatenate([a, np.zeros(n - len(a), dtype=np.float32)])


def translate(text: str, emotion: str = "neutral", tag: str = "statement",
              eridian_gain: float = ERIDIAN_GAIN,
              english_gain: float = ENGLISH_GAIN, english: bool = True) -> np.ndarray:
    """The translated voice: English TTS (front) mixed over the quieter Eridian
    chord (back). tag in {'statement','question'} adds the rising cluck + espeak
    intonation. Emotion shifts pitch/brightness on both tracks."""
    vp = persona.voice_params(emotion)
    semis = vp["pitch_semitones"]

    spoken = persona.say(text, tag)                          # literal Eridian syntax
    eng = tts.speak(spoken, pitch=int(np.clip(42 + 3 * semis, 5, 95)),
                    pitch_range=70) if english else np.zeros(0, dtype=np.float32)

    span_ms = (len(eng) / SR * 1000) if len(eng) else 260.0 * max(len(text.split()), 1)
    erid = eridian_phrase(text.split(), emotion, total_ms=span_ms)
    if tag == "question":
        erid = np.concatenate([question_cluck(semis), erid])

    n = max(len(eng), len(erid), 1)
    mix = english_gain * _fit(eng, n) + eridian_gain * _fit(erid, n)
    peak = np.abs(mix).max()
    return (mix / peak * 0.95).astype(np.float32) if peak > 0 else mix


def write_wav(audio: np.ndarray, path: str) -> None:
    import wave
    a = np.clip(audio, -1, 1)
    pcm = (a * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm)
