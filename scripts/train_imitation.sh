#!/usr/bin/env bash
# BDX-A imitation learning — movie-accurate MOTION via reference-motion tracking
# (mjlab / MuJoCo-Warp, host-side, D-007 reuse of BDX-R). The policy learns to
# track a reference clip (the "green ghost"), not just hit a velocity command —
# the path to the characteristic BDX gait/head motion.
#
# Uses .venv-mjlab (mjlab + warp). Reference motion defaults to BDX-R's shipped
# fake-walk; swap in real BDX-characteristic clips later via MOTION.
#
# Usage: scripts/train_imitation.sh [task] [num_envs] [max_iters]
set -euo pipefail
cd "$(dirname "$0")/.."

TASK="${1:-Mjlab-Imitation-Flat-BDX-R}"
NUM_ENVS="${2:-4096}"
MAX_ITER="${3:-3000}"
MOTION="${MOTION:-$PWD/third_party/bdx_r_mjlab/data/fake-walk.npz}"

[ -f "$MOTION" ] || { echo "motion file missing: $MOTION (run scripts/fetch_upstream.sh)"; exit 1; }
export MUJOCO_GL=egl

echo "[imitation] task=$TASK envs=$NUM_ENVS iters=$MAX_ITER motion=$(basename "$MOTION")"
.venv-mjlab/bin/bdx_r_train "$TASK" \
  --env.commands.motion.motion-file "$MOTION" \
  --env.scene.num-envs "$NUM_ENVS" \
  --agent.max-iterations "$MAX_ITER"
