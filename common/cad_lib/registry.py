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
    # BDX-A is adopted from BDX-R (D-007) — its printable parts are BDX-R's meshes,
    # not ours. We only keep the generic fit-coupon here (+ our charging/integration
    # add-ons as they're authored). ROCKY-5 is our own full part set.
    "bdx_a": [
        "common.cad_lib.coupons",
        "bdx_a.cad.parts.belly_rx_mount",       # Qi RX add-on (wireless charging)
    ],
    "rocky": [
        "rocky.cad.parts.core_plate",
        # Interchangeable 3-pronged limbs (movie): a symmetric 3-prong foot on
        # every leg (qty 5) and the one culturally-marked primary limb segment
        # (base-3 ruler + Eridian marriage symbol, engraved shallow so QA passes).
        "rocky.cad.parts.foot",
        "rocky.cad.parts.limb_marked",
        # Single-piece rock dome — fits the 250mm P2S envelope (211mm). The 2-piece
        # split (carapace_cap/skirt) is now validated (seam-flush displacement +
        # a dovetail registration lip; both QA-clean and assemble with zero
        # interference) but stays UNREGISTERED — redundant while the single piece
        # fits. Swap the two in if a future scale pushes the dome past the envelope.
        "rocky.cad.parts.carapace",             # movie-accurate rock dome (§4)
        "rocky.cad.parts.belly_rx_plate",       # Qi RX mount (wireless charging)
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
