"""Load and lightly validate a robot's design params (ROBOTS_SPEC.md §5).

`params.yaml` is the parametric root for everything downstream. This loader is
imported by tests, report generators, and the description pipeline so the file
is parsed in exactly one place.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ROBOTS = ("bdx_a", "rocky")


def params_path(robot: str) -> Path:
    if robot not in ROBOTS:
        raise ValueError(f"unknown robot {robot!r}; expected one of {ROBOTS}")
    return REPO_ROOT / robot / "design" / "params.yaml"


def load_params(robot: str) -> dict:
    with params_path(robot).open() as fh:
        return yaml.safe_load(fh)


def bdx_a_dof(params: dict) -> list[dict]:
    return params["dof"]


def rocky_dof(params: dict) -> list[dict]:
    """Expand ROCKY-5's per-limb template into 15 explicit joints (§4)."""
    out = []
    for i in range(params["limb_count"]):
        for j in params["dof_template"]:
            out.append(
                {
                    "name": f"leg{i}_{j['suffix']}",
                    "servo_id": 3 * i + j["offset"],
                    "limit_rad": j["limit_rad"],
                }
            )
    return out
