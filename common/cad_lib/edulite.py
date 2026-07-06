"""Robstride EduLite-05 mounting interface — the real datasheet flange, in one
place (ROBOTS_SPEC.md §4.5.2; constants in standards.EDULITE_*).

Every printed part that hosts an EduLite servo (the leg bracket's three joint
seats, the grip hand's wrist) cuts its mount from THESE builders so the flange
pattern is never re-typed. Mirrors the single-source-of-truth pattern used for
fits/inserts in standards.py.

The real interface (datasheet, D-022):
  * Ø46 round housing rim (the servo body seats in a round pocket, not a square
    slot) — `housing_pocket()`.
  * Ø38.5 pilot spigot that centres the servo — `pilot_recess()`.
  * Ø41.5 PCD bolt circle, M3+M4 fasteners on a 30° grid — `bolt_holes()`.
    Datasheet gives the PCD + "M3+M4 at 30deg" but not the exact count, so we
    realise a symmetric 6-bolt ring at 60° pitch (offset 30°) alternating
    M4-clearance / M3, which lands every bolt on the 30° grid (D-023).
  * Ø24 output collar that must stay free to rotate — `output_bore()`.

All builders return build123d geometry centred on the origin with the servo
MATING FACE at z=0 and the servo body on +Z (i.e. cuts extend toward -Z / into
the host solid). The caller `Pos`/`Rotation`s the returned cut into place.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Pos, Part

from common.cad_lib import standards as S

N_BOLTS = 6                 # 6 on the Ø41.5 PCD (60° pitch, offset 30°) => 30° grid
BOLT_START_DEG = 30.0


def housing_pocket(depth: float, fit: str = "slide") -> Part:
    """Round Ø46 (+fit) seat `depth` mm deep for the servo body/rim. Mating face
    at z=0, pocket opens toward +Z (cuts into -Z)."""
    d = S.EDULITE_HOUSING_DIA_MM + 2 * S.fit(fit)
    return Pos(0, 0, -depth / 2) * Cylinder(radius=d / 2, height=depth)


def pilot_recess(depth: float, fit: str = "slide") -> Part:
    """Ø38.5 (+fit) recess that receives the servo's centring pilot spigot."""
    d = S.EDULITE_PILOT_DIA_MM + 2 * S.fit(fit)
    return Pos(0, 0, -depth / 2) * Cylinder(radius=d / 2, height=depth)


def output_bore(length: float, fit: str = "loose", extend_up: float = 0.0) -> Part:
    """Ø24 (+fit) clearance so the output collar rotates. Spans z=extend_up down
    to z=-(length-extend_up); pass a small extend_up to punch cleanly through a
    face when z=0 sits on it."""
    d = S.EDULITE_OUTPUT_COLLAR_DIA_MM + 2 * S.fit(fit)
    zc = extend_up - length / 2
    return Pos(0, 0, zc) * Cylinder(radius=d / 2, height=length)


def bolt_holes(length: float, extend_up: float = 0.0) -> Part:
    """The Ø41.5 PCD ring: 6 holes at 60° (offset 30°), alternating M4-clearance
    / M3. Each hole spans z=extend_up down to z=-(length-extend_up)."""
    r = S.EDULITE_PCD_MM / 2.0
    zc = extend_up - length / 2
    cut: Part | None = None
    for i in range(N_BOLTS):
        a = math.radians(BOLT_START_DEG + i * (360.0 / N_BOLTS))
        dia = S.M4_INSERT_HOLE_DIA_MM if i % 2 == 0 else S.M3_INSERT_HOLE_DIA_MM
        h = Pos(r * math.cos(a), r * math.sin(a), zc) * Cylinder(radius=dia / 2, height=length)
        cut = h if cut is None else cut + h
    return cut


def flange_cuts(thru: float, extend_up: float = 1.0) -> Part:
    """Convenience: the full through-face flange (PCD bolts + Ø24 output bore) as
    a single cut spanning the host thickness `thru`. Use for a mount that fastens
    THROUGH a face; add `pilot_recess`/`housing_pocket` separately for a seat."""
    return bolt_holes(thru, extend_up) + output_bore(thru, extend_up=extend_up)
