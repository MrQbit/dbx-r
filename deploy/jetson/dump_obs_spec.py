#!/usr/bin/env python3
"""Dump the policy observation term order + dims to <robot>_obs_spec.json.

Run in the Isaac Lab container (same env the policy trained in). brain.py loads the
JSON and assembles the on-robot obs vector in the EXACT order/size the policy expects
— the single most common cause of "the robot runs but walks wrong" if left to guess.

  isaaclab.sh -p deploy/jetson/dump_obs_spec.py --task Duet-Rocky-Imitate-Rough-v0 \
      --out rocky_obs_spec.json
"""
import argparse
import json

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--task", required=True)
parser.add_argument("--out", required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
args.headless = True
app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym  # noqa: E402
import duet_tasks.tasks  # noqa: F401,E402  (registers the Duet tasks)
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

cfg = parse_env_cfg(args.task, num_envs=1)
env = gym.make(args.task, cfg=cfg)
om = env.unwrapped.observation_manager

names = om.active_terms["policy"]
dims = om.group_obs_term_dim["policy"]           # list of shape tuples
terms = [{"name": n, "dim": int(d[0] if isinstance(d, (tuple, list)) else d)}
         for n, d in zip(names, dims)]
spec = {"task": args.task, "terms": terms, "total": sum(t["dim"] for t in terms)}

with open(args.out, "w") as f:
    json.dump(spec, f, indent=2)
print(f"wrote {args.out}: total={spec['total']}")
for t in terms:
    print(f"  {t['name']:<24} {t['dim']}")

env.close()
simulation_app.close()
