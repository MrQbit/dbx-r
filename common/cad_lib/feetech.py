"""Feetech STS3215 / STS3250 slim serial-servo mounting interface — the real
inline pocket, in one place (ROBOTS_SPEC.md §4.5.2; constants in standards.STS_*).

ROCKY-5's 20 leg joints (D-041) moved off the fat external Robstride QDD cups onto
these SLIM serial servos, EMBEDDED INLINE in the links: the 45.2x24.7x35 body lies
ALONG the strut and only the output horn crosses the joint axis. Every printed leg
part that hosts an STS servo (hip yoke, coxa bracket, femur link, tibia bracket)
cuts its pocket from THESE builders so the servo footprint is never re-typed —
mirrors `edulite.py` for the old QDD and the fits/inserts single-source in
`standards.py`.

The real interface (datasheet, D-041):
  * a rectangular 45.2x24.7x35 body that drops into a slide-fit pocket — `body_pocket()`;
  * an output SPLINE HORN on the +H (35 mm) face, offset STS_OUTPUT_OFF along the body
    length toward the joint — `output_bore()` clears the horn so it drives the far link;
  * 4 case-screw bosses that retain the body — `screw_holes()`;
  * (optional) a 625ZZ IDLER on the far side of the output axis for the double-support
    servo bracket used at the pitch joints — reuse `standards.BEARING_625ZZ_*`.

All builders return build123d geometry in a CANONICAL frame: the OUTPUT AXIS is +Z
through the origin (the horn points +Z, protruding past z=0; cuts extend toward -Z /
into the host), the body LENGTH is along X and its SLIM width along Y, and the body is
offset so its spline sits on the +Z axis. The caller `Pos`/`Rotation`s the returned cut
onto the joint face (leg_mounts.sts_face_cut), exactly like the edulite builders.
"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Part

from common.cad_lib import standards as S


def body_pocket(fit: str = "slide", over: float = 2.0) -> Part:
    """Slide-fit 45.2x24.7x35 (+fit) pocket for the servo body. Output face at z=0
    (opens +Z by `over`, so the pocket breaks the joint face), body on -Z."""
    f = S.fit(fit)
    L = S.STS_BODY_L_MM + 2 * f
    W = S.STS_BODY_W_MM + 2 * f
    H = S.STS_BODY_H_MM + over
    # centre in X so the spline (origin) sits STS_OUTPUT_OFF from the body centre.
    return Pos(-S.STS_OUTPUT_OFF_MM, 0, over - H / 2) * Box(L, W, H)


def output_bore(length: float, fit: str = "loose", back: float = 1.0) -> Part:
    """Ø(horn)+fit clearance so the output horn + driven coupling rotate. Bores on
    the HORN side (+Z, toward the driven segment): spans z=-back up to z=length-back
    (a small `back` counterbore into the body-side face, the rest out past the horn)."""
    d = S.STS_HORN_DIA_MM + 2 * S.fit(fit)
    zc = length / 2 - back
    return Pos(0, 0, zc) * Cylinder(radius=d / 2, height=length)


def screw_holes(length: float, extend_up: float = 1.0) -> Part:
    """The 4 M2.5 case-screw bores (rectangle STS_SCREW_PITCH_L x _W about the body
    centre), axis Z into the body floor. Each spans z=extend_up down to z=-(length)."""
    zc = extend_up - length / 2
    cut: Part | None = None
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = -S.STS_OUTPUT_OFF_MM + sx * S.STS_SCREW_PITCH_L_MM / 2
            y = sy * S.STS_SCREW_PITCH_W_MM / 2
            h = Pos(x, y, zc) * Cylinder(radius=S.STS_SCREW_HOLE_DIA_MM / 2, height=length)
            cut = h if cut is None else cut + h
    return cut


def servo_dummy() -> Part:
    """Solid stand-in (render + interference only, NOT printed): the body box plus
    the protruding output horn, in the canonical frame (horn on +Z at the origin)."""
    body = Pos(-S.STS_OUTPUT_OFF_MM, 0, -S.STS_BODY_H_MM / 2) * Box(
        S.STS_BODY_L_MM, S.STS_BODY_W_MM, S.STS_BODY_H_MM)
    horn = Pos(0, 0, S.STS_HORN_PROTRUDE_MM / 2) * Cylinder(
        radius=S.STS_HORN_DIA_MM / 2, height=S.STS_HORN_PROTRUDE_MM)
    return body + horn
