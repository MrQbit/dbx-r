"""ROCKY-5 neural voice — zero-shot clone of the film Rocky (Coqui TTS).

The good voice: instead of espeak+DSP, this clones the actual film Rocky with a
neural model from ~2 min of reference audio. HYBRID for on-board (Jetson) use:
  * XTTS-v2 (heavier, better) generates a fixed-vocabulary CACHE offline -> instant
    playback, zero runtime compute (best for greetings / common lines).
  * YourTTS (light, 406MB, faster-than-real-time on CPU) synthesizes anything not
    cached, live. It's the deployable on-board engine (see docs bench: XTTS RTF ~4.6
    on CPU vs YourTTS ~0.3).
Dual-track per the design: neural English clone (front) + quiet Eridian chord (back).

Requires the .venv-tts env (coqui-tts). Reference audio + models are gitignored
(copyrighted / large).

ATTRIBUTION — the text-transform rules + clone approach are adapted (CC BY-NC 4.0)
from Pedram Amini's Rocky-Voice gist and Kuberwastaken/rocky-tts. See docs/LICENSES.md.
Non-commercial, personal use only.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
REFERENCE = os.path.join(_ROOT, "reference/external/rocky-tts/assets/rocky_training_audio_scrubbed.wav")
CACHE_DIR = os.path.join(_ROOT, "reference/voice_cache")     # gitignored
SR = 22050

# --- text transform (adapted from Pedram Amini / Kuberwastaken, CC BY-NC 4.0) ---
ARTICLES = {"a", "an", "the"}
AUXILIARIES = {"is", "are", "was", "were", "will", "would", "should", "could",
               "do", "does", "did", "has", "have", "had", "am", "been", "being"}
CONTRACTIONS = {
    "i'm": "I", "i've": "I", "i'll": "I", "i'd": "I", "you're": "you",
    "you've": "you", "you'll": "you", "we're": "we", "we've": "we", "we'll": "we",
    "they're": "they", "it's": "it", "that's": "that", "there's": "there",
    "what's": "what", "don't": "no", "doesn't": "no", "didn't": "no",
    "can't": "no can", "cannot": "no can", "won't": "no will", "isn't": "is not",
    "haven't": "no have", "hasn't": "no have", "hadn't": "no have",
}
EMPHASIS_MAP = {
    "amazing": "amaze amaze amaze", "wonderful": "amaze amaze amaze",
    "incredible": "amaze amaze amaze", "excellent": "good good good",
    "great": "good good good", "terrible": "bad bad bad", "awful": "bad bad bad",
    "happy": "happy happy happy", "sad": "sad sad sad", "angry": "angry angry angry",
    "scared": "scared scared scared", "afraid": "scared scared scared",
    "dangerous": "danger danger danger", "absolutely": "yes yes yes",
    "definitely": "yes yes yes", "really": "very", "extremely": "very very",
}
PHRASE_MAP = [
    (r"i don'?t understand", "no understand"), (r"i don'?t know", "I not know"),
    (r"what do you mean", "what mean"), (r"what does that mean", "what mean"),
    (r"going to ", ""), (r"want to ", "want "), (r"need to ", "need "),
    (r"have to ", "must "), (r"try to ", "try "), (r"able to ", "can "),
    (r"right now", "now"), (r"however", "but"), (r"therefore", "so"),
    (r"approximately", "about"), (r"i think that", "I think"),
    (r"goodbye", "see you later. But I no see you later"),
]


def rocky_transform(text: str) -> str:
    """English -> Rocky-speak (drop articles/aux, contractions, emphasis-tripling,
    ', question?' suffix). Adapted from the CC BY-NC 4.0 upstreams."""
    if not text or not text.strip():
        return text
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        s = s.strip()
        if not s:
            continue
        is_q = s.endswith("?")
        for pat, rep in PHRASE_MAP:
            s = re.sub(pat, rep, s, flags=re.IGNORECASE)
        words, new = s.split(), []
        for w in words:
            lo = w.lower().rstrip(".,!?;:")
            punct = w[len(lo):]
            if lo in CONTRACTIONS:
                new.append(CONTRACTIONS[lo] + punct)
            elif lo in EMPHASIS_MAP:
                new.append(EMPHASIS_MAP[lo] + punct)
            elif lo in ARTICLES:
                continue
            elif lo in AUXILIARIES and new:
                continue
            else:
                new.append(w)
        s = re.sub(r"\s+", " ", " ".join(new)).strip()
        if is_q and "question" not in s.lower():
            s = s.rstrip("?").strip() + ", question?"
        if s:
            s = s[0].upper() + s[1:]
        out.append(s)
    return re.sub(r"\s+([.,!?])", r"\1", re.sub(r"\s+", " ", " ".join(out))).strip()


# --- neural synthesis (Coqui) -------------------------------------------------
_ENGINES = {"yourtts": "tts_models/multilingual/multi-dataset/your_tts",
            "xtts": "tts_models/multilingual/multi-dataset/xtts_v2"}
_loaded: dict = {}


def _patch_torchaudio():
    """Bypass torchcodec (unavailable on aarch64) — load audio via soundfile."""
    import soundfile as sf
    import torch
    import torchaudio

    def _load(path, *a, **k):
        d, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return torch.from_numpy(d.T).contiguous(), sr
    torchaudio.load = _load


def _engine(name: str):
    if name not in _loaded:
        os.environ["COQUI_TOS_AGREED"] = "1"
        _patch_torchaudio()
        import torch
        from TTS.api import TTS
        dev = "cuda" if (name == "xtts" and torch.cuda.is_available()) else "cpu"
        _loaded[name] = TTS(_ENGINES[name], progress_bar=False).to(dev)
    return _loaded[name]


def _synth(rocky_text: str, engine: str, out_path: str, speed: float = 1.5):
    tts = _engine(engine)
    tmp = out_path + ".raw.wav"
    tts.tts_to_file(text=rocky_text, speaker_wav=REFERENCE, language="en", file_path=tmp)
    if abs(speed - 1.0) > 1e-3:
        subprocess.run(["ffmpeg", "-y", "-i", tmp, "-filter:a", f"atempo={speed}",
                        out_path], capture_output=True)
        os.remove(tmp)
    else:
        os.replace(tmp, out_path)
    return out_path


def _cache_path(rocky_text: str) -> str:
    key = hashlib.sha1(rocky_text.encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{key}.wav")


def speak(text: str, out_path: str, speed: float = 1.5, transform: bool = True,
          prefer_cache: bool = True) -> str:
    """HYBRID: transform -> if an XTTS cache hit exists use it (instant), else
    synthesize live with YourTTS. Returns out_path (the English clone track)."""
    rt = rocky_transform(text) if transform else text
    cached = _cache_path(rt)
    if prefer_cache and os.path.exists(cached):
        subprocess.run(["ffmpeg", "-y", "-i", cached, out_path], capture_output=True)
        return out_path
    return _synth(rt, "yourtts", out_path, speed)


def build_cache(phrases, speed: float = 1.5):
    """Pre-generate the fixed-vocab cache with XTTS (offline, best quality)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    made = []
    for p in phrases:
        rt = rocky_transform(p)
        _synth(rt, "xtts", _cache_path(rt), speed)
        made.append((p, rt))
    return made


