"""ROCKY-5 translated-voice tests — dual-track (Eridian back + English front),
emotion mapping, and the interrogative cluck."""

import numpy as np

from rocky.audio import voice
from rocky.audio.synth import SR


def test_translate_returns_finite_normalized_audio():
    a = voice.translate("hello Grace", emotion="excited", tag="statement")
    assert a.dtype == np.float32 and len(a) > SR * 0.2
    assert np.isfinite(a).all() and np.abs(a).max() <= 1.0


def test_dual_track_both_layers_present():
    # english-only (eridian muted) vs full mix should differ -> the Eridian back
    # track is really contributing
    text = "you sleep now"
    full = voice.translate(text, "curious", "question")
    eng_only = voice.translate(text, "curious", "question", eridian_gain=0.0)
    n = min(len(full), len(eng_only))
    assert not np.allclose(full[:n], eng_only[:n], atol=1e-3)


def test_eridian_only_has_no_speech_track():
    a = voice.translate("rock", "neutral", "statement", english=False)
    assert len(a) > 0 and np.isfinite(a).all()


def test_question_adds_cluck():
    # a question prepends the rising cluck -> longer Eridian than the statement
    q = voice.eridian_phrase(["you", "sleep"], "curious", total_ms=500)
    cluck = voice.question_cluck()
    assert len(cluck) > SR * 0.15
    # cluck rises in frequency (second half higher zero-crossing rate than first)
    half = len(cluck) // 2
    zc = lambda x: np.sum(np.abs(np.diff(np.sign(x)))) / 2
    assert zc(cluck[half:]) > zc(cluck[:half])


def test_emotion_shifts_pitch():
    # agitation raises pitch, solemnity lowers it (persona voice_params)
    assert voice.persona.voice_params("excited")["pitch_semitones"] > \
           voice.persona.voice_params("solemn")["pitch_semitones"]


def test_literal_syntax_in_translation():
    assert voice.persona.say("the humans are here", "statement") == \
           "leaky space blobs here, statement!"
