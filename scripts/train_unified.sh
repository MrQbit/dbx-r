#!/usr/bin/env bash
# UNIFIED gait+terrain training in the pinned Isaac Lab 2.3.2 container.
# One policy per robot learns the reference GAIT (imitation reward) AND rough-TERRAIN
# traversal (command-relative curriculum fix). Both robots in Isaac (weights don't
# cross sims, so mjlab imitation isn't portable — this is the unified path).
#
# Usage: scripts/train_unified.sh <rocky|bdx> <num_envs> <max_iterations> [extra...]
set -euo pipefail
cd "$(dirname "$0")/.."

ROBOT="${1:-rocky}"
NUM_ENVS="${2:-4096}"
MAX_ITER="${3:-6000}"
shift $(( $# < 3 ? $# : 3 )) || true
EXTRA=("$@")

IMG="$(cat orchestrator/.isaac_image_digest)"
mkdir -p runs

if [ "$ROBOT" = "rocky" ]; then
  TASK="Duet-Rocky-Imitate-Rough-v0"
  make -s _desc ROBOT=rocky >/dev/null           # ensure rocky.urdf fresh
  PYPATH="/workspace/duet/rocky/isaac"
  BDX_INSTALL="true"
elif [ "$ROBOT" = "bdx" ]; then
  TASK="Duet-Bdx-Imitate-Rough-v0"
  PYPATH="/workspace/duet/rocky/isaac:/workspace/duet/third_party/bdx_r_isaaclab/source/BDXR"
  BDX_INSTALL="./isaaclab.sh -p -m pip install -q -e /workspace/duet/third_party/bdx_r_isaaclab/source/BDXR || true"
else
  echo "unknown robot: $ROBOT (use rocky|bdx)"; exit 2
fi

echo "[train-unified] robot=$ROBOT task=$TASK envs=$NUM_ENVS iters=$MAX_ITER"
docker run --rm --gpus all \
  -e OMNI_KIT_ACCEPT_EULA=YES -e OMNI_KIT_ALLOW_ROOT=1 \
  -e LD_PRELOAD=/lib/aarch64-linux-gnu/libgomp.so.1 \
  -e PYTHONPATH="$PYPATH" \
  -v "$PWD:/workspace/duet" \
  -v "$PWD/runs:/workspace/duet/logs" \
  -w /workspace/duet \
  --entrypoint bash "$IMG" -c "
    set -e
    cd /workspace/isaaclab
    ./isaaclab.sh -p -m pip install -q -e /workspace/duet/rocky/isaac
    $BDX_INSTALL
    cd /workspace/duet
    /workspace/isaaclab/isaaclab.sh -p /workspace/duet/rocky/isaac/train.py \
      --task=$TASK --headless --num_envs $NUM_ENVS --max_iterations $MAX_ITER ${EXTRA[*]}
    chown -R $(id -u):$(id -g) /workspace/duet/logs 2>/dev/null || true
  "
