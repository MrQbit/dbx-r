"""Command-relative terrain curriculum — the fix for the stuck-curriculum bug
(docs/ingest/terrain-curriculum-fix.md). Isaac Lab's stock terrain_levels_vel
promotes only if the robot walks > half the 8 m patch (~4 m); a robot capped at
0.35 m/s never gets there and is demoted forever. Here we promote on FRACTION OF
COMMANDED distance covered, so progress is gated on tracking quality and works at
any command speed. Applies identically to both robots."""

from __future__ import annotations

import torch
from collections.abc import Sequence

from isaaclab.assets import Articulation
from isaaclab.managers import SceneEntityCfg
from isaaclab.terrains import TerrainImporter


def terrain_levels_track(
    env,
    env_ids: Sequence[int],
    asset_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
) -> torch.Tensor:
    asset: Articulation = env.scene[asset_cfg.name]
    terrain: TerrainImporter = env.scene.terrain
    command = env.command_manager.get_command("base_velocity")

    # net displacement from the spawn cell this episode
    distance = torch.norm(
        asset.data.root_pos_w[env_ids, :2] - env.scene.env_origins[env_ids, :2], dim=1
    )
    # distance the command *asked* this robot to travel over a full episode
    cmd_dist = torch.norm(command[env_ids, :2], dim=1) * env.max_episode_length_s

    # promote if it covered >=60% of commanded distance AND actually moved
    move_up = (distance > 0.6 * cmd_dist) & (distance > 1.0)
    # demote if it covered <25% of commanded distance (timid / fell)
    move_down = (distance < 0.25 * cmd_dist) & ~move_up

    terrain.update_env_origins(env_ids, move_up, move_down)
    return torch.mean(terrain.terrain_levels.float())
