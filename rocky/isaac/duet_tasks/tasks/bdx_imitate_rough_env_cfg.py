"""BDX-A UNIFIED gait+terrain task (Isaac) — the in-Isaac path for BDX (chosen over
carrying mjlab weights, which don't cross sims). One policy learns the bipedal gait
(track bdx_reference) AND rough-terrain traversal, with the command-relative
terrain-curriculum fix. BDX is a biped: it yaws to turn (no holonomic constraint).

Reuses BDX-R's articulation (BDX_R_CFG) on Isaac Lab's generic rough velocity env.
"""

from __future__ import annotations

from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass
from isaaclab_tasks.manager_based.locomotion.velocity.velocity_env_cfg import (
    LocomotionVelocityRoughEnvCfg,
)

import duet_tasks.mdp as duet_mdp

_REF = "duet_tasks.tasks.bdx_reference"
_GAIT_JOINTS = [".*_Hip_Yaw", ".*_Hip_Roll", ".*_Hip_Pitch", ".*_Knee", ".*_Ankle"]


@configclass
class BdxImitateRoughEnvCfg(LocomotionVelocityRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        # lazy import: only needs the BDXR package when a BDX env is instantiated
        from BDXR.robots.bdxr import BDX_R_CFG

        # --- robot ---
        self.scene.robot = BDX_R_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.scene.height_scanner.prim_path = "{ENV_REGEX_NS}/Robot/base_link"

        # --- BDX body names for terrain-aware rewards/terminations ---
        self.rewards.feet_air_time.params["sensor_cfg"].body_names = ".*_Foot"
        self.rewards.feet_air_time.params["threshold"] = 0.4
        self.rewards.undesired_contacts = None            # skip (BDX link names differ)
        self.rewards.flat_orientation_l2.weight = -1.0    # relaxed for climbing
        self.rewards.dof_pos_limits.weight = -1.0
        self.terminations.base_contact.params["sensor_cfg"].body_names = "base_link"

        # --- events: base is base_link; class-based mass event 2.3.2-incompatible ---
        self.events.add_base_mass = None
        for name in ("base_external_force_torque", "base_com"):
            ev = getattr(self.events, name, None)
            if ev is not None and "asset_cfg" in getattr(ev, "params", {}):
                ev.params["asset_cfg"].body_names = "base_link"

        # --- terrain-curriculum fix (docs/ingest/terrain-curriculum-fix.md) ---
        self.episode_length_s = 30.0                                    # C
        self.curriculum.terrain_levels.func = duet_mdp.terrain_levels_track  # A
        self.commands.base_velocity.resampling_time_range = (             # B
            self.episode_length_s, self.episode_length_s)
        self.scene.terrain.max_init_terrain_level = 0                    # D
        self.rewards.action_rate_l2.weight = -0.005                      # E

        # BDX commands (A.1): a biped that turns normally (keep ang_vel_z)
        self.commands.base_velocity.ranges.lin_vel_x = (-0.5, 0.8)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.3, 0.3)
        self.commands.base_velocity.ranges.ang_vel_z = (-1.0, 1.0)

        # --- gait character: track the bipedal reference (modest weight) ---
        self.rewards.track_gait = RewTerm(
            func=duet_mdp.track_reference_gait,
            weight=0.5,
            params={
                "reference_module": _REF,
                "gait_period": 0.8,
                "std": 0.6,
                "asset_cfg": SceneEntityCfg("robot", joint_names=_GAIT_JOINTS),
            },
        )


@configclass
class BdxImitateRoughEnvCfg_PLAY(BdxImitateRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 32
        self.episode_length_s = 20.0
        if self.scene.terrain.terrain_generator is not None:
            self.scene.terrain.terrain_generator.num_rows = 5
            self.scene.terrain.terrain_generator.num_cols = 5
            self.scene.terrain.terrain_generator.curriculum = False
        self.observations.policy.enable_corruption = False
        self.events.base_external_force_torque = None
        self.events.push_robot = None
