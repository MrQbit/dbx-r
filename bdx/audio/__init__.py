"""BDX-A audio — expressive "droidspeak" voice (beeps/boops/warbles/chirps).

Mirrors rocky/audio/ but for the Disney-BDX droid voice. See droidspeak.py.
"""

from __future__ import annotations

from bdx.audio.droidspeak import (
    SR,
    EMOTIONS,
    VOCAB,
    Voice,
    syllable,
    chirp,
    render,
    emote,
    say,
    sentence,
)

__all__ = [
    "SR",
    "EMOTIONS",
    "VOCAB",
    "Voice",
    "syllable",
    "chirp",
    "render",
    "emote",
    "say",
    "sentence",
]
