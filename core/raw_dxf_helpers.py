"""Internal helpers for raw DXF entity extraction and metadata shaping."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .dxf_sampling import expand_lwpolyline_points, sample_arc_points
from .raw_dxf_types import LayerInfo, Point2D, RawEntity, SceneRect


def extract_raw_entity(
    entity: Any,
    entity_type: str,
    layer_name: str,
) -> tuple[RawEntity | None, list[Point2D]]:
    """Convert a supported DXF entity into the raw dictionary shape used by the app."""

    if entity_type == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        return (
            {
                "type": "LINE",
                "start": (start.x, start.y),
                "end": (end.x, end.y),
                "layer": layer_name,
            },
            [(start.x, start.y), (end.x, end.y)],
        )

    if entity_type == "CIRCLE":
        center = entity.dxf.center
        radius = float(entity.dxf.radius)
        return (
            {
                "type": "CIRCLE",
                "center": (center.x, center.y),
                "radius": radius,
                "layer": layer_name,
            },
            [
                (center.x - radius, center.y - radius),
                (center.x + radius, center.y + radius),
            ],
        )

    if entity_type == "ARC":
        center = entity.dxf.center
        radius = float(entity.dxf.radius)
        points = sample_arc_points(center.x, center.y, radius, entity.dxf.start_angle, entity.dxf.end_angle)
        return (
            {
                "type": "ARC",
                "center": (center.x, center.y),
                "radius": radius,
                "start_angle": float(entity.dxf.start_angle),
                "end_angle": float(entity.dxf.end_angle),
                "points": points,
                "layer": layer_name,
            },
            points,
        )

    if entity_type == "LWPOLYLINE":
        points = expand_lwpolyline_points(entity)
        if not points:
            return None, []
        return (
            {
                "type": "LWPOLYLINE",
                "points": points,
                "closed": bool(entity.closed),
                "layer": layer_name,
            },
            points,
        )

    if entity_type == "POINT":
        location = entity.dxf.location
        return (
            {
                "type": "POINT",
                "location": (location.x, location.y),
                "layer": layer_name,
            },
            [(location.x, location.y)],
        )

    return None, []


def build_scene_rect(bounds: dict[str, float] | None) -> SceneRect:
    """Build the Qt scene rect used by the 2D preview."""

    if bounds is None:
        return (-50.0, -50.0, 100.0, 100.0)

    width = max(bounds["max_x"] - bounds["min_x"], 1.0)
    height = max(bounds["max_y"] - bounds["min_y"], 1.0)
    margin_x = width * 0.08
    margin_y = height * 0.08
    return (
        bounds["min_x"] - margin_x,
        -(bounds["max_y"] + margin_y),
        width + margin_x * 2,
        height + margin_y * 2,
    )


def build_layer_info(
    document: Any,
    layer_entity_counts: Counter,
    layer_type_counts: dict[str, Counter],
    normalized_mapping: dict[str, str],
) -> list[LayerInfo]:
    """Build sorted layer metadata for the import status UI."""

    layer_info: list[LayerInfo] = []
    known_layer_names: set[str] = set()

    for layer in document.layers:
        layer_name = str(layer.dxf.name)
        known_layer_names.add(layer_name)
        layer_info.append(
            {
                "name": layer_name,
                "color": int(layer.color),
                "linetype": str(layer.dxf.linetype),
                "is_off": bool(layer.is_off()),
                "is_frozen": bool(layer.is_frozen()),
                "is_locked": bool(layer.is_locked()),
                "is_visible": not layer.is_off() and not layer.is_frozen(),
                "plot": bool(getattr(layer.dxf, "plot", 1)),
                "mapped_type": normalized_mapping.get(layer_name.upper()),
                "entity_count": int(layer_entity_counts.get(layer_name, 0)),
                "entity_types": dict(sorted(layer_type_counts.get(layer_name, Counter()).items())),
            }
        )

    for layer_name in sorted(set(layer_entity_counts) - known_layer_names):
        layer_info.append(
            {
                "name": layer_name,
                "color": 7,
                "linetype": "Continuous",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": normalized_mapping.get(layer_name.upper()),
                "entity_count": int(layer_entity_counts.get(layer_name, 0)),
                "entity_types": dict(sorted(layer_type_counts.get(layer_name, Counter()).items())),
            }
        )

    layer_info.sort(key=lambda item: (-item["entity_count"], item["name"].lower()))
    return layer_info


__all__ = ["build_layer_info", "build_scene_rect", "extract_raw_entity"]
