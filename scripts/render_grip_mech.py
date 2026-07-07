#!/usr/bin/env python3
"""Preview the ROCKY-5 grip HAND mechanism — matplotlib Agg, no pyglet/GL.

D-038: the hand is now the SLIM 2+1 manipulator (two primary walking-tip fingers +
one opposing thumb, hidden micro-servo drive). The renderer lives in
`scripts/render_hand_2plus1.py`; this script keeps the old entrypoint + output path
(`docs/media/rocky_grip_mech.png`) and delegates to it.

Usage: .venv/bin/python scripts/render_grip_mech.py [out.png]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import render_hand_2plus1  # noqa: E402


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "docs" / "media" / "rocky_grip_mech.png")
    sys.argv = [sys.argv[0], out]
    return render_hand_2plus1.main()


if __name__ == "__main__":
    raise SystemExit(main())
