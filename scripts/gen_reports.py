#!/usr/bin/env python3
"""Generate the deterministic design reports that gates assert on.

Currently: torque reports (§3.3, §4) -> docs/reports/torque_<robot>.md.
Idempotent: re-running overwrites with identical content. Exits non-zero if any
torque check FAILS, so `make gate-1` fails loudly rather than silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain script (python scripts/gen_reports.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.params import load_params  # noqa: E402
from common.cad_lib.torque import check_rocky, render_report  # noqa: E402

REPORTS = Path(__file__).resolve().parent.parent / "docs" / "reports"


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ok = True
    # BDX-A adopts BDX-R's Robstride actuators (D-007) — torque validated upstream.
    for robot, checker in (("rocky", check_rocky),):
        params = load_params(robot)
        result = checker(params)
        out = REPORTS / f"torque_{robot}.md"
        out.write_text(render_report(result, params))
        status = "PASS" if result.passed else "FAIL"
        print(f"[gen_reports] {out.relative_to(REPORTS.parent.parent)}: {status}")
        ok = ok and result.passed
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
