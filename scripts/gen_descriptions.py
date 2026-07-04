#!/usr/bin/env python3
"""Description generator — the `_desc` stage / gate-3 producer (§5).

params.yaml -> RobotModel -> URDF + MJCF, written to <robot>/description/.
USD conversion (Isaac Lab headless `convert_urdf.py`) runs in the isaac stage
inside the container; it consumes the URDF written here.

Usage: python scripts/gen_descriptions.py [robot ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.description_gen.builders import build  # noqa: E402
from common.description_gen.urdf import to_urdf  # noqa: E402
from common.description_gen.mjcf import to_mjcf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def generate(robot: str) -> None:
    m = build(robot)
    out = ROOT / robot / "description"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{robot}.urdf").write_text(to_urdf(m))
    (out / f"{robot}.mjcf.xml").write_text(to_mjcf(m))
    print(f"[gen_desc] {robot}: {len(m.links)} links, {len(m.actuated_joints)} DOF, "
          f"mass={m.total_mass():.2f} kg -> {robot}.urdf + {robot}.mjcf.xml")


def main() -> int:
    # BDX-A is the vendored BDX-R model (D-007) — not generated here. Only ROCKY-5.
    for robot in sys.argv[1:] or ["rocky"]:
        generate(robot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
