#!/usr/bin/env python3
"""Pre-generate the fixed-vocabulary Rocky voice cache with XTTS (offline, best
quality) so the on-board robot can play common lines instantly (zero compute) and
fall back to live YourTTS for anything else. Run in .venv-tts. Cache -> gitignored
reference/voice_cache/."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rocky.audio import neural_tts as nt

# Common-question RESPONSES in Rocky's voice (the instant-play set). Anything not
# here falls back to live YourTTS. Grouped: social / identity / status / capability /
# comprehension / emotion / task / movie signatures.
VOCAB = [
    # social
    "Hello.", "Hello, friend.", "Goodbye.", "Thank you.", "Thank you, Grace.",
    "Friend. Friend.", "Fist my bump.", "Yes.", "No.", "Maybe.",
    # identity
    "I am Rocky.", "Rocky. Eridian.", "I am your friend.",
    # status
    "Good good good.", "I am well.", "Tired tired.", "Happy happy.",
    # capability / task
    "Yes. Rocky can help.", "I fix. I build.", "I look.", "I come.",
    "Wait.", "Ready ready.", "Follow me.",
    # comprehension
    "I don't understand.", "Again? Question?", "I hear you.",
    # emotion / alert
    "Amaze amaze amaze!", "Danger!", "Sad.",
    # movie signatures
    "Question?", "You sleep now.", "Grace, Rocky save stars.", "I fix ship.",
]

if __name__ == "__main__":
    made = nt.build_cache(VOCAB)
    for orig, rt in made:
        print(f"cached: '{orig}' -> '{rt}'")
    print(f"\n{len(made)} phrases cached (XTTS) in {nt.CACHE_DIR}")
