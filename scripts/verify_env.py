#!/usr/bin/env python3
"""G0 environment gate (ROBOTS_SPEC.md §1, §10).

Asserts the DGX Spark host prerequisites, then (when the Isaac Lab image is
recorded) launches a headless Isaac Sim smoke. Host checks run offline; the
Isaac smoke is skipped with a clear PENDING when the container isn't set up yet
so the rest of the pipeline can be scaffolded and tested on the host first.

Exit 0 iff every non-skipped MUST check passes.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_DRIVER = (580, 95, 5)
MIN_CUDA_MAJOR = 13
MIN_FREE_GB = 150          # pre-flight (WEEKEND_RUNBOOK.md)
# Host venv deps (aarch64 wheels). build123d is NOT here by design — it lives in
# the micromamba CAD env (D-003) and is checked separately via scripts/cadpy.
HOST_IMPORTS = ["yaml", "numpy", "trimesh", "mujoco", "yourdfpy"]


def _ver_tuple(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in s.strip().split(".") if x.isdigit())


class Checks:
    def __init__(self):
        self.failed = 0
        self.skipped = 0

    def ok(self, name, detail=""):
        print(f"  [PASS] {name} {detail}".rstrip())

    def fail(self, name, detail=""):
        print(f"  [FAIL] {name} {detail}".rstrip())
        self.failed += 1

    def skip(self, name, detail=""):
        print(f"  [SKIP] {name} {detail}".rstrip())
        self.skipped += 1


def check_arch(c: Checks):
    m = platform.machine()
    (c.ok if m == "aarch64" else c.fail)("arch aarch64", f"(got {m})")


def check_gpu(c: Checks):
    exe = shutil.which("nvidia-smi")
    if not exe:
        c.fail("nvidia-smi present", "(not found)")
        return
    out = subprocess.run(
        [exe, "--query-gpu=driver_version", "--format=csv,noheader"],
        capture_output=True, text=True,
    ).stdout
    drv = _ver_tuple(out.splitlines()[0]) if out.strip() else ()
    (c.ok if drv >= MIN_DRIVER else c.fail)(
        "driver >= 580.95.05", f"(got {'.'.join(map(str, drv)) or '?'})"
    )
    # CUDA version reported by the driver.
    smi = subprocess.run([exe], capture_output=True, text=True).stdout
    cuda_major = 0
    for line in smi.splitlines():
        if "CUDA Version" in line:
            try:
                cuda_major = int(float(line.split("CUDA Version:")[1].split()[0]))
            except (IndexError, ValueError):
                pass
    (c.ok if cuda_major >= MIN_CUDA_MAJOR else c.fail)(
        "CUDA >= 13", f"(got {cuda_major or '?'})"
    )


def check_disk(c: Checks):
    free = shutil.disk_usage(ROOT).free / 1e9
    (c.ok if free >= MIN_FREE_GB else c.fail)(
        f"free disk >= {MIN_FREE_GB} GB", f"(got {free:.0f} GB)"
    )


def check_host_imports(c: Checks):
    for mod in HOST_IMPORTS:
        try:
            __import__(mod)
            c.ok(f"import {mod}")
        except Exception as e:  # noqa: BLE001
            # CAD stack may not be installed for a host-only G1 run; warn softly.
            c.skip(f"import {mod}", f"({type(e).__name__}) — run scripts/setup_env.sh")


def check_cad_env(c: Checks):
    """build123d lives in the micromamba CAD env (D-003); check it via cadpy."""
    cadpy = ROOT / "scripts" / "cadpy"
    try:
        r = subprocess.run([str(cadpy), "-c", "import build123d, OCP"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            c.ok("CAD env (build123d + OCP via cadpy)")
        else:
            c.skip("CAD env (build123d)", "run scripts/setup_cad_env.sh")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        c.skip("CAD env (build123d)", f"({type(e).__name__}) run scripts/setup_cad_env.sh")


def check_isaac_smoke(c: Checks):
    digest_file = ROOT / "orchestrator" / ".isaac_image_digest"
    # Prefer the frozen digest (§1: image is pinned at G0 for the whole weekend).
    image = None
    if digest_file.exists():
        image = digest_file.read_text().strip()
    image = image or os.environ.get("DUET_ISAAC_IMAGE")
    if not image:
        c.skip("Isaac Sim headless smoke", "(image not pinned yet — G0 container step pending)")
        return
    # Headless create+destroy stage, <5 min (§1). Success == clean exit 0:
    # Isaac/Kit logs to its own files, not stdout, so a printed marker is
    # unreliable — a failed SimulationApp init raises and exits non-zero instead.
    smoke = (
        "from isaacsim import SimulationApp\n"
        "app = SimulationApp({'headless': True})\n"
        "import omni.usd\n"
        "omni.usd.get_context().new_stage()\n"
        "app.update(); app.close()\n"
    )
    cmd = [
        "docker", "run", "--rm", "--gpus", "all",
        "-e", "OMNI_KIT_ACCEPT_EULA=YES", "-e", "OMNI_KIT_ALLOW_ROOT=1",
        "-e", "LD_PRELOAD=/lib/aarch64-linux-gnu/libgomp.so.1",
        image, "python", "-c", smoke,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        (c.ok if r.returncode == 0 else c.fail)(
            "Isaac Sim headless smoke", "" if r.returncode == 0 else f"(exit {r.returncode})")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        c.fail("Isaac Sim headless smoke", f"({type(e).__name__})")


def main() -> int:
    print("G0 environment verification (ROBOTS_SPEC.md §1)")
    c = Checks()
    check_arch(c)
    check_gpu(c)
    check_disk(c)
    check_host_imports(c)
    check_cad_env(c)
    check_isaac_smoke(c)
    print(f"\nG0: {c.failed} failed, {c.skipped} skipped")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
