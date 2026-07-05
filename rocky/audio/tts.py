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
