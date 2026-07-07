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
    """Expand ROCKY-5 into explicit joints: 20 leg joints (§4, 4 per limb after the
    D-039 tibia_roll) + per-leg grip manipulators (D-008). Order == obs == action ==
    servo-id order. Servo IDs stride by the number of per-limb joints so IDs stay
    contiguous per limb (leg i => n*i+offset) as the template grows."""
    n = len(params["dof_template"])            # per-limb joint count (4 with tibia_roll)
    out = []
    for i in range(params["limb_count"]):
        for j in params["dof_template"]:
            out.append(
                {
                    "name": f"leg{i}_{j['suffix']}",
                    "servo_id": n * i + j["offset"],
                    "limit_rad": j["limit_rad"],
                }
            )
    man = params.get("manipulators")
    if man:
        for leg, sid in zip(man["legs"], man["servo_ids"]):
            out.append({"name": f"leg{leg}_grip", "servo_id": sid,
                        "limit_rad": man["grip_limit_rad"]})
    return out