# --- Eridian dual-track overlay (lean numpy — no scipy/espeak) -----------------
_PITCHES = np.array([110.0, 130.81, 146.83, 164.81, 196.0, 220.0, 261.63, 293.66])


def _eridian_bed(n: int, seed: int = 0) -> np.ndarray:
    """Quiet organic chord bed to sit UNDER the English clone (the 'native' voice)."""
    rng = np.random.RandomState(seed)
    freqs = _PITCHES[rng.choice(len(_PITCHES), 3, replace=False)]
    t = np.arange(n) / SR
    a = np.zeros(n, dtype=np.float32)
    for f in freqs:
        for k, amp in enumerate([1.0, 0.5, 0.3], 1):
            a += amp * np.sin(2 * np.pi * f * k * (1 + 0.003 * (k - 1)) * t)
    a += 0.35 * np.sin(2 * np.pi * min(freqs) / 2 * t)          # sub-bass
    env = np.minimum(1.0, np.minimum(t / 0.1, (t[-1] - t) / 0.2 + 0.0))
    return (a / (np.abs(a).max() + 1e-9) * env).astype(np.float32)


def dual_track(english_wav: str, out_path: str, eridian_gain: float = 0.28) -> str:
    """Mix the quiet Eridian chord bed UNDER the neural English clone (front)."""
    import soundfile as sf
    eng, sr = sf.read(english_wav, dtype="float32", always_2d=False)
    if eng.ndim > 1:
        eng = eng.mean(1)
    bed = _eridian_bed(len(eng))
    mix = eng + eridian_gain * bed[:len(eng)]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.95
    sf.write(out_path, mix.astype(np.float32), sr)
    return out_path
