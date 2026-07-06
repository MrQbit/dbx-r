#!/usr/bin/env python3
"""Export a trained rsl_rl policy (actor MLP) to ONNX for on-Jetson inference.

Run this INSIDE the Isaac Lab container on the DGX (where rsl_rl + the checkpoint
live), then copy the resulting .onnx to the Jetson. The robot brain loads it with
onnxruntime — no Isaac/torch needed on-robot.

Usage (in container):
  isaaclab.sh -p deploy/jetson/export_policy.py \
      --checkpoint logs/rsl_rl/rocky_flat/<run>/model_5999.pt --out rocky.onnx
"""
import argparse
import os

import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--obs-dim", type=int, default=250, help="policy obs vector length")
    args = ap.parse_args()

    ckpt = torch.load(args.checkpoint, map_location="cpu")
    # rsl_rl stores the ActorCritic state_dict under 'model_state_dict'
    from rsl_rl.modules import ActorCritic  # available in the Isaac container
    sd = ckpt["model_state_dict"]
    # infer action dim from the actor's last layer
    act_dim = [v for k, v in sd.items() if k.startswith("actor.") and k.endswith(".bias")][-1].shape[0]
    ac = ActorCritic(args.obs_dim, args.obs_dim, act_dim,
                     actor_hidden_dims=[512, 256, 128], critic_hidden_dims=[512, 256, 128],
                     activation="elu")
    ac.load_state_dict(sd)
    ac.eval()

    class ActorOnly(torch.nn.Module):
        def __init__(self, actor):
            super().__init__()
            self.actor = actor

        def forward(self, obs):
            return self.actor(obs)          # deterministic mean action

    wrapper = ActorOnly(ac.actor)
    dummy = torch.zeros(1, args.obs_dim)
    torch.onnx.export(wrapper, dummy, args.out, input_names=["obs"],
                      output_names=["action"], dynamic_axes={"obs": {0: "n"}, "action": {0: "n"}},
                      opset_version=17)
    print(f"exported {args.out}  (obs {args.obs_dim} -> action {act_dim})")


if __name__ == "__main__":
    main()
