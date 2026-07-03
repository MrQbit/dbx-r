#!/usr/bin/env bash
# CAD environment — aarch64 OCP contingency-2 (ROBOTS_SPEC.md §1), idempotent.
#
# Path taken (recorded in D-003):
#   * cadquery-ocp has NO linux-aarch64 pip wheel -> contingency 1 fails.
#   * conda-forge provides ocp 7.7.2 for aarch64 -> use it (contingency 2).
#   * build123d 0.9.x needs OCP 7.8 (unavailable on aarch64); pin build123d
#     0.8.0, which targets OCP 7.7.2. Install --no-deps so pip does not try to
#     pull the missing cadquery-ocp wheel; add the pure-python deps by hand.
#   * py-lib3mf 2.5.0 ships its native module as `lib3mf`, but build123d 0.8.0
#     imports `py_lib3mf` -> install a one-line re-export shim.
#
# Result: full build123d B-rep CAD on aarch64. `make gate-2` CAD stages and
# tests run in this env via scripts/cadpy.
set -euo pipefail

MM="$HOME/.local/bin/micromamba"
MR="$HOME/micromamba"
ENV=duet-cad

# 1. micromamba (userspace static binary; no sudo)
if [[ ! -x "$MM" ]]; then
  mkdir -p "$(dirname "$MM")"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-aarch64/latest \
    | tar -xj -C "$(dirname "$MM")" --strip-components=1 bin/micromamba
fi

# 2. conda-forge OCP env (idempotent create)
if ! "$MM" env list | grep -q "$ENV"; then
  "$MM" create -y -r "$MR" -n "$ENV" -c conda-forge python=3.11 ocp=7.7.2 lib3mf numpy
fi
run(){ "$MM" run -r "$MR" -n "$ENV" "$@"; }

# 3. build123d 0.8.0 (OCP-7.7.2 compatible) + pure-python deps + host test deps
run python -c "import build123d" 2>/dev/null || {
  run pip install --no-deps build123d==0.8.0 ocpsvg
  run pip install numpy scipy svgpathtools svgelements anytree ezdxf ipython \
      trianglesolver py-lib3mf trimesh numpy-stl manifold3d rtree pyyaml pytest
}

# 4. py_lib3mf shim (build123d 0.8.0 imports py_lib3mf; wheel ships it as lib3mf)
SP="$($MM run -r "$MR" -n "$ENV" python -c 'import site; print(site.getsitepackages()[0])')"
if [[ ! -f "$SP/py_lib3mf.py" ]]; then
  printf 'from lib3mf import *  # aarch64 shim (D-003)\nfrom lib3mf import Lib3MF\n' \
    > "$SP/py_lib3mf.py"
fi

# 5. verify
run python -c "from build123d import Box; import py_lib3mf; print('CAD env OK: build123d', __import__('build123d').__version__)"
