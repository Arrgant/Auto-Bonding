"""Internal helpers for raw DXF entity extraction and metadata shaping."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .layer_semantics import suggest_layer_semantic_role
from .layer_stack import layer_sort_key
from .dxf_sampling import expand_lwpolyline_points, sample_arc_points, sample_bulge_segment
from .raw_dxf_types import LayerInfo, Point2D, RawEntity, SceneRect


def extract_raw_entity(
    entity: Any,
    entity_type: str,
    layer_name: str,
    *,
    _insert_depth: int = 0,
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

    if entity_type == "ELLIPSE":
        points, is_closed = _expand_ellipse_points(entity)
        if len(points) < 2:
            return None, []
        return (
            {
                "type": "ELLIPSE",
                "points": points,
                "closed": is_closed,
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

    if entity_type in {"TEXT", "ATTRIB", "ATTDEF"}:
        insert = entity.dxf.insert
        text = str(entity.dxf.text or "")
        height = max(float(getattr(entity.dxf, "height", 1.0) or 1.0), 0.1)
        rotation = float(getattr(entity.dxf, "rotation", 0.0) or 0.0)
        box_width = _estimate_text_width(text, height, float(getattr(entity.dxf, "width", 1.0) or 1.0))
        return (
            {
                "type": entity_type,
                "text": text,
                "insert": (insert.x, insert.y),
                "height": height,
                "rotation": rotation,
                "box_width": box_width,
                "layer": layer_name,
            },
            _build_text_bounds((insert.x, insert.y), box_width, height, rotation),
        )

    if entity_type == "MTEXT":
        insert = entity.dxf.insert
        text = str(entity.plain_text() or "")
        height = max(float(getattr(entity.dxf, "char_height", 1.0) or 1.0), 0.1)
        rotation = float(getattr(entity.dxf, "rotation", 0.0) or 0.0)
        box_width = _estimate_text_width(text, height, float(getattr(entity.dxf, "width", 0.0) or 0.0))
        line_count = max(text.count("\n") + 1, 1)
        box_height = height * line_count * 1.35
        return (
            {
                "type": "MTEXT",
                "text": text,
                "insert": (insert.x, insert.y),
                "height": height,
                "rotation": rotation,
                "box_width": box_width,
                "layer": layer_name,
            },
            _build_text_bounds((insert.x, insert.y), box_width, box_height, rotation),
        )

    if entity_type == "HATCH":
        hatch_paths: list[list[Point2D]] = []
        bound_points: list[Point2D] = []
        for boundary_path in entity.paths:
            if not hasattr(boundary_path, "vertices"):
                continue
            path_points = _expand_hatch_polyline_path(boundary_path)
            if len(path_points) < 2:
                continue
            hatch_paths.append(path_points)
            bound_points.extend(path_points)

        if not hatch_paths:
            return None, []

        return (
            {
                "type": "HATCH",
                "paths": hatch_paths,
                "solid_fill": bool(getattr(entity.dxf, "solid_fill", 1)),
                "layer": layer_name,
            },
            bound_points,
        )

    if entity_type == "SOLID":
        points = _extract_solid_points(entity)
        if len(points) < 3:
            return None, []

        return (
            {
                "type": "SOLID",
                "points": points,
                "layer": layer_name,
            },
            points,
        )

    if entity_type == "INSERT":
        if _insert_depth >= 8:
            return None, []

        children: list[RawEntity] = []
        bound_points: list[Point2D] = []
        try:
            virtual_entities = list(entity.virtual_entities())
        except Exception:
            virtual_entities = []

        for child in virtual_entities:
            child_layer_name = str(getattr(child.dxf, "layer", layer_name) or layer_name)
            if child_layer_name == "0":
                child_layer_name = layer_name
            child_raw_entity, child_points = extract_raw_entity(
                child,
                child.dxftype(),
                child_layer_name,
                _insert_depth=_insert_depth + 1,
            )
            if child_raw_entity is None:
                continue
            children.append(child_raw_entity)
            bound_points.extend(child_points)

        for attrib in getattr(entity, "attribs", []):
            attrib_layer_name = str(getattr(attrib.dxf, "layer", layer_name) or layer_name)
            if attrib_layer_name == "0":
                attrib_layer_name = layer_name
            attrib_raw_entity, attrib_points = extract_raw_entity(
                attrib,
                attrib.dxftype(),
                attrib_layer_name,
                _insert_depth=_insert_depth + 1,
            )
            if attrib_raw_entity is None:
                continue
            children.append(attrib_raw_entity)
            bound_points.extend(attrib_points)

        if not children:
            return None, []

        insert_point = entity.dxf.insert
        return (
            {
                "type": "INSERT",
                "name": str(getattr(entity.dxf, "name", "") or ""),
                "insert": (insert_point.x, insert_point.y),
                "rotation": float(getattr(entity.dxf, "rotation", 0.0) or 0.0),
                "xscale": float(getattr(entity.dxf, "xscale", 1.0) or 1.0),
                "yscale": float(getattr(entity.dxf, "yscale", 1.0) or 1.0),
                "entities": children,
                "layer": layer_name,
            },
            bound_points,
        )

    return None, []


def _estimate_text_width(text: str, height: float, declared_width: float) -> float:
    if declared_width > 0.0:
        return declared_width

    lines = text.splitlines() or [""]
    max_chars = max((len(line) for line in lines), default=1)
    return max(height * max(max_chars, 1) * 0.62, height)


def _build_text_bounds(
    insert: Point2D,
    box_width: float,
    box_height: float,
    rotation: float,
) -> list[Point2D]:
    x_origin, y_origin = insert
    angle = math.radians(rotation)
    cos_value = math.cos(angle)
    sin_value = math.sin(angle)
    corners = [
        (0.0, 0.0),
        (box_width, 0.0),
        (box_width, box_height),
        (0.0, box_height),
    ]
    return [
        (
            x_origin + dx * cos_value - dy * sin_value,
            y_origin + dx * sin_value + dy * cos_value,
        )
        for dx, dy in corners
    ]


def _expand_hatch_polyline_path(boundary_path: Any) -> list[Point2D]:
    vertices = list(getattr(boundary_path, "vertices", []) or [])
    if not vertices:
        return []

    points: list[Point2D] = [(float(vertices[0][0]), float(vertices[0][1]))]
    pairs = list(zip(vertices, vertices[1:]))
    if bool(getattr(boundary_path, "is_closed", False)):
        pairs.append((vertices[-1], vertices[0]))

    for start_vertex, end_vertex in pairs:
        start_point = (float(start_vertex[0]), float(start_vertex[1]))
        end_point = (float(end_vertex[0]), float(end_vertex[1]))
        bulge = float(start_vertex[2]) if len(start_vertex) > 2 else 0.0
        points.extend(sample_bulge_segment(start_point, end_point, bulge))

    if len(points) > 1 and bool(getattr(boundary_path, "is_closed", False)):
        first_x, first_y = points[0]
        last_x, last_y = points[-1]
        if math.isclose(first_x, last_x, abs_tol=1e-9) and math.isclose(first_y, last_y, abs_tol=1e-9):
            points.pop()

    return points


def _expand_ellipse_points(entity: Any) -> tuple[list[Point2D], bool]:
    center = entity.dxf.center
    major_axis = entity.dxf.major_axis
    ratio = abs(float(getattr(entity.dxf, "ratio", 1.0) or 1.0))
    start_param = float(getattr(entity.dxf, "start_param", 0.0) or 0.0)
    end_param = float(getattr(entity.dxf, "end_param", math.tau) or math.tau)
    while end_param < start_param:
        end_param += math.tau

    sweep = end_param - start_param
    if abs(sweep) <= 1e-9:
        return [], False

    major_x = float(major_axis.x)
    major_y = float(major_axis.y)
    minor_x = -major_y * ratio
    minor_y = major_x * ratio

    is_closed = math.isclose(abs(sweep), math.tau, rel_tol=1e-6, abs_tol=1e-6)
    steps = max(16, min(96, int(abs(sweep) / (math.pi / 24.0)) + 1))
    points = [
        (
            center.x + math.cos(start_param + sweep * index / steps) * major_x + math.sin(start_param + sweep * index / steps) * minor_x,
            center.y + math.cos(start_param + sweep * index / steps) * major_y + math.sin(start_param + sweep * index / steps) * minor_y,
        )
        for index in range(steps + 1)
    ]
    if is_closed:
        points.pop()
    return points, is_closed


def _extract_solid_points(entity: Any) -> list[Point2D]:
    raw_points = [
        getattr(entity.dxf, "vtx0", None),
        getattr(entity.dxf, "vtx1", None),
        getattr(entity.dxf, "vtx3", None),
        getattr(entity.dxf, "vtx2", None),
    ]
    points: list[Point2D] = []
    for point in raw_points:
        if point is None:
            continue
        xy_point = (float(point.x), float(point.y))
        if not points or not (
            math.isclose(points[-1][0], xy_point[0], abs_tol=1e-9)
            and math.isclose(points[-1][1], xy_point[1], abs_tol=1e-9)
        ):
            points.append(xy_point)

    if len(points) > 2 and math.isclose(points[0][0], points[-1][0], abs_tol=1e-9) and math.isclose(points[0][1], points[-1][1], abs_tol=1e-9):
        points.pop()

    return points


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
    enabled_layers: set[str] | None = None,
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
                "suggested_role": suggest_layer_semantic_role(layer_name),
                "enabled": True if enabled_layers is None else layer_name in enabled_layers,
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
                "suggested_role": suggest_layer_semantic_role(layer_name),
                "enabled": True if enabled_layers is None else layer_name in enabled_layers,
                "entity_count": int(layer_entity_counts.get(layer_name, 0)),
                "entity_types": dict(sorted(layer_type_counts.get(layer_name, Counter()).items())),
            }
        )

    layer_info.sort(key=lambda item: layer_sort_key(str(item["name"])))
    return layer_info


__all__ = ["build_layer_info", "build_scene_rect", "extract_raw_entity"]
