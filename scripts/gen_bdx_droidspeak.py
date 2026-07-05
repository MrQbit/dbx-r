#!/usr/bin/env python3
"""Render BDX-A droidspeak demo WAVs (ROBOTS_SPEC.md §7, BDX track -> docs/media/).

The named vocabulary utterances (greeting/question/happy/alarm/...) plus a short
'spoken' sentence, so you can HEAR BDX-A's beep-boop voice next to Rocky's chords.
22.05 kHz mono. Deterministic.
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bdx.audio.droidspeak import SR, say, sentence  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "media"


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    demos = {
        "greeting": say("greeting"),
        "question": say("question"),
        "happy": say("happy"),
        "alarm": say("alarm"),
        # a short "sentence": greet, ask, affirm, get excited
        "sentence": sentence(["greeting", "question", "yes", "happy"]),
    }
    for name, audio in demos.items():
        p = OUT / f"bdx_droidspeak_{name}.wav"
        _write_wav(p, audio)
        print(f"[bdx-audio] {p.relative_to(OUT.parent.parent)}  ({len(audio) / SR:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
