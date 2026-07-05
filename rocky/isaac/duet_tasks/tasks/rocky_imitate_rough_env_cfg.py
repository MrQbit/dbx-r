"""ROCKY-5 UNIFIED gait+terrain task (Isaac) — the in-Isaac replacement for the
mjlab imitation run. One policy learns BOTH the movie-accurate reference gait
(track the syncopated cycloid wave "ghost") AND rough-terrain traversal, with the
command-relative terrain-curriculum fix. Holonomic: no commanded chassis yaw.
"""

from __future__ import annotations

from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass

import duet_tasks.mdp as duet_mdp

from .rocky_rough_env_cfg import RockyRoughEnvCfg

_REF = "duet_tasks.tasks.rocky_reference"
_GAIT_JOINTS = [".*_coxa_yaw", ".*_femur_pitch", ".*_tibia_pitch"]


@configclass
class RockyImitateRoughEnvCfg(RockyRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        # --- terrain-curriculum fix (docs/ingest/terrain-curriculum-fix.md) ---
        self.episode_length_s = 30.0                                    # C
        self.curriculum.terrain_levels.func = duet_mdp.terrain_levels_track  # A
        self.commands.base_velocity.resampling_time_range = (             # B
            self.episode_length_s, self.episode_length_s)
        self.scene.terrain.max_init_terrain_level = 0                    # D
        self.rewards.action_rate_l2.weight = -0.005                      # E

        # --- holonomic: omnidirectional translation, NO commanded chassis yaw ---
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)

        # --- movie-accurate gait: track the reference "ghost" ---
        self.rewards.track_gait = RewTerm(
            func=duet_mdp.track_reference_gait,
            weight=1.0,
            params={
                "reference_module": _REF,
                "gait_period": 1.2,
                "std": 0.6,
                "asset_cfg": SceneEntityCfg("robot", joint_names=_GAIT_JOINTS),
            },
        )


@configclass
class RockyImitateRoughEnvCfg_PLAY(RockyImitateRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 32
        self.episode_length_s = 20.0                     # spec eval window
        if self.scene.terrain.terrain_generator is not None:
            self.scene.terrain.terrain_generator.num_rows = 5
            self.scene.terrain.terrain_generator.num_cols = 5
            self.scene.terrain.terrain_generator.curriculum = False
        self.observations.policy.enable_corruption = False
        self.events.base_external_force_torque = None
        self.events.push_robot = None
