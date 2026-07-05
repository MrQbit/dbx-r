"""BDX-A "droidspeak" expressive voice (ROBOTS_SPEC.md §7, BDX track).

Where ROCKY-5 speaks in flute-like musical CHORDS (see rocky/audio/synth.py),
BDX-A is a Disney-BDX / astromech droid: beeps, boops, warbles, chirps. A
retro-droid FM/square timbre with pitch GLIDES (portamento), vibrato/FM
WARBLES, and fast CHIRPS, sequenced into 2-6 syllable "talking" phrases.

Additive/FM synth, numpy, 22.05 kHz mono, WAV via the `wave` module — same
conventions as Rocky's synth so the two voices share tooling. Emotion drives a
(pitch contour, speed, timbre) mapping the way persona.py drives Rocky's chords.
Every utterance is deterministic given a seed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SR = 22050

# Droid register — a bit higher/brighter than Rocky's G2-G4, for the chirpy
# astromech feel. Base pitches (Hz) syllables glide between.
BASE_HZ = 330.0                 # ~E4, the neutral "talking" centre
PITCH_LO = 180.0                # floor for grave/negative blips
PITCH_HI = 1200.0              # ceiling for excited chirps

# Vibrato/warble defaults (FM of the fundamental).
WARBLE_HZ = 14.0                # fast droid warble (Rocky's vibrato is 5 Hz)
WARBLE_CENTS = 35.0             # ± depth in cents

# ADSR (ms) — snappy, so syllables read as distinct beeps not sustained notes.
ADSR_MS = (6.0, 40.0, 0.75, 30.0)   # attack, decay, sustain-level, release


# --------------------------------------------------------------------------
# low-level synthesis
# --------------------------------------------------------------------------
def _adsr(n: int, sr: int = SR) -> np.ndarray:
    """Snappy ADSR, scaled down to always leave a sustain plateau (cf. Rocky)."""
    a, d, s, r = ADSR_MS
    note_ms = n / sr * 1000
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


def _timbre(phase: np.ndarray, kind: str, fm_index: float) -> np.ndarray:
    """Retro-droid oscillator over an already-integrated phase (radians).

    kind:
      'fm'       — sine carrier frequency-modulated by a sine (bell/R2 tone)
      'square'   — band-limited-ish square via odd harmonics (blippy, robotic)
      'triangle' — softer triangle via odd harmonics with 1/k^2 rolloff
    Distinct from Rocky's inharmonic flute partials.
    """
    if kind == "fm":
        # modulator at 2x carrier -> metallic droid ring
        return np.sin(phase + fm_index * np.sin(2.0 * phase))
    if kind == "triangle":
        sig = np.zeros_like(phase)
        for k in (1, 3, 5, 7, 9):
            sig += ((-1) ** ((k - 1) // 2)) * np.sin(k * phase) / (k * k)
        return sig / (np.abs(sig).max() + 1e-9)
    # default: square-ish (odd harmonics, 1/k)
    sig = np.zeros_like(phase)
    for k in (1, 3, 5, 7, 9, 11):
        sig += np.sin(k * phase) / k
    return sig / (np.abs(sig).max() + 1e-9)


def syllable(f0: float, f1: float, dur_ms: float, *,
             kind: str = "square", warble: float = 0.0,
             warble_hz: float = WARBLE_HZ, fm_index: float = 2.0,
             sr: int = SR) -> np.ndarray:
    """One droid syllable: a beep that GLIDES from f0->f1 (portamento) with an
    optional WARBLE (vibrato/FM depth in cents) and a retro timbre.

    A rising glide reads "curious/question"; falling reads "no/sad"; flat with
    warble reads "talking". Returns a normalised, finite waveform.
    """
    n = max(int(dur_ms * sr / 1000), 1)
    t = np.arange(n) / sr
    # exponential (musical) glide between the two pitches
    frac = np.linspace(0.0, 1.0, n)
    inst_hz = f0 * (f1 / f0) ** frac
    if warble > 0.0:
        depth = (2 ** (warble / 1200.0)) - 1.0
        inst_hz = inst_hz * (1.0 + depth * np.sin(2 * np.pi * warble_hz * t))
    # integrate instantaneous frequency -> phase (glide-correct, no clicks)
    phase = 2 * np.pi * np.cumsum(inst_hz) / sr
    sig = _timbre(phase, kind, fm_index)
    sig = sig * _adsr(n, sr)
    return sig / (np.abs(sig).max() + 1e-9)


def chirp(f0: float, f1: float, dur_ms: float = 90.0, *,
          kind: str = "fm", sr: int = SR) -> np.ndarray:
    """A very short, fast glide — the classic astromech chirp/blip."""
    return syllable(f0, f1, dur_ms, kind=kind, warble=0.0, sr=sr)


def render(parts, gap_ms: float = 60.0, sr: int = SR) -> np.ndarray:
    """Concatenate syllables/chirps separated by short silent gaps.

    `parts` is a list of waveforms, or (waveform, gap_ms_override) tuples.
    Shorter default gap than Rocky (60 vs 180 ms) — droid speech is quicker.
    """
    out = []
    for p in parts:
        if isinstance(p, tuple):
            wav, g = p
        else:
            wav, g = p, gap_ms
        out.append(wav)
        out.append(np.zeros(int(g * sr / 1000)))
    audio = np.concatenate(out) if out else np.zeros(0)
    return audio / (np.abs(audio).max() + 1e-9) if audio.size else audio


# --------------------------------------------------------------------------
# emotion -> sound mapping (cf. rocky/persona.py EMOTIONS + voice_params)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Voice:
    """How an emotion shapes droidspeak."""
    contour: str                    # 'rise' | 'fall' | 'flat' | 'updown' | 'random'
    n_syllables: tuple              # (min, max) syllables in a phrase
    center: float                   # base pitch (Hz)
    span_cents: float               # glide span per syllable (± around center)
    dur_ms: float                   # nominal syllable duration
    warble: float                   # vibrato/FM depth (cents)
    kind: str = "square"            # timbre
    dissonance: float = 0.0         # detune spread for urgent/alarmed (cents)
    jitter: tuple = field(default=(0.0, 0.0))   # (pitch_cents, dur_frac) randomness


# The named emotional states. Contours picked to match the brief:
#   curious   — rising lilt (question)
#   happy     — fast bright ascending chirps
#   alarmed   — fast dissonant/urgent
#   sad       — slow descending, lower
#   affirmative / negative — single up-blip / down-blip
EMOTIONS = {
    "neutral":     Voice("flat",   (2, 4), BASE_HZ,       120.0, 150.0,  20.0, "square"),
    "curious":     Voice("rise",   (2, 3), BASE_HZ,       500.0, 150.0,  30.0, "triangle"),
    "happy":       Voice("rise",   (3, 5), BASE_HZ * 1.3, 350.0,  80.0,  25.0, "fm"),
    "excited":     Voice("updown", (4, 6), BASE_HZ * 1.4, 400.0,  70.0,  40.0, "fm"),
    "alarmed":     Voice("updown", (3, 5), BASE_HZ * 1.2, 250.0,  70.0,  90.0, "square",
                         dissonance=55.0, jitter=(60.0, 0.15)),
    "sad":         Voice("fall",   (2, 3), BASE_HZ * 0.7, 350.0, 260.0,  35.0, "triangle"),
    "affirmative": Voice("rise",   (1, 1), BASE_HZ,       700.0, 110.0,  10.0, "fm"),
    "negative":    Voice("fall",   (1, 1), BASE_HZ * 0.85, 700.0, 130.0, 15.0, "square"),
}


def _clip_hz(hz: float) -> float:
    return float(min(max(hz, PITCH_LO), PITCH_HI))


def _contour_pair(contour: str, center: float, span_cents: float,
                  step: int, n_steps: int, rng) -> tuple:
    """(f0, f1) glide endpoints for syllable `step` of `n_steps`, per contour.
    Ascending phrases march the center up across syllables; 'updown' zig-zags."""
    span = (2 ** (span_cents / 1200.0))
    # progressive center drift for multi-syllable ascending/urgent phrases
    prog = step / max(n_steps - 1, 1)
    if contour == "rise":
        c = center * (2 ** (prog * 700.0 / 1200.0))     # drift up ~a fifth overall
        return _clip_hz(c), _clip_hz(c * span)
    if contour == "fall":
        c = center * (2 ** (-prog * 500.0 / 1200.0))
        return _clip_hz(c), _clip_hz(c / span)
    if contour == "updown":
        up = (step % 2 == 0)
        c = center * (2 ** ((prog - 0.5) * 300.0 / 1200.0))
        return (_clip_hz(c), _clip_hz(c * span)) if up else (_clip_hz(c * span), _clip_hz(c))
    if contour == "random":
        c = center * (2 ** (rng.uniform(-0.5, 0.5) * span_cents / 1200.0))
        return _clip_hz(c), _clip_hz(c * (2 ** (rng.uniform(-0.5, 0.5) * span_cents / 600.0)))
    # flat: small wobble around center so consecutive syllables differ slightly
    c = center * (2 ** (rng.uniform(-0.15, 0.15) * span_cents / 1200.0))
    return _clip_hz(c), _clip_hz(c * (2 ** (rng.uniform(-0.1, 0.1))))


def emote(emotion: str, *, seed: int = 0, n_syllables: int | None = None,
          sr: int = SR) -> np.ndarray:
    """Render an expressive phrase for an emotional state -> audio waveform.

    Deterministic given (emotion, seed, n_syllables). The number of syllables is
    drawn from the Voice's range (seeded); each syllable is a glide whose
    endpoints follow the Voice's contour, with seeded pitch/duration jitter and,
    for 'alarmed', a dissonant detuned layer.
    """
    if emotion not in EMOTIONS:
        raise KeyError(f"unknown emotion {emotion!r}; have {sorted(EMOTIONS)}")
    v = EMOTIONS[emotion]
    rng = np.random.RandomState(seed)
    lo, hi = v.n_syllables
    n = n_syllables if n_syllables is not None else int(rng.randint(lo, hi + 1))
    parts = []
    for step in range(n):
        f0, f1 = _contour_pair(v.contour, v.center, v.span_cents, step, n, rng)
        jp, jd = v.jitter
        if jp:
            j = 2 ** (rng.uniform(-jp, jp) / 1200.0)
            f0, f1 = _clip_hz(f0 * j), _clip_hz(f1 * j)
        dur = v.dur_ms * (1.0 + (rng.uniform(-jd, jd) if jd else 0.0))
        wav = syllable(f0, f1, dur, kind=v.kind, warble=v.warble, sr=sr)
        if v.dissonance:
            det = 2 ** (v.dissonance / 1200.0)
            wav = wav + 0.7 * syllable(f0 * det, f1 * det, dur,
                                       kind=v.kind, warble=v.warble, sr=sr)
            wav = wav / (np.abs(wav).max() + 1e-9)
        # urgent phrases run tight; excited/happy quick; sad slow
        gap = 30.0 if emotion in ("alarmed", "excited", "happy") else 55.0
        parts.append((wav, gap))
    return render(parts, sr=sr)


# --------------------------------------------------------------------------
# named vocabulary (cf. Rocky's MOTIFS)
# --------------------------------------------------------------------------
# Each entry: the emotion it renders through + a fixed seed for a stable "word".
VOCAB = {
    "greeting":  ("curious", 7),        # a friendly rising lilt
    "question":  ("curious", 3),        # rising, inquisitive
    "yes":       ("affirmative", 1),    # up-blip
    "no":        ("negative", 1),       # down-blip
    "alarm":     ("alarmed", 5),        # urgent dissonant
    "happy":     ("happy", 2),          # bright ascending chirps
    "sad":       ("sad", 4),            # slow descending
    "hello":     ("happy", 9),          # excited greeting variant
}


def say(intent: str, *, seed: int | None = None, sr: int = SR) -> np.ndarray:
    """Render a named vocabulary utterance OR an emotion by name -> audio.

    `say("greeting")` / `say("yes")` use the fixed VOCAB word; `say("curious")`
    renders that emotion with the given (or default 0) seed. Deterministic.
    """
    if intent in VOCAB:
        emo, vseed = VOCAB[intent]
        return emote(emo, seed=vseed if seed is None else seed, sr=sr)
    return emote(intent, seed=0 if seed is None else seed, sr=sr)


def sentence(intents, *, gap_ms: float = 110.0, seed: int = 0,
             sr: int = SR) -> np.ndarray:
    """Stitch several utterances into one 'talking' line, with breath-like gaps.
    Each intent is offset by its position so repeated words vary slightly."""
    parts = []
    for i, intent in enumerate(intents):
        parts.append((say(intent, seed=seed + i, sr=sr), gap_ms))
    return render(parts, sr=sr)
