#!/usr/bin/env python3
"""Visual A/B: RMS energy + MFCC spectrogram, movie Rocky vs our generated voice.
Shows exactly where the film's audio drops to zero between words vs our curve.
Output PNG -> reference/ (derived from copyrighted audio -> gitignored)."""
import sys

import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SR = 22050
CLIPS = [
    ("MOVIE Rocky (clean, Boundaries)", "reference/audio/rocky_voice_clean.wav"),
    ("OURS — Rocky translated (english)", "docs/media/rocky_voice_english_only.wav"),
]


def main():
    fig, axes = plt.subplots(len(CLIPS), 2, figsize=(13, 5.5))
    for row, (name, path) in enumerate(CLIPS):
        y, _ = librosa.load(path, sr=SR, mono=True)
        # RMS energy over time
        rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=256)[0]
        t = librosa.times_like(rms, sr=SR, hop_length=256)
        ax = axes[row, 0]
        ax.fill_between(t, rms, color="#c0392b" if row == 0 else "#2980b9", alpha=0.85)
        ax.set_title(f"{name}\nRMS energy (word-gap structure)", fontsize=9)
        ax.set_xlabel("s"); ax.set_ylabel("RMS"); ax.set_ylim(0, max(rms.max(), 1e-3) * 1.1)
        # MFCC
        mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13)
        ax2 = axes[row, 1]
        librosa.display.specshow(mfcc, x_axis="time", sr=SR, hop_length=512, ax=ax2, cmap="magma")
        ax2.set_title("MFCC", fontsize=9)
    fig.suptitle("Voice A/B — movie Rocky (top) vs generated (bottom): note the film's "
                 "hard drops to ZERO between words", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = "reference/voice_rms_mfcc.png"
    fig.savefig(out, dpi=95); plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
