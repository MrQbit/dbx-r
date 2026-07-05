"""Reference-gait imitation reward (Isaac Lab) — the unified in-Isaac path for
movie-accurate MOTION (replaces the mjlab imitation run; weights don't cross sims).

The policy is rewarded for matching a hand-authored reference joint trajectory at
the current gait phase (the "ghost"). Robot-agnostic: it samples a reference
module (rocky_reference / bdx_reference) into a phase lookup table on first call,
keyed to the env's actual joint order, then tracks it on GPU."""

from __future__ import annotations

import importlib

import torch

from isaaclab.assets import Articulation
from isaaclab.managers import SceneEntityCfg

_TABLE_CACHE: dict = {}


def _reference_table(env, asset, joint_ids, reference_module: str, n: int = 64):
    key = (id(env), reference_module, tuple(joint_ids))
    tbl = _TABLE_CACHE.get(key)
    if tbl is None:
        mod = importlib.import_module(reference_module)
        names = [asset.joint_names[i] for i in joint_ids]
        rows = []
        for k in range(n):
            ref = mod.reference(k / n)
            rows.append([float(ref.get(nm, 0.0)) for nm in names])
        tbl = torch.tensor(rows, device=env.device, dtype=torch.float32)
        _TABLE_CACHE[key] = tbl
    return tbl


def track_reference_gait(
    env,
    reference_module: str,
    gait_period: float = 1.2,
    std: float = 0.5,
    asset_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
) -> torch.Tensor:
    """exp(-||q - q_ref(phase)||^2 / std^2) over the tracked joints. phase advances
    with episode time; gait_period is the cycle length (s)."""
    asset: Articulation = env.scene[asset_cfg.name]
    joint_ids = asset_cfg.joint_ids
    if joint_ids is None or (isinstance(joint_ids, slice)):
        joint_ids = list(range(asset.num_joints))
    table = _reference_table(env, asset, list(joint_ids), reference_module)
    n = table.shape[0]

    phase = (env.episode_length_buf.float() * env.step_dt / gait_period) % 1.0
    idx = (phase * n).long().clamp(0, n - 1)
    ref = table[idx]                                          # [num_envs, njoints]

    q = asset.data.joint_pos[:, joint_ids]
    err = torch.mean((q - ref) ** 2, dim=1)      # mean over joints: informative gradient
    return torch.exp(-err / (std ** 2))
