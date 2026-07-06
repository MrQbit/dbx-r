#!/usr/bin/env python3
"""Assemble the ROCKY-5 CAD parts into a stance and render it from 3 angles, so we
can judge the printed robot's LOOK (vs the movie Eridian). Uses the real part STLs
placed per params geometry (not the simplified training URDF primitives).

Run in the CAD venv:  scripts/cadpy scripts/render_rocky_assembly.py
"""
import glob
import math
import os

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import yaml

P = yaml.safe_load(open("rocky/design/params.yaml"))["dimensions"]
R_BODY = P["carapace_dia_mm"] / 2.0
DOME_H = P["dome_height_mm"]
R_FOOT = P["footprint_dia_mm"] / 2.0
STANCE = P["stance_height_mm"]
N = 5
STONE = "#8a8078"


def load(name):
    fs = glob.glob(f"**/{name}.stl", recursive=True)
    return trimesh.load(fs[0]) if fs else None


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def place(mesh, R=np.eye(3), t=(0, 0, 0)):
    m = mesh.copy()
    m.vertices = m.vertices @ R.T + np.array(t)
    return m


def build():
    parts = []
    z_body = STANCE                      # body centre height
    # --- carapace dome on top of the body ---
    car = load("carapace")
    if car:
        parts.append(place(car, t=(0, 0, z_body - car.bounds[0][2])))
    # --- 5 legs: straight rigid brackets splayed out + down to the feet ---
    br = load("leg_bracket")
    foot = load("foot")
    grip = load("grip_hand")
    r_root, z_root = R_BODY - 10, z_body - 20
    # pitch so the (straight) bracket tip lands near the footprint ring at the ground
    reach = br.bounds[1][0] - br.bounds[0][0] if br else 200
    pitch = math.atan2(z_root - 10, R_FOOT - r_root)      # down-and-out
    for i in range(N):
        yaw = math.radians(90) + i * 2 * math.pi / N       # limb0 toward +Y (front)
        R = Rz(yaw) @ Ry(pitch)
        root = (r_root * math.cos(yaw), r_root * math.sin(yaw), z_root)
        if br:
            parts.append(place(br, R, root))
        # foot / grip at the bracket tip
        tip_local = np.array([reach, 0, 0])
        tip = R @ tip_local + np.array(root)
        end = grip if (grip is not None and i in (1, 4)) else foot
        if end is not None:
            parts.append(place(end, Rz(yaw), tip))
    return parts


def render():
    parts = build()
    views = [("iso", 22, -60), ("front", 8, 90), ("top", 89, -90)]
    fig = plt.figure(figsize=(16, 6))
    for k, (name, elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, 3, k + 1, projection="3d")
        for m in parts:
            ax.add_collection3d(Poly3DCollection(
                m.vertices[m.faces], facecolor=STONE, edgecolor="#5a5450",
                linewidths=0.05, alpha=1.0))
        allv = np.vstack([m.vertices for m in parts])
        c = allv.mean(0)
        r = (allv.max(0) - allv.min(0)).max() / 2
        for lim, mid in zip("xyz", c):
            getattr(ax, f"set_{lim}lim")(mid - r, mid + r)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(name, fontsize=11)
    fig.suptitle("ROCKY-5 assembled from CAD parts — current design (stance)",
                 fontsize=13, weight="bold")
    plt.tight_layout()
    out = "docs/media/rocky_assembly.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    render()
