"""Helpers for extracting structured wire geometry from raw DXF entities."""

from __future__ import annotations

import math

from ..raw_dxf_types import LayerInfo, Point2D, RawArcEntity, RawEntity, RawLWPolylineEntity, RawLineEntity
from .wire_models import WireGeometry, WirePoint


def extract_wire_geometries(
    raw_entities: list[RawEntity],
    layer_info: list[LayerInfo],
) -> list[WireGeometry]:
    """Extract deterministic wire records from wire-semantic raw entities."""

    wire_layers = _resolve_wire_layers(layer_info)
    wires: list[WireGeometry] = []

    for entity_index, entity in enumerate(raw_entities):
        layer_name = str(entity.get("layer", "0"))
        if layer_name not in wire_layers:
            continue

        wire = _extract_wire_geometry(entity_index, entity)
        if wire is not None:
            wires.append(wire)

    return wires


def _resolve_wire_layers(layer_info: list[LayerInfo]) -> set[str]:
    wire_layers: set[str] = set()
    for layer in layer_info:
        role_name = layer.get("mapped_type") or layer.get("suggested_role")
        if role_name == "wire":
            wire_layers.add(str(layer["name"]))
    return wire_layers


def _extract_wire_geometry(entity_index: int, entity: RawEntity) -> WireGeometry | None:
    entity_type = entity["type"]
    if entity_type == "LINE":
        return _build_wire_geometry(entity_index, entity, (entity["start"], entity["end"]))
    if entity_type == "ARC":
        points = tuple(entity.get("points", []))
        return _build_wire_geometry(entity_index, entity, points)
    if entity_type == "LWPOLYLINE" and not bool(entity.get("closed")):
        points = tuple(entity.get("points", []))
        return _build_wire_geometry(entity_index, entity, points)
    return None


def _build_wire_geometry(
    entity_index: int,
    entity: RawLineEntity | RawArcEntity | RawLWPolylineEntity,
    points: tuple[Point2D, ...],
) -> WireGeometry | None:
    if len(points) < 2:
        return None

    first_point_xy = (float(points[0][0]), float(points[0][1]))
    second_point_xy = (float(points[-1][0]), float(points[-1][1]))
    if first_point_xy == second_point_xy:
        return None

    route_points = tuple((float(x_value), float(y_value)) for x_value, y_value in points)
    wire_id = f"W{entity_index + 1:04d}"
    first_point = WirePoint(
        point_id=f"{wire_id}-P1",
        wire_id=wire_id,
        role="first",
        x=first_point_xy[0],
        y=first_point_xy[1],
        source_entity_index=entity_index,
    )
    second_point = WirePoint(
        point_id=f"{wire_id}-P2",
        wire_id=wire_id,
        role="second",
        x=second_point_xy[0],
        y=second_point_xy[1],
        source_entity_index=entity_index,
    )

    return WireGeometry(
        wire_id=wire_id,
        layer_name=str(entity.get("layer", "0")),
        source_type=entity["type"],
        source_entity_indices=(entity_index,),
        route_points=route_points,
        first_point=first_point,
        second_point=second_point,
        length=_polyline_length(route_points),
        angle_deg=_wire_angle(first_point_xy, second_point_xy),
        bbox=_route_bbox(route_points),
    )


def _polyline_length(points: tuple[Point2D, ...]) -> float:
    total = 0.0
    for start, end in zip(points, points[1:]):
        total += math.dist(start, end)
    return total


def _wire_angle(first_point: Point2D, second_point: Point2D) -> float:
    delta_x = second_point[0] - first_point[0]
    delta_y = second_point[1] - first_point[1]
    return math.degrees(math.atan2(delta_y, delta_x))


def _route_bbox(points: tuple[Point2D, ...]) -> tuple[float, float, float, float]:
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    return (min(x_values), min(y_values), max(x_values), max(y_values))


__all__ = ["extract_wire_geometries"]
