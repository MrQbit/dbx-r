#!/usr/bin/env bash
# BDX-A on-Jetson setup — adds the DROIDSPEAK voice (beeps/boops sound effects).
# Much lighter than Rocky's neural clone: droidspeak is a pure-numpy synth, so no
# TTS model needed. Run setup_common.sh first.
set -euo pipefail
source ~/duet-venv/bin/activate

echo "=== BDX-A droidspeak setup ==="
# Droidspeak = numpy additive/FM synth (bdx/audio/droidspeak.py) — no model download.
pip install numpy soundfile scipy

# BDX's code (copy from the repo):
#   ~/duet/bdx/audio/droidspeak.py    (beep/boop synth + emotion map + vocabulary)
#   ~/duet/rocky/audio/synth.py       (shared SR constant)
echo ">> copy ~/duet/bdx and ~/duet/rocky/audio from the repo"
echo ">> copy the exported policy:  scp bdx.onnx jetson:~/bdx.onnx"

echo "=== BDX-A ready. Run: python ~/duet/deploy/jetson/brain.py --robot bdx ==="
