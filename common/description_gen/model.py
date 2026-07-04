"""Robot description model — the deterministic core of the pipeline (§5).

params.yaml -> RobotModel (links + joints + default pose) -> URDF / MJCF / USD.
Inertias are computed analytically from uniform-density primitives, so every
tensor is positive-definite by construction and equals its own uniform-density
estimate (the G3 "within 10x" check). Links backed by real CAD swap their mass
in later; the shape-based inertia stays a valid estimate.

Frame convention: each link's origin sits at its proximal (parent) joint; limb
segments extend along -Z (downward in the neutral standing pose).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Inertia:
    ixx: float
    iyy: float
    izz: float
    ixy: float = 0.0
    ixz: float = 0.0
    iyz: float = 0.0

    def matrix(self) -> np.ndarray:
        return np.array([
            [self.ixx, self.ixy, self.ixz],
            [self.ixy, self.iyy, self.iyz],
            [self.ixz, self.iyz, self.izz],
        ])


def box_inertia(mass: float, dims: tuple[float, float, float]) -> Inertia:
    lx, ly, lz = dims
    return Inertia(
        ixx=mass * (ly * ly + lz * lz) / 12.0,
        iyy=mass * (lx * lx + lz * lz) / 12.0,
        izz=mass * (lx * lx + ly * ly) / 12.0,
    )


def cylinder_inertia(mass: float, radius: float, height: float, axis: str = "z") -> Inertia:
    ir = mass * (3 * radius * radius + height * height) / 12.0  # transverse
    ia = mass * radius * radius / 2.0                            # about axis
    if axis == "z":
        return Inertia(ixx=ir, iyy=ir, izz=ia)
    if axis == "y":
        return Inertia(ixx=ir, iyy=ia, izz=ir)
    return Inertia(ixx=ia, iyy=ir, izz=ir)


@dataclass
class Shape:
    kind: str                      # "box" | "cylinder" | "sphere"
    dims: tuple[float, ...]        # box:(lx,ly,lz) cyl:(r,h) sphere:(r,)
    axis: str = "z"                # cylinder axis


@dataclass
class Link:
    name: str
    mass: float                    # kg
    shape: Shape                   # collision primitive + inertia source (SI, metres)
    com: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def inertia(self) -> Inertia:
        if self.shape.kind == "box":
            return box_inertia(self.mass, self.shape.dims)  # type: ignore[arg-type]
        if self.shape.kind == "cylinder":
            r, h = self.shape.dims
            return cylinder_inertia(self.mass, r, h, self.shape.axis)
        if self.shape.kind == "sphere":
            r = self.shape.dims[0]
            i = 2.0 * self.mass * r * r / 5.0
            return Inertia(ixx=i, iyy=i, izz=i)
        raise ValueError(f"unknown shape {self.shape.kind!r}")

    def uniform_estimate_inertia(self) -> Inertia:
        """Bounding-box uniform-density estimate for the G3 within-10x check."""
        if self.shape.kind == "box":
            dims = self.shape.dims
        elif self.shape.kind == "cylinder":
            r, h = self.shape.dims
            d = 2 * r
            dims = (d, d, h) if self.shape.axis == "z" else (
                (d, h, d) if self.shape.axis == "y" else (h, d, d))
        else:
            r = self.shape.dims[0]
            dims = (2 * r, 2 * r, 2 * r)
        return box_inertia(self.mass, dims)  # type: ignore[arg-type]


@dataclass
class Joint:
    name: str
    jtype: str                     # "revolute" | "fixed"
    parent: str
    child: str
    origin_xyz: tuple[float, float, float]
    origin_rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    lower: float = 0.0
    upper: float = 0.0
    effort: float = 0.0            # N·m
    velocity: float = 0.0          # rad/s
    servo_id: int | None = None


@dataclass
class RobotModel:
    name: str
    root: str
    links: dict[str, Link] = field(default_factory=dict)
    joints: list[Joint] = field(default_factory=list)
    default_q: dict[str, float] = field(default_factory=dict)
    default_base_height: float = 0.0   # base z (m) that plants the default pose

    def add_link(self, link: Link) -> None:
        self.links[link.name] = link

    def add_joint(self, joint: Joint) -> None:
        self.joints.append(joint)

    @property
    def actuated_joints(self) -> list[Joint]:
        return [j for j in self.joints if j.jtype == "revolute"]

    def total_mass(self) -> float:
        return sum(l.mass for l in self.links.values())
