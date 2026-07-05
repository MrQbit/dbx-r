#!/usr/bin/env bash
# Queue the two UNIFIED gait+terrain runs on the single GPU: Rocky, then BDX.
# Each is independent — if one fails, the next still runs (logged, not &&).
# Usage: scripts/train_queue.sh [num_envs] [max_iters]
set -uo pipefail
cd "$(dirname "$0")/.."

NUM_ENVS="${1:-4096}"
MAX_ITER="${2:-6000}"
QLOG="runs/queue.status"
mkdir -p runs
: > "$QLOG"

for ROBOT in rocky bdx; do
  echo "[queue] $(date -u +%H:%M:%S) starting $ROBOT ($NUM_ENVS envs, $MAX_ITER iters)" | tee -a "$QLOG"
  if scripts/train_unified.sh "$ROBOT" "$NUM_ENVS" "$MAX_ITER"; then
    echo "[queue] $(date -u +%H:%M:%S) $ROBOT DONE" | tee -a "$QLOG"
  else
    echo "[queue] $(date -u +%H:%M:%S) $ROBOT FAILED (exit $?) — continuing" | tee -a "$QLOG"
  fi
done
echo "[queue] $(date -u +%H:%M:%S) all done" | tee -a "$QLOG"
