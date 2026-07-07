"""ROCKY-5 leg-chassis EduLite / bearing mount cutters (build123d).

Thin build123d layer over `common.cad_lib.edulite` so every leg-chassis part cuts
its servo interface from the SAME real datasheet flange (Ø41.5 PCD M3+M4, Ø38.5
pilot, Ø24 output) instead of re-typing it — mirrors how leg_bracket / grip_palm
reuse the edulite builders. Adds the orientation glue (a mount cut can face any of
±X/±Y/±Z) plus a 625ZZ press-seat cutter for the non-driven pitch pivots.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rotation, Part

from common.cad_lib import standards as S
from common.cad_lib import edulite as E
from common.cad_lib import feetech as F
from rocky.cad.parts import leg_geom as G

# Rotation (deg about X,Y,Z) that sends a builder's local +Z (the OUTPUT direction,
# cuts toward -Z) onto the requested outward face normal. Shared by the edulite QDD
# flange (hand mount) and the STS inline-servo pocket (leg joints).
_FACE_ROT = {
    "+Z": (0, 0, 0),
    "-Z": (180, 0, 0),
    "+Y": (-90, 0, 0),
    "-Y": (90, 0, 0),
    "+X": (0, 90, 0),
    "-X": (0, -90, 0),
}


def sts_face_cut(
    joint_pt: tuple[float, float, float],
    out_normal: str,
    through: float,
    with_output: bool = True,
    with_screws: bool = True,
    body_over: float = 2.0,
) -> Part:
    """Real Feetech STS inline-servo pocket at a joint whose OUTPUT AXIS passes
    through `joint_pt` along `out_normal` (the direction the horn drives). The 45.2x
    24.7x35 body drops into the slide pocket lying ALONG the link; the horn punches
    `through` the joint wall so it couples the driven segment; 4 M2.5 case screws
    retain it. Slims the leg — the fat external Ø54 EduLite cup is gone (D-041)."""
    cut = F.body_pocket(over=body_over)
    if with_screws:
        cut = cut + F.screw_holes(S.STS_BODY_H_MM + body_over, extend_up=1.0)
    if with_output:
        cut = cut + F.output_bore(through, fit="loose", back=1.0)
    cut = Rotation(*_FACE_ROT[out_normal]) * cut
    return Pos(*joint_pt) * cut


def sts_body(joint_pt: tuple[float, float, float], out_normal: str) -> Part:
    """Solid STS servo stand-in placed at a joint (render + interference only)."""
    return Pos(*joint_pt) * Rotation(*_FACE_ROT[out_normal]) * F.servo_dummy()


def box_from_aabb(aabb: tuple[float, float, float, float, float, float],
                  grow: float = 0.0) -> Part:
    """A build123d Box spanning the world-frame AABB (grown by `grow` per side)."""
    x0, x1, y0, y1, z0, z1 = aabb
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(
        (x1 - x0) + 2 * grow, (y1 - y0) + 2 * grow, (z1 - z0) + 2 * grow)


def idler_seat_cut(axis_pt: tuple[float, float, float], out_normal: str,
                   back: float, depth: float | None = None) -> Part:
    """625ZZ IDLER seat carrying the FAR end of the output shaft (the double-support
    servo bracket). Bored coaxial with the output axis, `back` mm behind the joint on
    the servo-body (-out_normal) side, into the housing back wall."""
    depth = (S.BEARING_625ZZ_W_MM + 0.6) if depth is None else depth
    d = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
    seat = Pos(0, 0, back - depth / 2) * Cylinder(radius=d / 2, height=depth)
    seat = Rotation(*_FACE_ROT[out_normal]) * seat
    return Pos(*axis_pt) * seat


def edulite_face_cut(
    face_pt: tuple[float, float, float],
    normal: str,
    through: float,
    reg_depth: float = 5.0,
    with_output: bool = True,
    with_register: bool = True,
) -> Part:
    """Real EduLite mount cut on a wall whose OUTER face is at `face_pt` and whose
    outward normal is `normal` (the direction the servo body points). Follows the
    proven leg_bracket pattern:

      * a shallow Ø46 slide HOUSING register that seats/centres the servo body rim
        (replaces the Ø38.5 pilot: a body-rim register avoids the feather-edge the
        Ø38.5 pilot leaves against the Ø41.5 bolt circle), then
      * the Ø41.5 PCD bolts (M3+M4) + the Ø24 output bore punched `through` the
        wall into -normal, so the flange bolts bite and the output collar drives
        the link on the far side.

    `with_register=False` for a face that already has its own deep body pocket
    (the hip yoke) or is a plain bolt-to-print flange (the tibia hand pad).
    """
    cut = E.bolt_holes(through, extend_up=1.0)
    if with_output:
        cut = cut + E.output_bore(through, fit="loose", extend_up=1.0)
    if with_register:
        cut = cut + E.housing_pocket(reg_depth, fit="slide")
    cut = Rotation(*_FACE_ROT[normal]) * cut
    return Pos(*face_pt) * cut


def bearing_seat_cut(
    face_pt: tuple[float, float, float],
    normal: str,
    depth: float | None = None,
) -> Part:
    """Blind 625ZZ press seat opening on the face at `face_pt`, bored into -normal
    (the non-driven side of a pitch pivot). Receives the mating link's Ø5 stub."""
    depth = (S.BEARING_625ZZ_W_MM + 0.6) if depth is None else depth
    d = S.BEARING_625ZZ_OD_MM + 2 * S.FIT_PRESS_MM
    seat = Pos(0, 0, -depth / 2) * Cylinder(radius=d / 2, height=depth)
    seat = Rotation(*_FACE_ROT[normal]) * seat
    return Pos(*face_pt) * seat


