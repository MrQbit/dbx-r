#!/usr/bin/env bash
# G0 environment setup (ROBOTS_SPEC.md §1) — idempotent, non-interactive.
# The ONLY place `sudo` is permitted (CLAUDE.md Working rules). Safe to re-run.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
cd "$(dirname "$0")/.."

echo "[setup] host uv venv (Python 3.11)"
if [[ ! -x .venv/bin/python ]]; then
  uv venv --python 3.11 .venv
fi
uv pip install --python .venv pyyaml numpy trimesh numpy-stl manifold3d pytest

echo "[setup] CAD environment (aarch64 OCP contingency, §1 / D-003)"
# build123d/OCP has no aarch64 pip wheel; setup_cad_env.sh builds the micromamba
# conda-forge OCP env used by scripts/cadpy. Idempotent.
bash scripts/setup_cad_env.sh

echo "[setup] Isaac Lab 2.3.x ARM image (pin newest 2.3.x tag + record digest)"
# Primary path: pull the official multi-arch Isaac Lab image (ARM variant).
# Fallback (source build via dgx-spark-playbook) is documented in §1; on pull
# failure this script logs D-### and exits non-zero so gate-0 halts the common
# track rather than proceeding on a broken toolchain.
if [[ -n "${DUET_ISAAC_IMAGE:-}" ]]; then
  if docker pull "$DUET_ISAAC_IMAGE"; then
    docker image inspect "$DUET_ISAAC_IMAGE" --format '{{index .RepoDigests 0}}' \
      > orchestrator/.isaac_image_digest
    echo "[setup] pinned $(cat orchestrator/.isaac_image_digest)"
  else
    echo "[setup] ERROR: Isaac image pull failed — see §1 fallback; log D-###" >&2
    exit 1
  fi
else
  echo "[setup] DUET_ISAAC_IMAGE unset — skipping container pin (host-only setup)"
fi

echo "[setup] enable Isaac Lab asset caching (tolerate later network loss, §G0)"
mkdir -p "${HOME}/.cache/ov" "${HOME}/.cache/isaac"

touch orchestrator/.env_ready
echo "[setup] done"
