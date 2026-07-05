#!/usr/bin/env python3
"""A/B acoustic comparison: our generated Rocky voice vs a reference movie clip.

Reference clips (reference/audio/, gitignored — copyrighted, private analysis only)
are full scene mixes, so whole-clip stats are polluted by music/dialogue/SFX. Pass
a --start/--dur window to focus on a Rocky line for a precise comparison.

Features (scipy/numpy, no librosa): spectral centroid, band-energy split
(sub-bass <200 / mid / presence 2-4k / air >4k), spectral flatness, zero-crossing
rate. Also writes a side-by-side spectrogram PNG.
"""
import argparse
import glob
import os
import wave

import numpy as np
from scipy import signal

SR = 22050


def load(path, start=0.0, dur=None):
    w = wave.open(path, "rb")
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
    if w.getnchannels() == 2:
        a = a.reshape(-1, 2).mean(axis=1)
    a /= 32768.0
    if sr != SR:
        n = int(len(a) * SR / sr)
        a = np.interp(np.linspace(0, len(a), n, endpoint=False), np.arange(len(a)), a).astype(np.float32)
    if start or dur:
        s = int(start * SR)
        e = int((start + dur) * SR) if dur else len(a)
        a = a[s:e]
    return a


def features(a):
    n, hop = 2048, 1024
    win = np.hanning(n)
    cents, flat, bands = [], [], []
    for i in range(0, max(len(a) - n, 1), hop):
        seg = a[i:i + n] * win
        sp = np.abs(np.fft.rfft(seg)) + 1e-9
        fr = np.fft.rfftfreq(n, 1 / SR)
        if sp.sum() < 1e-4:
            continue
        cents.append((sp * fr).sum() / sp.sum())
        flat.append(np.exp(np.log(sp).mean()) / sp.mean())        # spectral flatness
        e = sp ** 2
        tot = e.sum()
        bands.append([e[fr < 200].sum() / tot,
                      e[(fr >= 200) & (fr < 2000)].sum() / tot,
                      e[(fr >= 2000) & (fr < 4000)].sum() / tot,
                      e[fr >= 4000].sum() / tot])
    bands = np.array(bands)
    zcr = np.mean(np.abs(np.diff(np.sign(a)))) / 2
    return {"centroid": float(np.mean(cents)), "flatness": float(np.mean(flat)),
            "zcr": float(zcr),
            "sub<200": float(bands[:, 0].mean()), "mid": float(bands[:, 1].mean()),
            "presence2-4k": float(bands[:, 2].mean()), "air>4k": float(bands[:, 3].mean())}


def spectrogram_png(clips, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    fig, axes = plt.subplots(len(clips), 1, figsize=(9, 2.4 * len(clips)))
    if len(clips) == 1:
        axes = [axes]
    for ax, (name, a) in zip(axes, clips):
        f, t, Sxx = signal.spectrogram(a, SR, nperseg=1024)
        ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-10), shading="gouraud", cmap="magma")
        ax.set_ylim(0, 5000); ax.set_ylabel("Hz"); ax.set_title(name, fontsize=9)
    axes[-1].set_xlabel("s")
    fig.tight_layout(); fig.savefig(out, dpi=90); plt.close(fig)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--ref", default=None, help="reference wav (default: all in reference/audio)")
    args = ap.parse_args()

    refs = [args.ref] if args.ref else sorted(glob.glob("reference/audio/*.wav"))
    gen = "docs/media/rocky_voice_english_only.wav"
    keys = ["centroid", "sub<200", "mid", "presence2-4k", "air>4k", "flatness", "zcr"]
    print(f"{'clip':<34}" + "".join(f"{k:>13}" for k in keys))
    rows = []
    for path in refs + [gen]:
        a = load(path, args.start if path in refs else 0, args.dur if path in refs else None)
        ff = features(a)
        rows.append((os.path.basename(path), a))
        tag = " (window)" if (path in refs and args.dur) else ""
        print(f"{os.path.basename(path) + tag:<34}" + "".join(f"{ff[k]:>13.3f}" for k in keys))
    png = spectrogram_png(rows, "reference/voice_compare.png")
    print("spectrogram:", png or "(matplotlib unavailable)")
