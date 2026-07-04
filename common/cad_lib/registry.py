"""Part registry — the authoritative list of printable parts per robot (§4.5).

Each entry is an importable module exposing `part()` and `META`. The coupons
plate is shared (printed once, plate #1). Keeping this explicit (vs directory
scanning) makes `make gate-2` deterministic and its order reproducible.
"""

from __future__ import annotations

import importlib
from types import ModuleType

# robot -> list of module import paths
_PARTS: dict[str, list[str]] = {
    "bdx_a": [
        "common.cad_lib.coupons",
        "bdx_a.cad.parts.knee_link",
    ],
    "rocky": [
        "rocky.cad.parts.core_plate",
        # Shared wireless-charging dock (both robots dock on it); QA'd here.
        "common.cad_lib.charging_base",
    ],
}


def parts_for(robot: str) -> list[ModuleType]:
    if robot not in _PARTS:
        raise ValueError(f"unknown robot {robot!r}")
    return [importlib.import_module(m) for m in _PARTS[robot]]


def all_robots() -> list[str]:
    return list(_PARTS)
