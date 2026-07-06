#!/usr/bin/env bash
# ROCKY-5 on-Jetson setup — adds the neural VOICE (clone) on top of setup_common.sh.
# Rocky speaks the translated voice: YourTTS neural clone (live) + XTTS cache
# (instant common lines) + the Eridian chord bed. Run setup_common.sh first.
set -euo pipefail
source ~/duet-venv/bin/activate

echo "=== ROCKY-5 voice setup ==="
# Coqui TTS (YourTTS live + XTTS for the cache). YourTTS is ~406 MB and runs
# faster-than-real-time on the Orin Nano; XTTS (1.8 GB) is used offline to build
# the phrase cache (see scripts/gen_rocky_phrase_cache.py on the DGX).
pip install "coqui-tts==0.24.3" "transformers==4.44.0" "numpy<2" torch torchaudio soundfile

# Rocky's code + reference audio + prebuilt phrase cache (copy from the repo):
#   ~/duet/rocky/audio/            (neural_tts.py, synth.py, codec.py, voice.py)
#   ~/duet/rocky/persona.py
#   ~/duet/reference/external/rocky-tts/assets/rocky_training_audio_scrubbed.wav
#   ~/duet/reference/voice_cache/  (XTTS-generated common phrases)
echo ">> copy ~/duet/{rocky, reference/external/rocky-tts/assets, reference/voice_cache} from the repo"
echo ">> copy the exported policy:  scp rocky.onnx jetson:~/rocky.onnx"

echo "=== ROCKY-5 ready. Run: python ~/duet/deploy/jetson/brain.py --robot rocky ==="
