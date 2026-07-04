#!/usr/bin/env bash
# Launch BDX-R training (BDX-A track, D-007) inside the pinned Isaac Lab 2.3.2
# container. Reuses BDX-R's own Isaac Lab extension + task verbatim; we improve
# via training. Non-interactive / headless (Prime Directive #1).
#
# Usage: scripts/train_bdxr.sh <task> <num_envs> <max_iterations> [extra args...]
#   e.g. scripts/train_bdxr.sh Bdxr-Velocity-Flat-v0 64 5      # smoke
#        scripts/train_bdxr.sh Bdxr-Velocity-Flat-v0 4096 1500 # real run
set -euo pipefail
cd "$(dirname "$0")/.."

TASK="${1:-Bdxr-Velocity-Flat-v0}"
NUM_ENVS="${2:-64}"
MAX_ITER="${3:-5}"
shift $(( $# < 3 ? $# : 3 )) || true
EXTRA=("$@")

IMG="$(cat orchestrator/.isaac_image_digest)"
BDXR="$PWD/third_party/bdx_r_isaaclab"
[ -d "$BDXR" ] || { echo "fetch upstream first: scripts/fetch_upstream.sh"; exit 1; }
mkdir -p runs

echo "[train] task=$TASK envs=$NUM_ENVS iters=$MAX_ITER"
docker run --rm --gpus all \
  -e OMNI_KIT_ACCEPT_EULA=YES -e OMNI_KIT_ALLOW_ROOT=1 \
  -e LD_PRELOAD=/lib/aarch64-linux-gnu/libgomp.so.1 \
  -v "$BDXR:/workspace/bdxr" \
  -v "$PWD/runs:/workspace/isaaclab/logs" \
  --entrypoint bash "$IMG" -c "
    set -e
    cd /workspace/isaaclab
    ./isaaclab.sh -p -m pip install -q -e /workspace/bdxr/source/BDXR
    ./isaaclab.sh -p /workspace/bdxr/scripts/rsl_rl/train.py \
      --task=$TASK --headless --num_envs $NUM_ENVS --max_iterations $MAX_ITER ${EXTRA[*]}
    chown -R $(id -u):$(id -g) /workspace/isaaclab/logs 2>/dev/null || true
  "
