"""RobotModel -> MJCF (ROBOTS_SPEC.md §5).

Emits a MuJoCo model with a floating base, a floor plane, primitive collision
geoms, explicit inertials (matching the URDF), and one position actuator per
joint carrying the STS3215 PD gains + effort clamp (Appendix A.3). Used for the
G3 settle test and later sim2sim. MJCF box size is HALF-extents (unlike URDF).
"""

from __future__ import annotations

import math

from common.description_gen.model import Link, RobotModel, Shape

# STS3215 sim actuator (Appendix A.3); kp is N·m/rad for the position servo.
KP = 40.0
DAMPING = 0.6
ARMATURE = 0.01


def _geom(shape: Shape, com) -> str:
    cx, cy, cz = com
    pos = f'pos="{cx:.6f} {cy:.6f} {cz:.6f}"'
    if shape.kind == "box":
        lx, ly, lz = shape.dims
        return f'<geom type="box" size="{lx/2:.6f} {ly/2:.6f} {lz/2:.6f}" {pos}/>'
    if shape.kind == "cylinder":
        r, h = shape.dims
        euler = {"z": "0 0 0", "y": "1.5707963 0 0", "x": "0 1.5707963 0"}[shape.axis]
        return f'<geom type="cylinder" size="{r:.6f} {h/2:.6f}" {pos} euler="{euler}"/>'
    if shape.kind == "sphere":
        return f'<geom type="sphere" size="{shape.dims[0]:.6f}" {pos}/>'
    raise ValueError(shape.kind)


def _inertial(link: Link) -> str:
    inr = link.inertia()
    cx, cy, cz = link.com
    return (f'<inertial pos="{cx:.6f} {cy:.6f} {cz:.6f}" mass="{link.mass:.6f}" '
            f'diaginertia="{inr.ixx:.8f} {inr.iyy:.8f} {inr.izz:.8f}"/>')


def _subtree(model: RobotModel, joint, children: dict, indent: int) -> str:
    """Emit a <body> for joint.child and everything below it."""
    pad = "  " * (indent + 1)
    j = joint
    x, y, z = j.origin_xyz
    rr, rp, ry = j.origin_rpy
    link = model.links[j.child]
    ax, ay, az = j.axis
    lines = [
        f'{pad}<body name="{j.child}" pos="{x:.6f} {y:.6f} {z:.6f}" euler="{rr:.6f} {rp:.6f} {ry:.6f}">',
    ]
    if j.jtype == "revolute":
        lines.append(
            f'{pad}  <joint name="{j.name}" type="hinge" axis="{ax:.4f} {ay:.4f} {az:.4f}" '
            f'range="{j.lower:.4f} {j.upper:.4f}" damping="{DAMPING}" armature="{ARMATURE}"/>')
    lines += [
        f'{pad}  {_inertial(link)}',
        f'{pad}  {_geom(link.shape, link.com)}',
    ]
    for gj in children.get(j.child, []):
        lines.append(_subtree(model, gj, children, indent + 1))
    lines.append(f'{pad}</body>')
    return "\n".join(lines)


def to_mjcf(model: RobotModel) -> str:
    children: dict[str, list] = {}
    for j in model.joints:
        children.setdefault(j.parent, []).append(j)

    root = model.links[model.root]
    h = model.default_base_height
    body_lines = [
        f'    <body name="{model.root}" pos="0 0 {h:.6f}">',
        f'      <freejoint/>',
        f'      {_inertial(root)}',
        f'      {_geom(root.shape, root.com)}',
    ]
    for j in children.get(model.root, []):
        body_lines.append(_subtree(model, j, children, 2))
    body_lines.append("    </body>")

    acts = "\n".join(
        f'    <position name="{j.name}" joint="{j.name}" kp="{KP}" '
        f'ctrlrange="{j.lower:.4f} {j.upper:.4f}" forcerange="{-j.effort:.3f} {j.effort:.3f}"/>'
        for j in model.actuated_joints
    )
    return f"""<mujoco model="{model.name}">
  <compiler angle="radian"/>
  <option timestep="0.005" gravity="0 0 -9.81" iterations="50"/>
  <default>
    <geom friction="0.8 0.02 0.001" condim="3"/>
  </default>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1" pos="0 0 0"/>
{chr(10).join(body_lines)}
  </worldbody>
  <actuator>
{acts}
  </actuator>
</mujoco>
"""
