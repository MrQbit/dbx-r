"""PartMeta — the contract every printable part declares (ROBOTS_SPEC.md §4.5.1).

Each `<robot>/cad/parts/<name>.py` exports:
    def part() -> build123d.Part      # the geometry
    META = PartMeta(...)              # everything the pipeline needs about it

PartMeta is pure-Python (no CAD dependency) so BOM/print/QA tooling can import
it without pulling in build123d/OCP.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Insert:
    """A threaded insert / bearing seat referenced by a part."""
    kind: str            # "m3_heatset" | "m2_selftap" | "bearing_625zz"
    count: int
    note: str = ""


@dataclass(frozen=True)
class PartMeta:
    name: str
    material: str                       # "PETG" | "PLA" | "TPU"
    qty: int
    # Print orientation as a quaternion (w, x, y, z) applied before slicing.
    orientation_quat: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    inserts: tuple[Insert, ...] = ()
    # Mating clearances actually used, keyed by feature -> fit kind (audit trail).
    clearances: dict[str, str] = field(default_factory=dict)
    cosmetic: bool = False              # cosmetic parts use the 1.6 mm min wall
    supports: str = "none"              # "none" | "tree" | "normal"
    plate_group: str = "default"        # which print plate this part belongs to

    @property
    def min_wall_mm(self) -> float:
        from common.cad_lib.standards import MIN_WALL_COSMETIC_MM, MIN_WALL_STRUCTURAL_MM
        return MIN_WALL_COSMETIC_MM if self.cosmetic else MIN_WALL_STRUCTURAL_MM
