"""RobotModel -> URDF (ROBOTS_SPEC.md §5).

Collision geometry is primitives ONLY (boxes/cylinders/spheres — never trimesh),
per §5. Visual uses the same primitives for now; decimated per-link STL visuals
swap in as CAD parts are authored (the joint/inertial structure is unaffected).
Inertials come straight from the analytic model, so every tensor is PD.
"""

from __future__ import annotations

import math

from common.description_gen.model import Link, RobotModel, Shape


def _geometry_xml(shape: Shape) -> tuple[str, tuple[float, float, float]]:
    """Return (geometry-inner-xml, extra_rpy) for a shape (URDF cylinders are +Z)."""
    if shape.kind == "box":
        lx, ly, lz = shape.dims
        return f'<box size="{lx:.6f} {ly:.6f} {lz:.6f}"/>', (0.0, 0.0, 0.0)
    if shape.kind == "cylinder":
        r, h = shape.dims
        rpy = {"z": (0, 0, 0), "y": (math.pi / 2, 0, 0), "x": (0, math.pi / 2, 0)}[shape.axis]
        return f'<cylinder radius="{r:.6f}" length="{h:.6f}"/>', rpy
    if shape.kind == "sphere":
        return f'<sphere radius="{shape.dims[0]:.6f}"/>', (0.0, 0.0, 0.0)
    raise ValueError(shape.kind)


def _link_xml(link: Link) -> str:
    inr = link.inertia()
    cx, cy, cz = link.com
    geo, (rr, rp, ry) = _geometry_xml(link.shape)
    origin = f'<origin xyz="{cx:.6f} {cy:.6f} {cz:.6f}" rpy="{rr:.6f} {rp:.6f} {ry:.6f}"/>'
    return f"""  <link name="{link.name}">
    <inertial>
      <origin xyz="{cx:.6f} {cy:.6f} {cz:.6f}"/>
      <mass value="{link.mass:.6f}"/>
      <inertia ixx="{inr.ixx:.8f}" iyy="{inr.iyy:.8f}" izz="{inr.izz:.8f}" ixy="{inr.ixy:.8f}" ixz="{inr.ixz:.8f}" iyz="{inr.iyz:.8f}"/>
    </inertial>
    <visual>{origin}<geometry>{geo}</geometry></visual>
    <collision>{origin}<geometry>{geo}</geometry></collision>
  </link>"""


def _joint_xml(j) -> str:
    x, y, z = j.origin_xyz
    rr, rp, ry = j.origin_rpy
    ax, ay, az = j.axis
    body = [
        f'    <parent link="{j.parent}"/>',
        f'    <child link="{j.child}"/>',
        f'    <origin xyz="{x:.6f} {y:.6f} {z:.6f}" rpy="{rr:.6f} {rp:.6f} {ry:.6f}"/>',
    ]
    if j.jtype == "revolute":
        body += [
            f'    <axis xyz="{ax:.6f} {ay:.6f} {az:.6f}"/>',
            f'    <limit lower="{j.lower:.4f}" upper="{j.upper:.4f}" '
            f'effort="{j.effort:.3f}" velocity="{j.velocity:.3f}"/>',
        ]
    return f'  <joint name="{j.name}" type="{j.jtype}">\n' + "\n".join(body) + "\n  </joint>"


def to_urdf(model: RobotModel) -> str:
    parts = [f'<?xml version="1.0"?>', f'<robot name="{model.name}">']
    parts.append(_link_xml(model.links[model.root]))
    for link_name, link in model.links.items():
        if link_name != model.root:
            parts.append(_link_xml(link))
    for j in model.joints:
        parts.append(_joint_xml(j))
    parts.append("</robot>")
    return "\n".join(parts) + "\n"
