# Ingest — rough-terrain curriculum fix (both robots)

## Root cause (why terrain_level stuck at ~0.06–0.12)
Isaac Lab's `terrain_levels_vel` PROMOTES a robot only if it walks **> 4.0 m net**
(half the 8 m terrain patch) in an episode, and DEMOTES if it covers **< command·
episode·0.5** (~2.7 m). Rocky is spec-capped at 0.35 m/s omnidirectional (§6.3),
and the command **resamples to a new random direction at t=10 s** in a 20 s episode
— so net displacement is ~1–2 m. move_up never fires; move_down fires most
episodes → curriculum drifts DOWN from the initial mean level 2.5 to ~1, trapping
the robot on easy terrain → timid gait, poor tracking. Known Isaac Lab failure
mode for low-command robots (issue #969, discussion #2620).

## Fix (spec-compliant; commands stay on the 0.35 m/s disk — the levers are the
## curriculum/episode, on which the spec is silent — log D-###)
- **A. Command-relative curriculum** (`duet_tasks/mdp/curriculums.py::terrain_levels_track`):
  promote if distance > 0.6·(‖cmd‖·episode_len) AND > 1 m; demote if < 0.25·that.
  Gated on TRACKING quality, works at any command speed. Wire via
  `self.curriculum.terrain_levels.func = terrain_levels_track`.
- **B. Constant command per episode:** `resampling_time_range = (episode_len, episode_len)`
  (stops mid-episode direction flip; makes cmd_dist exact). Land A+B together.
- **C. 30 s training episode** (`episode_length_s = 30.0`); keep 20 s in _PLAY (eval).
- **D. Start at the bottom:** `terrain.max_init_terrain_level = 0`.
- **E. Restore spec Rocky character rewards (A.2):** wave-gait phase w=0.6 (biggest
  anti-timidity lever), height-hold 130±10 mm w=0.4, and action_rate to **−0.005**
  (inherited base is −0.01, double the spec → over-penalizes motion).

## Applies identically to BDX-A (same base env, same terrain_levels_vel). Put
`terrain_levels_track` in a shared duet_tasks/mdp/curriculums.py; apply A–D to both
rough configs. Expected: terrain_level climbs steadily; vel_err drops as the robot
is rewarded for moving and practices real terrain.

Sources: Isaac Lab issue #969, discussion #2620, issues #1685/#1492; legged_gym
`_update_terrain_curriculum`; Isaac Lab G1 rough_env_cfg (working recipe).
