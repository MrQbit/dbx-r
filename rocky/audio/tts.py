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
_EVENT_WORD = 1                        # espeakEVENT_WORD


class _EId(ctypes.Union):
    _fields_ = [("name", ctypes.c_char_p), ("string", ctypes.c_char * 8),
                ("number", ctypes.c_int)]


class _EEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("unique_identifier", ctypes.c_uint),
                ("text_position", ctypes.c_int), ("length", ctypes.c_int),
                ("audio_position", ctypes.c_int), ("sample", ctypes.c_int),
                ("id", _EId)]


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


def _trim_silence(a, thr=0.02, margin_ms=8):
    """Trim leading/trailing near-silence from a word block (espeak pads the last
    word with end-of-phrase silence; short words get dead air) so the ~85ms gaps
    are the ONLY silence between words."""
    if len(a) == 0:
        return a
    env = np.abs(a)
    pk = env.max()
    if pk < 1e-6:
        return a
    above = np.where(env > thr * pk)[0]
    if len(above) == 0:
        return a
    m = int(SR * margin_ms / 1000)
    return a[max(above[0] - m, 0):min(above[-1] + m, len(a))]


def laptop_fx(a, normalize: bool = True, bits: int = 10, lo: float = 130.0,
              hi: float = 4200.0, down_sr: int = 18000):
    """Full translator chain: bitcrush/clip then band-pass. Applied PER-WORD (see
    speak_translated) so the band-pass IIR tail can't smear energy across the
    inter-word silence — the film drops to ABSOLUTE ZERO between words (discrete
    data-blocks). bitcrush/band-limit give the digitized speaker-cone texture;
    higher `hi`/`bits` = clearer, lower = more muffled/lo-fi."""
    if len(a) == 0:
        return a
    a = _bitcrush(a, bits=bits, down_sr=down_sr)
    a = np.tanh(a * 1.4) / np.tanh(1.4)                  # gentler clipping
    a = _bandpass(a, lo=lo, hi=hi)                       # keep top for consonant clarity
    if not normalize:
        return a.astype(np.float32)
    m = np.abs(a).max()
    return (a / m * 0.95).astype(np.float32) if m > 0 else a


def speak_with_words(text: str, pitch: int = 46, rate: int = 135,
                     voice: str = "en", pitch_range: int = 45):
    """Like speak(), but also returns espeak's WORD-boundary sample positions, so a
    naturally-articulated phrase can be split into per-word blocks afterward."""
    lib = _init()
    chunks, word_samples = [], []
    CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short),
                          ctypes.c_int, ctypes.POINTER(_EEvent))

    def _cb(wav, n, events):
        if n > 0:
            chunks.append(np.ctypeslib.as_array(wav, (n,)).copy())
        if events:
            i = 0
            while events[i].type != 0:                   # 0 = LIST_TERMINATED
                if events[i].type == _EVENT_WORD:
                    word_samples.append(int(events[i].sample))
                i += 1
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
        return np.zeros(0, dtype=np.float32), []
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    if _native_sr != SR:
        scale = SR / _native_sr
        word_samples = [int(s * scale) for s in word_samples]
        n_out = int(len(audio) * scale)
        audio = np.interp(np.linspace(0, len(audio), n_out, endpoint=False),
                          np.arange(len(audio)), audio).astype(np.float32)
    return audio, sorted(set(w for w in word_samples if 0 < w < len(audio)))


def speak_translated(text: str, pitch: int = 46, rate: int = 135,
                     gap_ms: float = 85.0, voice: str = "en-us",
                     fx: dict | None = None) -> np.ndarray:
    """Rocky's ON-SHIP translator voice. Synthesize the WHOLE phrase in one pass
    (punctuation stripped -> FLAT/declarative, tags deadpan) so espeak articulates
    words naturally with coarticulation; then SPLIT at word boundaries, TRIM each
    block's silence padding, and rejoin with ~85ms TRUE-ZERO gaps + per-block
    laptop_fx. Discrete data-blocks (film-measured) AND intelligible words.
    `voice` picks the espeak voice; `fx` overrides laptop_fx params (bits/lo/hi)."""
    fx = fx or {}
    clean = " ".join(w.strip(".,!?;:") for w in text.replace(",", " ").split()
                     if w.strip(".,!?;:"))
    audio, bounds = speak_with_words(clean, pitch=pitch, rate=rate,
                                     pitch_range=45, voice=voice)
    if len(audio) == 0:
        return audio
    starts = [0] + bounds
    ends = bounds + [len(audio)]
    gap = np.zeros(int(SR * gap_ms / 1000), dtype=np.float32)
    fade = max(int(SR * 0.006), 1)
    segs = []
    for s, e in zip(starts, ends):
        seg = _trim_silence(audio[s:e])                  # drop espeak's padding
        if len(seg) < 2 * fade:
            continue
        seg = laptop_fx(seg, normalize=False, **fx).copy()   # per-block -> gaps stay zero
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        segs.append(seg)
        segs.append(gap.copy())
    raw = np.concatenate(segs) if segs else np.zeros(0, dtype=np.float32)
    m = np.abs(raw).max()
    return (raw / m * 0.95).astype(np.float32) if m > 0 else raw
