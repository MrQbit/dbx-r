#!/usr/bin/env bash
# Fetch the BDX-R upstream reference repos we build BDX-A on (ROBOTS_SPEC.md §0.6
# ingest). Pinned to exact SHAs, cloned READ-ONLY into third_party/ (gitignored).
# We IMPROVE on these by subclassing/extending in our own tree — never editing
# the vendored copies. Licenses recorded in docs/LICENSES.md (§0.7).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p third_party

fetch() {  # url sha dest
  local url="$1" sha="$2" dest="third_party/$3"
  if [[ -d "$dest/.git" ]]; then
    git -C "$dest" fetch --quiet origin "$sha" || true
  else
    git clone --quiet "$url" "$dest"
  fi
  git -C "$dest" checkout --quiet "$sha"
  echo "[fetch] $3 @ $sha"
}

# BDX-R Isaac Lab (MIT, Kayden Knapik) — URDF/USD/meshes + Isaac Lab training.
fetch https://github.com/BDX-R/BDX-R-IsaacLab.git \
  62f0ba642fa0225180dc484f3ff195b7052b2a34 bdx_r_isaaclab

# BDX-R MjLab (Apache-2.0) — MuJoCo models + velocity/imitation tasks (host-native).
fetch https://github.com/BDX-R/BDX-R-MjLab.git \
  079acd294650aa149644828723da517eabd808c9 bdx_r_mjlab

echo "[fetch] upstream ready in third_party/"
