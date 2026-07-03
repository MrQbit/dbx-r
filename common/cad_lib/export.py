"""Export build123d parts to STL and compute mass properties (§4.5, §5).

Runs in the CAD env (build123d/OCP). Bridges CAD geometry to the trimesh-based
QA pipeline: export STL -> load with trimesh -> QA. Mass comes from build123d's
exact solid volume times the material density, so the mass-properties report and
the G1/G2 torque re-check use real numbers, not bounding-box estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from build123d import Part, export_stl

from common.cad_lib.part_meta import PartMeta
from common.cad_lib.standards import density


@dataclass
class MassProps:
    name: str
    material: str
    qty: int
    volume_mm3: float
    unit_mass_g: float
    total_mass_g: float


def part_mass(part: Part, meta: PartMeta) -> MassProps:
    vol = float(part.volume)                       # mm^3 (exact B-rep volume)
    unit_g = vol * density(meta.material) / 1000.0  # g/cm^3 -> g per mm^3/1000
    return MassProps(
        name=meta.name,
        material=meta.material,
        qty=meta.qty,
        volume_mm3=vol,
        unit_mass_g=unit_g,
        total_mass_g=unit_g * meta.qty,
    )


def export_part_stl(part: Part, out_path: Path, tolerance: float = 0.05) -> Path:
    """Write a decimated STL (linear tol 0.05 mm keeps <=20k tris/part, §5)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(part, str(out_path), tolerance=tolerance, angular_tolerance=0.2)
    return out_path
