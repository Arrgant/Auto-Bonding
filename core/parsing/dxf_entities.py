"""Stateless DXF entity parsing helpers."""

from __future__ import annotations

from typing import Any

from ..dxf_sampling import expand_lwpolyline_points, sample_bulge_segment
from ..geometry.converter import BondingElement


def resolve_element_type(layer: str, layer_mapping: dict[str, str]) -> str:
    """Resolve a DXF layer name into an internal bonding element type."""

    return layer_mapping.get(layer.upper(), "unknown")


def parse_dxf_entity(entity: Any, element_type: str, layer: str) -> BondingElement | None:
    """Parse one DXF entity into a bonding element when supported."""

    entity_type = entity.dxftype()
    if entity_type == "LINE":
        return parse_line(entity, element_type, layer)
    if entity_type == "CIRCLE":
        return parse_circle(entity, element_type, layer)
    if entity_type == "ARC":
        return parse_arc(entity, element_type, layer)
    if entity_type == "LWPOLYLINE":
        return parse_polyline(entity, element_type, layer)
    if entity_type == "POINT":
        return parse_point(entity, element_type, layer)
    return None


def parse_line(entity: Any, element_type: str, layer: str) -> BondingElement:
    """Parse a LINE entity."""

    start = entity.dxf.start
    end = entity.dxf.end
    return BondingElement(
        element_type=element_type,
        layer=layer,
        geometry={
            "p1": [start.x, start.y, start.z],
            "p2": [end.x, end.y, end.z],
        },
        properties={
            "layer": layer,
            "color": entity.dxf.color if hasattr(entity.dxf, "color") else 7,
        },
    )


def parse_circle(entity: Any, element_type: str, layer: str) -> BondingElement:
    """Parse a CIRCLE entity."""

    center = entity.dxf.center
    radius = entity.dxf.radius
    return BondingElement(
        element_type=element_type,
        layer=layer,
        geometry={
            "center": [center.x, center.y, center.z],
            "radius": radius,
        },
        properties={
            "layer": layer,
            "diameter": radius * 2,
        },
    )


def parse_arc(entity: Any, element_type: str, layer: str) -> BondingElement:
    """Parse an ARC entity."""

    center = entity.dxf.center
    radius = entity.dxf.radius
    start_angle = entity.dxf.start_angle
    end_angle = entity.dxf.end_angle
    return BondingElement(
        element_type=element_type,
        layer=layer,
        geometry={
            "center": [center.x, center.y, center.z],
            "radius": radius,
            "start_angle": start_angle,
            "end_angle": end_angle,
        },
        properties={
            "layer": layer,
            "arc_length": radius * (end_angle - start_angle),
        },
    )


def parse_polyline(entity: Any, element_type: str, layer: str) -> BondingElement:
    """Parse an LWPOLYLINE entity, expanding bulge segments into sampled points."""

    return BondingElement(
        element_type=element_type,
        layer=layer,
        geometry={
            "points": expand_polyline_points(entity),
            "closed": entity.closed,
        },
        properties={
            "layer": layer,
            "width": entity.dxf.const_width if hasattr(entity.dxf, "const_width") else 0,
        },
    )


def parse_point(entity: Any, element_type: str, layer: str) -> BondingElement:
    """Parse a POINT entity."""

    location = entity.dxf.location
    return BondingElement(
        element_type=element_type,
        layer=layer,
        geometry={
            "x": location.x,
            "y": location.y,
            "z": location.z,
        },
        properties={"layer": layer},
    )


def expand_polyline_points(entity: Any) -> list[list[float]]:
    """Expand polyline vertices into sampled XY points, preserving bulge arcs."""

    return [[x_value, y_value, 0.0] for x_value, y_value in expand_lwpolyline_points(entity)]


def sample_bulge_segment(
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    bulge: float,
) -> list[list[float]]:
    """Sample a bulge segment into intermediate points."""

    return [[x_value, y_value, 0.0] for x_value, y_value in sample_bulge_segment(start_point, end_point, bulge)]


__all__ = [
    "expand_polyline_points",
    "parse_arc",
    "parse_circle",
    "parse_dxf_entity",
    "parse_line",
    "parse_point",
    "parse_polyline",
    "resolve_element_type",
    "sample_bulge_segment",
]
