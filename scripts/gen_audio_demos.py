#!/usr/bin/env python3
"""Render ROCKY-5 chord-voice demo WAVs (ROBOTS_SPEC.md §7 -> docs/reports/audio/).

The reserved motifs (greeting/query/alarm/amaze) + a sample encoded phrase, so
you can HEAR Rocky's voice. 22.05 kHz mono.
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rocky.audio.synth import SR, render  # noqa: E402
from rocky.audio.codec import encode, MOTIFS  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "reports" / "audio"


def _write_wav(path: Path, audio: np.ndarray, sr: int = SR) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    demos = {name: render(encode([name])) for name in MOTIFS}
    # a sample "spoken" phrase
    demos["phrase_hello_grace"] = render(encode(["greeting", "hello", "grace", "friend", "query"]))
    for name, audio in demos.items():
        p = OUT / f"rocky_{name}.wav"
        _write_wav(p, audio)
        print(f"[audio] {p.relative_to(OUT.parent.parent)}  ({len(audio) / SR:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
