"""Offline English TTS for ROCKY-5's translated voice — direct ctypes binding to
libespeak-ng (no binary, no sudo, aarch64-native). espeak-ng's rugged, slightly
clipped, mechanical timbre is exactly the film's "laptop translator" texture: in
Project Hail Mary, Grace's TTS speaks the ENGLISH translation on top of Rocky's
native Eridian chords. This is the English (front) track; rocky/audio/voice.py
mixes it over the quieter Eridian chord (back) track.
"""

from __future__ import annotations

import ctypes

import numpy as np
from scipy import signal

from rocky.audio.synth import SR

_AUDIO_OUTPUT_RETRIEVAL = 1
_RATE, _PITCH, _RANGE = 1, 3, 4        # espeak_SetParameter ids

_lib = None
_native_sr = SR


def _init():
    global _lib, _native_sr
    if _lib is not None:
        return _lib
    lib = ctypes.CDLL("libespeak-ng.so.1")
    lib.espeak_Initialize.restype = ctypes.c_int
    _native_sr = lib.espeak_Initialize(_AUDIO_OUTPUT_RETRIEVAL, 0, None, 0)
    if _native_sr < 0:
        raise RuntimeError("espeak-ng failed to initialize")
    _lib = lib
    return lib


def speak(text: str, pitch: int = 42, rate: int = 150, voice: str = "en",
          pitch_range: int = 60) -> np.ndarray:
    """Synthesize `text` to a float32 waveform in [-1, 1] at SR. pitch 0-100,
    rate wpm, pitch_range 0-100 (expressiveness). Emotion maps onto pitch/range
    in voice.py (agitation -> higher pitch, per the film's sound design)."""
    lib = _init()
    chunks: list = []

    CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short),
                          ctypes.c_int, ctypes.c_void_p)

    def _cb(wav, n, events):
        if n > 0:
            chunks.append(np.ctypeslib.as_array(wav, (n,)).copy())
        return 0

    cb = CB(_cb)
    lib.espeak_SetSynthCallback(cb)
    lib.espeak_SetVoiceByName(voice.encode())
    lib.espeak_SetParameter(_RATE, int(rate), 0)
    lib.espeak_SetParameter(_PITCH, int(np.clip(pitch, 0, 100)), 0)
    lib.espeak_SetParameter(_RANGE, int(np.clip(pitch_range, 0, 100)), 0)

    b = text.encode()
    lib.espeak_Synth(b, len(b) + 1, 0, 0, 0, 0, None, None)
    lib.espeak_Synchronize()

    if not chunks:
        return np.zeros(0, dtype=np.float32)
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    if _native_sr != SR:                              # resample if espeak differs
        n_out = int(len(audio) * SR / _native_sr)
        audio = np.interp(np.linspace(0, len(audio), n_out, endpoint=False),
                          np.arange(len(audio)), audio).astype(np.float32)
    return audio


# --- "laptop translator" character (movie-match) ---------------------------
def _bandpass(a, lo=150.0, hi=4000.0):
    """Strip sub-150 warmth + above-4k air -> the thin translated-TTS interface
    (removes the natural warm human chest resonance)."""
    ny = SR / 2.0
    sos = signal.butter(4, [lo / ny, min(hi / ny, 0.99)], btype="band", output="sos")
    return signal.sosfilt(sos, a).astype(np.float32)


def _bitcrush(a, bits=9, down_sr=16000):
    """Quantize + sample-rate-reduce (sample-and-hold) -> rugged, digitized,
    'industrial speaker cone' texture."""
    q = 2 ** (bits - 1)
    a = np.round(a * q) / q
    step = max(int(round(SR / down_sr)), 1)
    if step > 1:
        a = np.repeat(a[::step], step)[:len(a)]         # 16 kHz sample-and-hold
    return a.astype(np.float32)


def laptop_fx(a):
    """Full translator chain: band-pass + bitcrush/downsample + soft-clip drive."""
    if len(a) == 0:
        return a
    a = _bandpass(a)
    a = _bitcrush(a, bits=9, down_sr=16000)
    a = np.tanh(a * 1.6) / np.tanh(1.6)                  # mild clipping distortion
    m = np.abs(a).max()
    return (a / m * 0.95).astype(np.float32) if m > 0 else a


def speak_translated(text: str, pitch: int = 46, rate: int = 165,
                     gap_ms: float = 42.0) -> np.ndarray:
    """Rocky's ON-SHIP translator voice: each word synthesized IN ISOLATION (so it
    reads FLAT/declarative — no sentence intonation, tags like 'question' stay
    deadpan) and concatenated with 35-50ms micro-pauses (discrete data-blocks,
    hard word cuts), then run through the laptop_fx texture chain."""
    words = [w.strip(".,!?;:") for w in text.replace(",", " ").split()]
    words = [w for w in words if w]
    gap = np.zeros(int(SR * gap_ms / 1000), dtype=np.float32)
    segs = []
    for w in words:
        wv = speak(w, pitch=pitch, rate=rate, pitch_range=25)   # low range = flat
        segs.append(wv)
        segs.append(gap)
    raw = np.concatenate(segs) if segs else np.zeros(0, dtype=np.float32)
    return laptop_fx(raw)
