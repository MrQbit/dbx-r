"""G7 audio — BDX-A droidspeak voice (ROBOTS_SPEC.md §7, BDX track).

The FM/square beep-boop synth, emotion->sound map, and named vocabulary. Mirrors
tests/test_audio.py for Rocky's chord voice. Checks: finite audio of the expected
length, distinct emotions produce distinct audio, and full determinism.
"""

from __future__ import annotations

import numpy as np
import pytest

from bdx.audio import droidspeak
from bdx.audio.droidspeak import SR, EMOTIONS, VOCAB, syllable, emote, say, sentence


def test_syllable_is_finite_and_normalised():
    n_expected = int(150 * SR / 1000)
    a = syllable(330.0, 660.0, 150.0)
    assert a.shape[0] == n_expected
    assert np.all(np.isfinite(a))
    assert np.abs(a).max() <= 1.0 + 1e-6


def test_syllable_glide_changes_pitch():
    """A rising glide's second half should be higher-pitched (more zero-crossings)
    than its first half — portamento actually moves the frequency."""
    a = syllable(220.0, 880.0, 300.0, kind="square", warble=0.0)
    half = len(a) // 2
    zc_lo = np.sum(np.abs(np.diff(np.sign(a[:half]))) > 0)
    zc_hi = np.sum(np.abs(np.diff(np.sign(a[half:]))) > 0)
    assert zc_hi > zc_lo


def test_emote_returns_finite_audio_for_every_emotion():
    for name in EMOTIONS:
        a = emote(name, seed=0)
        assert a.size > 0
        assert np.all(np.isfinite(a))
        assert np.abs(a).max() <= 1.0 + 1e-6
        assert np.abs(a).max() > 0.1        # actually made sound


def test_n_syllables_controls_length():
    """More syllables -> longer audio (monotonic), for a fixed emotion+seed."""
    short = emote("neutral", seed=0, n_syllables=2)
    long = emote("neutral", seed=0, n_syllables=6)
    assert len(long) > len(short)


def test_distinct_emotions_produce_distinct_audio():
    """curious / happy / alarmed / sad must not collapse to the same waveform."""
    names = ["curious", "happy", "alarmed", "sad", "affirmative", "negative"]
    sigs = {n: emote(n, seed=0, n_syllables=3) for n in names}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = sigs[names[i]], sigs[names[j]]
            if len(a) != len(b):
                continue                    # different length -> already distinct
            assert not np.allclose(a, b), f"{names[i]} == {names[j]}"


def test_determinism_same_seed_same_audio():
    for name in EMOTIONS:
        a = emote(name, seed=11)
        b = emote(name, seed=11)
        assert np.array_equal(a, b)


def test_different_seed_can_vary():
    """Seeds should be able to change a multi-syllable phrase (not frozen)."""
    a = emote("neutral", seed=1)
    b = emote("neutral", seed=2)
    # may differ in length or content; assert they are not identical
    assert len(a) != len(b) or not np.array_equal(a, b)


def test_vocabulary_utterances_render():
    for word in VOCAB:
        a = say(word)
        assert a.size > 0 and np.all(np.isfinite(a)) and np.abs(a).max() > 0.1


def test_say_is_deterministic():
    for word in ("greeting", "yes", "no", "alarm"):
        assert np.array_equal(say(word), say(word))


def test_yes_and_no_differ():
    yes, no = say("yes"), say("no")
    m = min(len(yes), len(no))
    assert not np.allclose(yes[:m], no[:m])


def test_sentence_is_longer_than_its_parts_and_deterministic():
    line = sentence(["greeting", "question", "yes", "happy"])
    assert line.size > say("greeting").size
    assert np.all(np.isfinite(line))
    assert np.array_equal(line, sentence(["greeting", "question", "yes", "happy"]))


def test_unknown_emotion_raises():
    with pytest.raises(KeyError):
        emote("ecstatic")
