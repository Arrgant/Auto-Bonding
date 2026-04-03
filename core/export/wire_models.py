"""Structured wire export models derived from 06_WIRE geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..raw_dxf_types import Point2D

WirePointRole = Literal["first", "second"]
WireAxis = Literal["x", "y"]
WireDirection = Literal["asc", "desc"]
WireGroupMode = Literal["fixed", "clustered"]


@dataclass(frozen=True)
class WirePoint:
    """One bond point that belongs to a single wire."""

    point_id: str
    wire_id: str
    role: WirePointRole
    x: float
    y: float
    z: float | None = None
    source_entity_index: int | None = None

    def resolved_z(self, default_z: float) -> float:
        """Return the effective export Z, preserving an explicit zero value."""

        if self.z is None:
            return default_z
        return self.z


@dataclass(frozen=True)
class WireGeometry:
    """One extracted wire with its geometric endpoints and path."""

    wire_id: str
    layer_name: str
    source_type: str
    source_entity_indices: tuple[int, ...]
    route_points: tuple[Point2D, ...]
    first_point: WirePoint
    second_point: WirePoint
    length: float
    angle_deg: float
    bbox: tuple[float, float, float, float]
    cluster_id: str | None = None

    @property
    def centroid(self) -> Point2D:
        min_x, min_y, max_x, max_y = self.bbox
        return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)


@dataclass(frozen=True)
class WireOrderingConfig:
    """Deterministic ordering controls for production-style numbering."""

    primary_axis: WireAxis = "x"
    primary_direction: WireDirection = "asc"
    secondary_direction: WireDirection = "asc"
    start_role: WirePointRole = "first"
    group_mode: WireGroupMode = "fixed"
    group_no: int = 1


@dataclass(frozen=True)
class OrderedWireRecord:
    """One wire plus its production sequence numbers."""

    wire_id: str
    wire_seq: int
    group_no: int
    first_point_seq: int
    second_point_seq: int
    geometry: WireGeometry


__all__ = [
    "OrderedWireRecord",
    "WireAxis",
    "WireDirection",
    "WireGroupMode",
    "WireGeometry",
    "WireOrderingConfig",
    "WirePoint",
    "WirePointRole",
]