def stub_bore_cut(
    face_pt: tuple[float, float, float],
    normal: str,
    length: float,
) -> Part:
    """Ø5 clearance for a stub-axle pin (or the 625ZZ inner race), bored -normal."""
    d = S.BEARING_625ZZ_ID_MM + 2 * S.FIT_SLIDE_MM
    bore = Pos(0, 0, -length / 2) * Cylinder(radius=d / 2, height=length)
    bore = Rotation(*_FACE_ROT[normal]) * bore
    return Pos(*face_pt) * bore


def lattice_beam(
    length: float,
    w: float,
    h: float,
    wall: float = G.STRUT_WALL,
    rib_t: float = G.STRUT_RIB_T,
    rib_pitch: float = G.STRUT_RIB_PITCH,
    wire_d: float = G.STRUT_WIRE_D,
) -> Part:
    """A THIN-WALL gyroid/lattice STRUT (D-040), built centred at the origin with its
    axis along +X. A closed rectangular outer tube (wall thickness `wall`) encloses a
    rib lattice (transverse bulkheads at `rib_pitch`) threaded by an axial Ø`wire_d`
    wiring channel. Watertight, min wall == `wall` (>= the 2.4 mm structural floor).

    The printed part is only the stiff CORE — the Phase-2 sculpt shell carries the
    visible volume. Intended slicer setting: GYROID infill 30-40% inside this wall
    (documented in each strut part's META note). A closed thin-wall tube is far
    stiffer per gram than the old solid/I-beam and, crucially, resists the TORSION
    the new tibia_roll DOF puts through the shank. The hollow core is the wire run.
    """
    cav_w, cav_h = w - 2 * wall, h - 2 * wall
    outer = Box(length, w, h)
    if cav_w <= 0 or cav_h <= 0 or length <= 2 * wall + 2.0:
        return outer                                   # too small to hollow — stay solid
    beam = outer - Box(length - 2 * wall, cav_w, cav_h)   # closed hollow (ends walled)
    # Internal transverse ribs across the cavity.
    span = length - 2 * wall - rib_t
    n = max(1, int(span // rib_pitch) + 1)
    ribs = None
    for i in range(n):
        xr = 0.0 if n == 1 else (-span / 2 + span * i / (n - 1))
        r = Pos(xr, 0, 0) * Box(rib_t, cav_w, cav_h)
        ribs = r if ribs is None else ribs + r
    beam = beam + ribs
    # Axial wiring channel through the ribs (stays inside the cavity -> ends closed).
    if wire_d > 0 and wire_d < min(cav_w, cav_h):
        beam = beam - Rotation(0, 90, 0) * Cylinder(radius=wire_d / 2, height=length - 2 * wall - 0.4)
    return beam
