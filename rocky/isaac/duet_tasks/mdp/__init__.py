"""Duet custom MDP terms (Isaac Lab): terrain-curriculum fix + reference-gait
imitation reward, shared by both robots."""

from .curriculums import terrain_levels_track  # noqa: F401
from .rewards import track_reference_gait       # noqa: F401
