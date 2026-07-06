#!/usr/bin/env bash
# PROJECT DUET — common Jetson (Orin Nano, JetPack 6, aarch64) on-robot setup.
# Installs the shared runtime: policy inference (ONNX Runtime), CAN servo bus,
# STT (faster-whisper), audio I/O. Robot-specific voice deps are added by
# setup_rocky.sh / setup_bdx.sh. Idempotent; run once per flash.
set -euo pipefail

echo "=== DUET Jetson common setup ==="
sudo apt-get update
# system deps: CAN utilities, audio, ffmpeg (TTS), build basics
sudo apt-get install -y python3-venv python3-pip can-utils ffmpeg \
    libportaudio2 libsndfile1 libespeak-ng1 i2c-tools

# CAN interface for the Robstride/EduLite motor bus (adjust to your USB-CAN adapter).
# For a Waveshare USB-CAN: it enumerates as can0 via slcan or a native gs_usb driver.
sudo modprobe can can_raw gs_usb 2>/dev/null || true

# Python venv for the robot brain
python3 -m venv ~/duet-venv
source ~/duet-venv/bin/activate
pip install --upgrade pip
# onnxruntime-gpu for Jetson comes from the NVIDIA index (JetPack-matched wheel);
# fall back to CPU wheel if unavailable.
pip install onnxruntime-gpu 2>/dev/null || pip install onnxruntime
pip install numpy python-can faster-whisper sounddevice soundfile scipy

echo "=== common setup done. Next: setup_rocky.sh OR setup_bdx.sh ==="
