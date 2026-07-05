#!/usr/bin/env bash
# BDX-A imitation learning — movie-accurate MOTION via reference-motion tracking
# (mjlab / MuJoCo-Warp, host-side, D-007 reuse of BDX-R). The policy learns to
# track a reference "green ghost", not just a velocity command — the path to the
# characteristic BDX gait.
#
# The IMITATION task uses a built-in polynomial reference (pkl); the -Legs variant
# ships its reference (polynomial_coefficients_legs.pkl) so it runs out of the box.
# TRACKING tasks instead take a motion clip via MOTION=<file.npz>.
#
# Usage: scripts/train_imitation.sh [task] [num_envs] [max_iters]
set -euo pipefail
cd "$(dirname "$0")/.."

TASK="${1:-Mjlab-Imitation-Flat-BDX-R-Legs}"
NUM_ENVS="${2:-4096}"
MAX_ITER="${3:-3000}"
export MUJOCO_GL=egl
export WANDB_MODE=disabled          # no W&B login; rsl_rl still writes local TB logs

ARGS=(--env.scene.num-envs "$NUM_ENVS" --agent.max-iterations "$MAX_ITER")
# Tracking tasks need an explicit motion clip; imitation tasks use their own pkl.
if [[ "$TASK" == *Tracking* ]]; then
  MOTION="${MOTION:-$PWD/third_party/bdx_r_mjlab/data/fake-walk.npz}"
  ARGS+=(--env.commands.motion.motion-file "$MOTION")
fi

echo "[imitation] task=$TASK envs=$NUM_ENVS iters=$MAX_ITER"
.venv-mjlab/bin/bdx_r_train "$TASK" "${ARGS[@]}"
