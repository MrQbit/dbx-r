"""ROCKY-5 flat-terrain velocity task (D-008). Our own design — reuses Isaac
Lab's GENERIC velocity locomotion env (rewards ~ Appendix A.2), swaps in Rocky's
URDF + STS3215 actuators. Pentapod, 17 DOF (15 legs + 2 front grips).
"""

from __future__ import annotations

from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.locomotion.velocity.velocity_env_cfg import (
    LocomotionVelocityRoughEnvCfg,
)

# Rocky's generated URDF (primitives only, self-contained — no mesh deps).
ROCKY_URDF = str(Path(__file__).resolve().parents[3] / "description" / "rocky.urdf")

ROCKY_CFG = ArticulationCfg(
    spawn=sim_utils.UrdfFileCfg(
        asset_path=ROCKY_URDF,
        fix_base=False,
        # Keep fixed-joint bodies: the sphere feet + palms attach via fixed joints,
        # and we need them as separate bodies for foot contact sensing.
        merge_fixed_joints=False,
        replace_cylinders_with_capsules=False,
        activate_contact_sensors=True,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False, max_depenetration_velocity=1.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=4,
            solver_velocity_iteration_count=0,
        ),
        joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
            gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=0.0, damping=0.0)
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.12),                     # lower spawn: tightened size (D-014)
        joint_pos={
            ".*_coxa_yaw": 0.0,
            ".*_femur_pitch": 0.6,
            ".*_tibia_pitch": 1.0,
            ".*_grip": 0.0,
        },
    ),
    # EduLite 05 implicit PD (D-013) on all 17 joints — effort clamp 6 Nm (was 17).
    actuators={
        "all": ImplicitActuatorCfg(
            joint_names_expr=[".*"],
            stiffness=40.0, damping=2.0,          # Robstride EduLite 05
            effort_limit_sim=6.0, velocity_limit_sim=15.0, armature=0.02,
        ),
    },
    soft_joint_pos_limit_factor=0.95,
)


@configclass
class RockyFlatEnvCfg(LocomotionVelocityRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        # --- robot ---
        self.scene.robot = ROCKY_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # --- flat terrain (drop the rough-terrain height scanner + curriculum) ---
        self.scene.terrain.terrain_type = "plane"
        self.scene.terrain.terrain_generator = None
        self.scene.height_scanner = None
        self.observations.policy.height_scan = None
        self.curriculum.terrain_levels = None

        # --- Rocky body names: feet are sphere feet + palms; base is base_link ---
        feet = "leg[0-4]_(foot|palm)"
        self.rewards.feet_air_time.params["sensor_cfg"].body_names = feet
        self.rewards.feet_air_time.params["threshold"] = 0.35
        self.rewards.undesired_contacts.params["sensor_cfg"].body_names = "base_link|leg[0-4]_(coxa|femur)"
        # ROCKY glides flat on its carapace (Appendix A.2 doubled flat penalty).
        self.rewards.flat_orientation_l2.weight = -5.0
        self.rewards.dof_pos_limits.weight = -1.0

        # --- omnidirectional commands (Appendix A.2): vx,vy on 0.35 disk, wz +/-1 ---
        self.commands.base_velocity.ranges.lin_vel_x = (-0.35, 0.35)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.35, 0.35)
        self.commands.base_velocity.ranges.ang_vel_z = (-1.0, 1.0)

        # --- terminate on carapace/base contact ---
        self.terminations.base_contact.params["sensor_cfg"].body_names = "base_link"

        # --- events: Rocky's base body is 'base_link' (not 'base'). The base env's
        # class-based mass-randomization term is incompatible in Isaac Lab 2.3.2 —
        # disable it (mass DR is a later refinement); repoint the rest to base_link.
        self.events.add_base_mass = None
        for name in ("base_external_force_torque", "base_com"):
            ev = getattr(self.events, name, None)
            if ev is not None and "asset_cfg" in getattr(ev, "params", {}):
                ev.params["asset_cfg"].body_names = "base_link"


@configclass
class RockyFlatEnvCfg_PLAY(RockyFlatEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 32
        self.observations.policy.enable_corruption = False
        self.events.base_external_force_torque = None
        self.events.push_robot = None
