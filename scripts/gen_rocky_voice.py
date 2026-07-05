#!/usr/bin/env python3
"""Render ROCKY-5 translated-voice demos: Eridian chord (quiet, back) + English TTS
(front), mixed. Also a chord-ONLY (native Eridian) and English-ONLY clip so the two
layers are audible separately. WAVs -> docs/media/rocky_voice_*.wav."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rocky.audio import voice

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "media")
os.makedirs(OUT, exist_ok=True)

LINES = [
    ("hello Grace", "excited", "statement", "greeting"),
    ("you sleep now", "curious", "question", "question"),
    ("the humans are here", "solemn", "statement", "observe"),
    ("amaze amaze amaze", "excited", "statement", "amaze"),
    ("Grace Rocky save stars", "agree", "statement", "bond"),
]


def main():
    for text, emo, tag, name in LINES:
        both = voice.translate(text, emotion=emo, tag=tag)
        voice.write_wav(both, os.path.join(OUT, f"rocky_voice_{name}.wav"))
        print(f"rocky_voice_{name}.wav  [{emo}/{tag}]  '{voice.persona.say(text, tag)}'")
    # layers of one line, so you can hear the translation stack
    text = "you sleep now"
    voice.write_wav(voice.translate(text, "curious", "question", english=False),
                    os.path.join(OUT, "rocky_voice_eridian_only.wav"))
    voice.write_wav(voice.translate(text, "curious", "question", eridian_gain=0.0),
                    os.path.join(OUT, "rocky_voice_english_only.wav"))
    print("also: rocky_voice_eridian_only.wav (native, back track) + rocky_voice_english_only.wav (front track)")


if __name__ == "__main__":
    main()
