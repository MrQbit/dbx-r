#!/usr/bin/env bash
# Launch ROCKY-5 training in the pinned Isaac Lab 2.3.2 container. Rocky is our
# own design (no upstream) — the duet_tasks extension (rocky/isaac) reuses Isaac
# Lab's generic velocity locomotion env with Rocky's URDF + STS3215 actuators.
#
# Usage: scripts/train_rocky.sh <num_envs> <max_iterations> [extra args...]
set -euo pipefail
cd "$(dirname "$0")/.."

NUM_ENVS="${1:-64}"
MAX_ITER="${2:-5}"
shift $(( $# < 2 ? $# : 2 )) || true
EXTRA=("$@")

IMG="$(cat orchestrator/.isaac_image_digest)"
make -s _desc ROBOT=rocky >/dev/null    # ensure rocky.urdf is fresh
mkdir -p runs

echo "[train-rocky] envs=$NUM_ENVS iters=$MAX_ITER"
docker run --rm --gpus all \
  -e OMNI_KIT_ACCEPT_EULA=YES -e OMNI_KIT_ALLOW_ROOT=1 \
  -e LD_PRELOAD=/lib/aarch64-linux-gnu/libgomp.so.1 \
  -e PYTHONPATH=/workspace/duet/rocky/isaac \
  -v "$PWD:/workspace/duet" \
  -v "$PWD/runs:/workspace/duet/logs" \
  -w /workspace/duet \
  --entrypoint bash "$IMG" -c "
    set -e
    cd /workspace/isaaclab
    ./isaaclab.sh -p -m pip install -q -e /workspace/duet/rocky/isaac
    cd /workspace/duet
    /workspace/isaaclab/isaaclab.sh -p /workspace/duet/rocky/isaac/train.py \
      --task=Duet-Rocky-Flat-v0 --headless --num_envs $NUM_ENVS --max_iterations $MAX_ITER ${EXTRA[*]}
    chown -R $(id -u):$(id -g) /workspace/duet/logs 2>/dev/null || true
  "
