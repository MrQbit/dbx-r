"""ROCKY-5 ROUGH-terrain velocity task — advanced terrain (stairs, drops, uneven,
slopes) with the height-scanner perception + difficulty curriculum.

Unlike the flat task, this keeps Isaac Lab's ROUGH_TERRAINS_CFG (pyramid stairs
up/down, random-grid boxes = edges/drops, random_rough = uneven, slopes) and the
ray-caster height scanner so the pentapod learns to SEE and negotiate terrain.
Rocky's low CoM + 5 legs should handle stairs/uneven well.
"""

from __future__ import annotations

from isaaclab.utils import configclass
from isaaclab_tasks.manager_based.locomotion.velocity.velocity_env_cfg import (
    LocomotionVelocityRoughEnvCfg,
)

from .rocky_flat_env_cfg import ROCKY_CFG


@configclass
class RockyRoughEnvCfg(LocomotionVelocityRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        # robot
        self.scene.robot = ROCKY_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        # height scanner rides on base_link (Rocky's base body, not 'base')
        self.scene.height_scanner.prim_path = "{ENV_REGEX_NS}/Robot/base_link"

        # Soften the default random-rough (near bed-of-nails) + stair heights so the
        # difficulty curriculum can actually progress (the 3k run stuck at level 0.06).
        tg = self.scene.terrain.terrain_generator
        if tg is not None:
            st = tg.sub_terrains
            if "random_rough" in st:
                st["random_rough"].noise_range = (0.01, 0.04)
                st["random_rough"].noise_step = 0.01
            for key in ("pyramid_stairs", "pyramid_stairs_inv"):
                if key in st:
                    st[key].step_height_range = (0.02, 0.12)

        # Rocky body names for the terrain-aware rewards
        self.rewards.feet_air_time.params["sensor_cfg"].body_names = "leg[0-4]_(foot|palm)"
        self.rewards.feet_air_time.params["threshold"] = 0.35
        self.rewards.undesired_contacts.params["sensor_cfg"].body_names = "base_link|leg[0-4]_(coxa|femur)"
        # On rough terrain the body tilts to climb — relax the flat-orientation penalty
        self.rewards.flat_orientation_l2.weight = -1.0
        self.rewards.dof_pos_limits.weight = -1.0

        # omnidirectional commands (Appendix A.2)
        self.commands.base_velocity.ranges.lin_vel_x = (-0.35, 0.35)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.35, 0.35)
        self.commands.base_velocity.ranges.ang_vel_z = (-1.0, 1.0)

        # terminate on carapace/base ground contact
        self.terminations.base_contact.params["sensor_cfg"].body_names = "base_link"

        # events: base body is base_link; the class-based mass event is 2.3.2-incompatible
        self.events.add_base_mass = None
        for name in ("base_external_force_torque", "base_com"):
            ev = getattr(self.events, name, None)
            if ev is not None and "asset_cfg" in getattr(ev, "params", {}):
                ev.params["asset_cfg"].body_names = "base_link"


@configclass
class RockyRoughEnvCfg_PLAY(RockyRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 32
        # smaller, non-curriculum terrain for viewing
        if self.scene.terrain.terrain_generator is not None:
            self.scene.terrain.terrain_generator.num_rows = 5
            self.scene.terrain.terrain_generator.num_cols = 5
            self.scene.terrain.terrain_generator.curriculum = False
        self.observations.policy.enable_corruption = False
        self.events.base_external_force_torque = None
        self.events.push_robot = None
