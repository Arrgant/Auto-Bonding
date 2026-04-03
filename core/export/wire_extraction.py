"""Helpers for extracting structured wire geometry from raw DXF entities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ..raw_dxf_types import LayerInfo, Point2D, RawArcEntity, RawEntity, RawLWPolylineEntity, RawLineEntity
from .wire_models import WireGeometry, WirePoint


WireMergeEndpointAlignment = Literal["continuous", "same_role_conflict"]


@dataclass(frozen=True)
class WireExtractionSkippedEntity:
    """One wire-layer entity that was not converted into a wire."""

    entity_index: int
    layer_name: str
    entity_type: str
    reason: str


@dataclass(frozen=True)
class WireExtractionAudit:
    """Summary of which wire-layer entities were extracted or skipped."""

    wire_layers: tuple[str, ...]
    extracted_wire_count: int
    candidate_entity_count: int
    skipped_entities: tuple[WireExtractionSkippedEntity, ...]
    merge_candidates: tuple["WireExtractionMergeCandidate", ...]
    extracted_counts_by_type: dict[str, int]
    skipped_counts_by_reason: dict[str, int]


@dataclass(frozen=True)
class WireExtractionMergeCandidate:
    """Two extracted wire fragments that likely belong to one multi-segment wire."""

    first_wire_id: str
    second_wire_id: str
    shared_x: float
    shared_y: float
    first_endpoint_role: str
    second_endpoint_role: str
    endpoint_alignment: WireMergeEndpointAlignment


def extract_wire_geometries(
    raw_entities: list[RawEntity],
    layer_info: list[LayerInfo],
    *,
    merge_tolerance: float = 1e-6,
) -> list[WireGeometry]:
    """Extract deterministic wire records from wire-semantic raw entities."""

    wires, _audit = extract_wire_geometries_with_audit(
        raw_entities,
        layer_info,
        merge_tolerance=merge_tolerance,
    )
    return wires


def extract_wire_geometries_with_audit(
    raw_entities: list[RawEntity],
    layer_info: list[LayerInfo],
    *,
    merge_tolerance: float = 1e-6,
) -> tuple[list[WireGeometry], WireExtractionAudit]:
    """Extract wire records and return a skip/extract summary for diagnostics."""

    wire_layers = _resolve_wire_layers(layer_info)
    wires: list[WireGeometry] = []
    skipped_entities: list[WireExtractionSkippedEntity] = []
    extracted_counts_by_type: dict[str, int] = {}
    skipped_counts_by_reason: dict[str, int] = {}
    candidate_entity_count = 0

    for entity_index, entity in enumerate(raw_entities):
        layer_name = str(entity.get("layer", "0"))
        if layer_name not in wire_layers:
            continue

        candidate_entity_count += 1
        wire, skip_reason = _extract_wire_geometry(entity_index, entity)
        if wire is not None:
            wires.append(wire)
            extracted_counts_by_type[wire.source_type] = extracted_counts_by_type.get(wire.source_type, 0) + 1
            continue
        skipped_entity = WireExtractionSkippedEntity(
            entity_index=entity_index,
            layer_name=layer_name,
            entity_type=str(entity["type"]),
            reason=skip_reason or "unsupported_entity_type",
        )
        skipped_entities.append(skipped_entity)
        skipped_counts_by_reason[skipped_entity.reason] = skipped_counts_by_reason.get(skipped_entity.reason, 0) + 1

    audit = WireExtractionAudit(
        wire_layers=tuple(sorted(wire_layers)),
        extracted_wire_count=len(wires),
        candidate_entity_count=candidate_entity_count,
        skipped_entities=tuple(skipped_entities),
        merge_candidates=_find_merge_candidates(wires, merge_tolerance=merge_tolerance),
        extracted_counts_by_type=extracted_counts_by_type,
        skipped_counts_by_reason=skipped_counts_by_reason,
    )
    return wires, audit


def _resolve_wire_layers(layer_info: list[LayerInfo]) -> set[str]:
    wire_layers: set[str] = set()
    for layer in layer_info:
        role_name = layer.get("mapped_type") or layer.get("suggested_role")
        if role_name == "wire":
            wire_layers.add(str(layer["name"]))
    return wire_layers


def _extract_wire_geometry(entity_index: int, entity: RawEntity) -> tuple[WireGeometry | None, str | None]:
    entity_type = entity["type"]
    if entity_type == "LINE":
        wire = _build_wire_geometry(entity_index, entity, (entity["start"], entity["end"]))
        if wire is None:
            return None, "zero_length_or_insufficient_points"
        return wire, None
    if entity_type == "ARC":
        points = tuple(entity.get("points", []))
        wire = _build_wire_geometry(entity_index, entity, points)
        if wire is None:
            return None, "zero_length_or_insufficient_points"
        return wire, None
    if entity_type == "LWPOLYLINE" and bool(entity.get("closed")):
        return None, "closed_lwpolyline"
    if entity_type == "LWPOLYLINE":
        points = tuple(entity.get("points", []))
        wire = _build_wire_geometry(entity_index, entity, points)
        if wire is None:
            return None, "zero_length_or_insufficient_points"
        return wire, None
    return None, "unsupported_entity_type"


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


def _find_merge_candidates(
    wires: list[WireGeometry],
    *,
    merge_tolerance: float,
) -> tuple[WireExtractionMergeCandidate, ...]:
    if not wires:
        return ()

    tolerance = max(float(merge_tolerance), 1e-12)
    endpoint_groups: dict[tuple[str, int, int], list[tuple[WireGeometry, str, Point2D]]] = {}
    for wire in wires:
        for role, point in (("first", wire.first_point), ("second", wire.second_point)):
            key = (
                wire.layer_name,
                int(round(point.x / tolerance)),
                int(round(point.y / tolerance)),
            )
            endpoint_groups.setdefault(key, []).append((wire, role, (point.x, point.y)))

    candidates: list[WireExtractionMergeCandidate] = []
    for grouped_endpoints in endpoint_groups.values():
        if len(grouped_endpoints) != 2:
            continue
        first_entry, second_entry = grouped_endpoints
        first_wire, first_role, first_xy = first_entry
        second_wire, second_role, second_xy = second_entry
        if first_wire.wire_id == second_wire.wire_id:
            continue
        if math.dist(first_xy, second_xy) > tolerance:
            continue
        candidates.append(
            WireExtractionMergeCandidate(
                first_wire_id=first_wire.wire_id,
                second_wire_id=second_wire.wire_id,
                shared_x=(first_xy[0] + second_xy[0]) / 2.0,
                shared_y=(first_xy[1] + second_xy[1]) / 2.0,
                first_endpoint_role=first_role,
                second_endpoint_role=second_role,
                endpoint_alignment=_merge_endpoint_alignment(first_role, second_role),
            )
        )

    return tuple(candidates)


def _merge_endpoint_alignment(
    first_role: str,
    second_role: str,
) -> WireMergeEndpointAlignment:
    if first_role == second_role:
        return "same_role_conflict"
    return "continuous"


__all__ = [
    "WireExtractionAudit",
    "WireExtractionMergeCandidate",
    "WireExtractionSkippedEntity",
    "WireMergeEndpointAlignment",
    "extract_wire_geometries",
    "extract_wire_geometries_with_audit",
]
