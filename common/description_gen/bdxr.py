"""Load the vendored BDX-R model (D-007). BDX-A IS BDX-R, so its description is
the upstream MuJoCo/URDF assets, not a hand-built approximation.

Fetch first: `scripts/fetch_upstream.sh` (pinned SHAs into third_party/).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MJLAB = REPO_ROOT / "third_party" / "bdx_r_mjlab" / "src" / "bdx_r_mjlab" / "robots" / "bdxr" / "xmls"
ISAACLAB = REPO_ROOT / "third_party" / "bdx_r_isaaclab" / "source" / "BDXR" / "data" / "Robots" / "BDXR"

# The 14 actuated joints of the full BDX-R model, in obs/action/servo-id order.
BDXR_JOINTS = [
    "Left_Hip_Yaw", "Left_Hip_Roll", "Left_Hip_Pitch", "Left_Knee", "Left_Ankle",
    "Right_Hip_Yaw", "Right_Hip_Roll", "Right_Hip_Pitch", "Right_Knee", "Right_Ankle",
    "Neck_Pitch", "Head_Pitch", "Head_Yaw", "Head_Roll",
]


def mjcf_path(full: bool = True) -> Path:
    """Path to BDX-R's MuJoCo model: full (14 DOF) or legs-only (10 DOF)."""
    p = MJLAB / ("bdxr.xml" if full else "bdxr_legs.xml")
    if not p.exists():
        raise FileNotFoundError(f"{p} missing — run scripts/fetch_upstream.sh")
    return p


def urdf_path() -> Path:
    p = ISAACLAB / "URDF.urdf"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing — run scripts/fetch_upstream.sh")
    return p


def is_available() -> bool:
    return (MJLAB / "bdxr.xml").exists()
