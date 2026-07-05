#!/usr/bin/env python3
"""Pre-generate the fixed-vocabulary Rocky voice cache with XTTS (offline, best
quality) so the on-board robot can play common lines instantly (zero compute) and
fall back to live YourTTS for anything else. Run in .venv-tts. Cache -> gitignored
reference/voice_cache/."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rocky.audio import neural_tts as nt

VOCAB = [
    "Hello.", "Question?", "Yes.", "No.", "Good good good.", "Amaze amaze amaze!",
    "I don't understand.", "You sleep now.", "Grace, Rocky save stars.",
    "I fix ship.", "Fist my bump.", "Danger!", "Thank you, Grace.",
]

if __name__ == "__main__":
    made = nt.build_cache(VOCAB)
    for orig, rt in made:
        print(f"cached: '{orig}' -> '{rt}'")
    print(f"\n{len(made)} phrases cached (XTTS) in {nt.CACHE_DIR}")
