"""Helpers for extracting structured wire geometry from raw DXF entities."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from ..dxf_sampling import expand_lwpolyline_points, sample_arc_points
from ..raw_dxf_types import LayerInfo, Point2D, RawEntity
from .wire_models import WireGeometry, WirePoint


WireMergeEndpointAlignment = Literal["continuous", "same_role_conflict"]
WireMergeAction = Literal["join_as_is", "reverse_first_then_join", "reverse_second_then_join"]
_PAD_MAX_SIDE = 2.5
_PAD_MAX_AREA = 4.0
_PAD_FILTER_MAX_LENGTH = 2.0
_PAD_DIAGONAL_MAX_LENGTH = 1.2
_PAD_DIAGONAL_ANGLE_TOLERANCE_DEG = 5.0
_WIRE_LAYER_ENTITY_TYPES = ("LINE", "LWPOLYLINE", "POLYLINE", "INSERT", "ARC", "SPLINE")


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
    wire_layer_entity_type_counts: dict[str, int]
    raw_candidate_wire_count: int
    pad_filtered_wire_count: int
    pre_merge_wire_path_count: int
    final_wire_paths: tuple["WireExtractionPathSummary", ...]


@dataclass(frozen=True)
class WireExtractionPathSummary:
    """One final wire-path summary used by audit/debug output."""

    wire_id: str
    length: float
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    bend_count: int


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


@dataclass(frozen=True)
class WireExtractionMergeProposal:
    """One suggested pairwise merge operation derived from audit candidates."""

    source_wire_id: str
    target_wire_id: str
    shared_x: float
    shared_y: float
    action: WireMergeAction
    reverse_wire_ids: tuple[str, ...]
    source_endpoint_role: str
    target_endpoint_role: str


@dataclass(frozen=True)
class _WireRouteCandidate:
    source_entity_indices: tuple[int, ...]
    layer_name: str
    source_type: str
    points: tuple[Point2D, ...]

    @property
    def length(self) -> float:
        return _polyline_length(self.points)

    @property
    def start_point(self) -> Point2D:
        return self.points[0]

    @property
    def end_point(self) -> Point2D:
        return self.points[-1]


@dataclass(frozen=True)
class _PadBBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def contains_all_points(self, points: Iterable[Point2D], *, tolerance: float) -> bool:
        return all(
            self.min_x - tolerance <= point[0] <= self.max_x + tolerance
            and self.min_y - tolerance <= point[1] <= self.max_y + tolerance
            for point in points
        )


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
    tolerance = max(float(merge_tolerance), 1e-12)
    wire_layer_entity_type_counts = _collect_wire_layer_entity_type_counts(
        raw_entities,
        layer_info,
        wire_layers,
    )
    wires: list[WireGeometry] = []
    skipped_entities: list[WireExtractionSkippedEntity] = []
    extracted_counts_by_type: dict[str, int] = {}
    skipped_counts_by_reason: dict[str, int] = {}
    route_candidates: list[_WireRouteCandidate] = []
    pad_outline_bboxes: list[_PadBBox] = []
    candidate_entity_count = 0

    for entity_index, entity in enumerate(raw_entities):
        layer_name = _entity_layer_name(entity)
        if layer_name not in wire_layers:
            continue

        candidate_entity_count += 1
        route_candidates.extend(
            _collect_wire_route_candidates(
                entity_index,
                entity,
                fallback_layer_name=layer_name,
                pad_outline_bboxes=pad_outline_bboxes,
                skipped_entities=skipped_entities,
                skipped_counts_by_reason=skipped_counts_by_reason,
            )
        )

    merge_candidates = _find_merge_candidates_for_routes(route_candidates, merge_tolerance=tolerance)
    pad_bboxes = _collect_pad_bboxes(
        route_candidates,
        pad_outline_bboxes,
        tolerance=tolerance,
    )
    filtered_candidates = _filter_pad_symbol_routes(
        route_candidates,
        pad_bboxes,
        tolerance=tolerance,
        skipped_entities=skipped_entities,
        skipped_counts_by_reason=skipped_counts_by_reason,
    )
    merged_candidates = _merge_connected_route_candidates(filtered_candidates, tolerance=tolerance)
    for candidate in filtered_candidates:
        extracted_counts_by_type[candidate.source_type] = (
            extracted_counts_by_type.get(candidate.source_type, 0) + 1
        )
    for wire_index, candidate in enumerate(merged_candidates, start=1):
        wire = _build_wire_geometry_from_route(wire_index, candidate)
        if wire is not None:
            wires.append(wire)

    final_wire_paths = tuple(
        WireExtractionPathSummary(
            wire_id=wire.wire_id,
            length=wire.length,
            start_x=wire.first_point.x,
            start_y=wire.first_point.y,
            end_x=wire.second_point.x,
            end_y=wire.second_point.y,
            bend_count=max(len(wire.route_points) - 2, 0),
        )
        for wire in wires
    )

    audit = WireExtractionAudit(
        wire_layers=tuple(sorted(wire_layers)),
        extracted_wire_count=len(wires),
        candidate_entity_count=candidate_entity_count,
        skipped_entities=tuple(skipped_entities),
        merge_candidates=merge_candidates,
        extracted_counts_by_type=extracted_counts_by_type,
        skipped_counts_by_reason=skipped_counts_by_reason,
        wire_layer_entity_type_counts=wire_layer_entity_type_counts,
        raw_candidate_wire_count=len(route_candidates),
        pad_filtered_wire_count=len(route_candidates) - len(filtered_candidates),
        pre_merge_wire_path_count=len(filtered_candidates),
        final_wire_paths=final_wire_paths,
    )
    return wires, audit


def _resolve_wire_layers(layer_info: list[LayerInfo]) -> set[str]:
    wire_layers: set[str] = set()
    for layer in layer_info:
        role_name = layer.get("mapped_type") or layer.get("suggested_role")
        if role_name == "wire":
            wire_layers.add(str(layer["name"]))
    return wire_layers


def _collect_wire_layer_entity_type_counts(
    raw_entities: list[RawEntity],
    layer_info: list[LayerInfo],
    wire_layers: set[str],
) -> dict[str, int]:
    counts = {entity_type: 0 for entity_type in _WIRE_LAYER_ENTITY_TYPES}
    for layer in layer_info:
        if str(layer["name"]) not in wire_layers:
            continue
        for entity_type in _WIRE_LAYER_ENTITY_TYPES:
            counts[entity_type] += int(layer.get("entity_types", {}).get(entity_type, 0))
    if any(counts.values()):
        return counts

    for entity in raw_entities:
        layer_name = _entity_layer_name(entity)
        if layer_name not in wire_layers:
            continue
        entity_type = _entity_type_name(entity)
        if entity_type in counts:
            counts[entity_type] += 1
    return counts


def _collect_wire_route_candidates(
    entity_index: int,
    entity: Any,
    *,
    fallback_layer_name: str,
    pad_outline_bboxes: list[_PadBBox],
    skipped_entities: list[WireExtractionSkippedEntity],
    skipped_counts_by_reason: dict[str, int],
) -> list[_WireRouteCandidate]:
    entity_type = _entity_type_name(entity)
    layer_name = _entity_layer_name(entity) or fallback_layer_name
    if layer_name == "0":
        layer_name = fallback_layer_name

    if entity_type == "INSERT":
        child_entities = tuple(_iter_insert_children(entity))
        if not child_entities:
            _append_skipped_entity(
                skipped_entities,
                skipped_counts_by_reason,
                entity_index=entity_index,
                layer_name=layer_name,
                entity_type=entity_type,
                reason="unsupported_entity_type",
            )
            return []
        routes: list[_WireRouteCandidate] = []
        for child_entity in child_entities:
            routes.extend(
                _collect_wire_route_candidates(
                    entity_index,
                    child_entity,
                    fallback_layer_name=layer_name,
                    pad_outline_bboxes=pad_outline_bboxes,
                    skipped_entities=skipped_entities,
                    skipped_counts_by_reason=skipped_counts_by_reason,
                )
            )
        return routes

    skip_reason, points = _extract_entity_route_points(entity)
    if skip_reason is not None or points is None or len(points) < 2:
        if skip_reason == "pad_outline":
            pad_points = _extract_polyline_points(entity)
            if _looks_like_small_pad_rect(pad_points):
                pad_outline_bboxes.append(
                    _PadBBox(*_route_bbox(_dedupe_closing_point(pad_points)))
                )
        _append_skipped_entity(
            skipped_entities,
            skipped_counts_by_reason,
            entity_index=entity_index,
            layer_name=layer_name,
            entity_type=entity_type,
            reason=skip_reason or "zero_length_or_insufficient_points",
        )
        return []

    route_points = tuple((float(x_value), float(y_value)) for x_value, y_value in points)
    if len(route_points) < 2 or route_points[0] == route_points[-1]:
        _append_skipped_entity(
            skipped_entities,
            skipped_counts_by_reason,
            entity_index=entity_index,
            layer_name=layer_name,
            entity_type=entity_type,
            reason="zero_length_or_insufficient_points",
        )
        return []

    return [
        _WireRouteCandidate(
            source_entity_indices=(entity_index,),
            layer_name=layer_name,
            source_type=entity_type,
            points=route_points,
        )
    ]


def _append_skipped_entity(
    skipped_entities: list[WireExtractionSkippedEntity],
    skipped_counts_by_reason: dict[str, int],
    *,
    entity_index: int,
    layer_name: str,
    entity_type: str,
    reason: str,
) -> None:
    skipped_entities.append(
        WireExtractionSkippedEntity(
            entity_index=entity_index,
            layer_name=layer_name,
            entity_type=entity_type,
            reason=reason,
        )
    )
    skipped_counts_by_reason[reason] = skipped_counts_by_reason.get(reason, 0) + 1


def _extract_entity_route_points(entity: Any) -> tuple[str | None, tuple[Point2D, ...] | None]:
    entity_type = _entity_type_name(entity)
    if entity_type == "LINE":
        return None, _extract_line_points(entity)
    if entity_type == "ARC":
        arc_points = _extract_arc_points(entity)
        if len(arc_points) < 2:
            return "zero_length_or_insufficient_points", None
        return None, arc_points
    if entity_type in {"LWPOLYLINE", "POLYLINE"}:
        polyline_points = _extract_polyline_points(entity)
        if _entity_closed(entity):
            if _looks_like_small_pad_rect(polyline_points):
                return "pad_outline", None
            return "closed_lwpolyline", None
        return None, polyline_points
    return "unsupported_entity_type", None


def _entity_type_name(entity: Any) -> str:
    if isinstance(entity, Mapping):
        return str(entity.get("type", "UNKNOWN"))
    if hasattr(entity, "dxftype"):
        return str(entity.dxftype())
    return str(type(entity).__name__)


def _entity_layer_name(entity: Any) -> str:
    if isinstance(entity, Mapping):
        return str(entity.get("layer", "0"))
    dxf_attribs = getattr(entity, "dxf", None)
    return str(getattr(dxf_attribs, "layer", "0"))


def _entity_closed(entity: Any) -> bool:
    if isinstance(entity, Mapping):
        return bool(entity.get("closed"))
    return bool(getattr(entity, "closed", False))


def _iter_insert_children(entity: Any) -> Iterable[Any]:
    if isinstance(entity, Mapping):
        return tuple(entity.get("entities", []))
    if hasattr(entity, "virtual_entities"):
        return tuple(entity.virtual_entities())
    return ()


def _extract_line_points(entity: Any) -> tuple[Point2D, ...]:
    if isinstance(entity, Mapping):
        start = entity["start"]
        end = entity["end"]
        return ((float(start[0]), float(start[1])), (float(end[0]), float(end[1])))
    start = entity.dxf.start
    end = entity.dxf.end
    return ((float(start.x), float(start.y)), (float(end.x), float(end.y)))


def _extract_arc_points(entity: Any) -> tuple[Point2D, ...]:
    if isinstance(entity, Mapping):
        return tuple((float(x_value), float(y_value)) for x_value, y_value in entity.get("points", []))
    return tuple(
        sample_arc_points(
            float(entity.dxf.center.x),
            float(entity.dxf.center.y),
            float(entity.dxf.radius),
            float(entity.dxf.start_angle),
            float(entity.dxf.end_angle),
        )
    )


def _extract_polyline_points(entity: Any) -> tuple[Point2D, ...]:
    if isinstance(entity, Mapping):
        return tuple((float(x_value), float(y_value)) for x_value, y_value in entity.get("points", []))
    if _entity_type_name(entity) == "LWPOLYLINE":
        return tuple((float(x_value), float(y_value)) for x_value, y_value in expand_lwpolyline_points(entity))
    vertices = getattr(entity, "vertices", None)
    if vertices is not None:
        return tuple(
            (float(vertex.dxf.location.x), float(vertex.dxf.location.y))
            for vertex in vertices
        )
    if hasattr(entity, "points"):
        return tuple((float(point[0]), float(point[1])) for point in entity.points())
    return ()


def _collect_pad_bboxes(
    route_candidates: list[_WireRouteCandidate],
    pad_outline_bboxes: list[_PadBBox],
    *,
    tolerance: float,
) -> tuple[_PadBBox, ...]:
    pad_bboxes: list[_PadBBox] = list(pad_outline_bboxes)
    axis_aligned_short_routes: list[_WireRouteCandidate] = []
    for route in route_candidates:
        if _looks_like_small_pad_rect(route.points):
            pad_bboxes.append(_PadBBox(*_route_bbox(_dedupe_closing_point(route.points))))
        if (
            len(route.points) == 2
            and route.length <= _PAD_MAX_SIDE
            and _is_axis_aligned_segment(route.start_point, route.end_point, tolerance=tolerance)
        ):
            axis_aligned_short_routes.append(route)
    pad_bboxes.extend(_find_small_rectangles_from_edges(axis_aligned_short_routes, tolerance=tolerance))
    return tuple(_dedupe_pad_bboxes(pad_bboxes, tolerance=tolerance))


def _filter_pad_symbol_routes(
    route_candidates: list[_WireRouteCandidate],
    pad_bboxes: tuple[_PadBBox, ...],
    *,
    tolerance: float,
    skipped_entities: list[WireExtractionSkippedEntity],
    skipped_counts_by_reason: dict[str, int],
) -> list[_WireRouteCandidate]:
    filtered_routes: list[_WireRouteCandidate] = []
    for route in route_candidates:
        skip_reason = _pad_symbol_filter_reason(route, pad_bboxes, tolerance=tolerance)
        if skip_reason is None:
            filtered_routes.append(route)
            continue
        _append_skipped_entity(
            skipped_entities,
            skipped_counts_by_reason,
            entity_index=route.source_entity_indices[0],
            layer_name=route.layer_name,
            entity_type=route.source_type,
            reason=skip_reason,
        )
    return filtered_routes


def _pad_symbol_filter_reason(
    route: _WireRouteCandidate,
    pad_bboxes: tuple[_PadBBox, ...],
    *,
    tolerance: float,
) -> str | None:
    if _looks_like_small_pad_rect(route.points):
        return "pad_outline"
    if route.length > _PAD_FILTER_MAX_LENGTH:
        return None
    if _route_inside_one_pad_bbox(route.points, pad_bboxes, tolerance=tolerance):
        return "pad_internal_short_line"
    if len(route.points) == 2 and route.length <= _PAD_DIAGONAL_MAX_LENGTH and _is_short_pad_diagonal(
        route.start_point,
        route.end_point,
    ):
        return "pad_diagonal_short_line"
    return None


def _route_inside_one_pad_bbox(
    points: tuple[Point2D, ...],
    pad_bboxes: tuple[_PadBBox, ...],
    *,
    tolerance: float,
) -> bool:
    return any(bbox.contains_all_points(points, tolerance=tolerance) for bbox in pad_bboxes)


def _looks_like_small_pad_rect(points: tuple[Point2D, ...]) -> bool:
    rect_points = tuple(dict.fromkeys(_dedupe_closing_point(points)))
    if len(rect_points) != 4:
        return False
    min_x, min_y, max_x, max_y = _route_bbox(rect_points)
    width = max_x - min_x
    height = max_y - min_y
    if width <= 0.0 or height <= 0.0:
        return False
    if max(width, height) > _PAD_MAX_SIDE or width * height > _PAD_MAX_AREA:
        return False
    return _looks_like_small_rotated_rect(rect_points)


def _looks_like_small_rotated_rect(points: tuple[Point2D, ...]) -> bool:
    if len(points) != 4:
        return False
    center_x = sum(point[0] for point in points) / 4.0
    center_y = sum(point[1] for point in points) / 4.0
    ordered_points = tuple(
        sorted(
            points,
            key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x),
        )
    )
    closed_points = ordered_points + (ordered_points[0],)
    vectors = [
        (
            end_point[0] - start_point[0],
            end_point[1] - start_point[1],
        )
        for start_point, end_point in zip(closed_points, closed_points[1:])
    ]
    lengths = [math.hypot(delta_x, delta_y) for delta_x, delta_y in vectors]
    if any(length <= 1e-9 or length > _PAD_MAX_SIDE for length in lengths):
        return False
    if not _lengths_close(lengths[0], lengths[2]) or not _lengths_close(lengths[1], lengths[3]):
        return False
    for index in range(4):
        first_vector = vectors[index]
        second_vector = vectors[(index + 1) % 4]
        if not _vectors_nearly_perpendicular(first_vector, second_vector):
            return False
    return _polygon_area(ordered_points) <= _PAD_MAX_AREA


def _lengths_close(first_length: float, second_length: float) -> bool:
    scale = max(first_length, second_length, 1.0)
    return abs(first_length - second_length) <= scale * 0.15


def _vectors_nearly_perpendicular(
    first_vector: Point2D,
    second_vector: Point2D,
) -> bool:
    first_length = math.hypot(first_vector[0], first_vector[1])
    second_length = math.hypot(second_vector[0], second_vector[1])
    if first_length <= 1e-9 or second_length <= 1e-9:
        return False
    cosine = abs(
        (
            first_vector[0] * second_vector[0]
            + first_vector[1] * second_vector[1]
        )
        / (first_length * second_length)
    )
    return cosine <= 0.25


def _polygon_area(points: tuple[Point2D, ...]) -> float:
    area = 0.0
    closed_points = points + (points[0],)
    for start_point, end_point in zip(closed_points, closed_points[1:]):
        area += start_point[0] * end_point[1] - end_point[0] * start_point[1]
    return abs(area) / 2.0


def _find_small_rectangles_from_edges(
    axis_aligned_short_routes: list[_WireRouteCandidate],
    *,
    tolerance: float,
) -> tuple[_PadBBox, ...]:
    if not axis_aligned_short_routes:
        return ()

    node_routes: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    route_nodes: list[tuple[tuple[str, int, int], tuple[str, int, int]]] = []
    for route_index, route in enumerate(axis_aligned_short_routes):
        first_node = _endpoint_key(route.layer_name, route.start_point, tolerance=tolerance)
        second_node = _endpoint_key(route.layer_name, route.end_point, tolerance=tolerance)
        route_nodes.append((first_node, second_node))
        node_routes[first_node].append(route_index)
        node_routes[second_node].append(route_index)

    visited_routes: set[int] = set()
    pad_bboxes: list[_PadBBox] = []
    for route_index in range(len(axis_aligned_short_routes)):
        if route_index in visited_routes:
            continue
        component_routes, component_nodes = _collect_route_component(
            route_index,
            route_nodes,
            node_routes,
            visited_routes,
        )
        if len(component_nodes) != 4:
            continue
        unique_edges = {
            tuple(sorted(route_nodes[candidate_index]))
            for candidate_index in component_routes
            if route_nodes[candidate_index][0] != route_nodes[candidate_index][1]
        }
        if len(unique_edges) != 4:
            continue
        node_edge_count: dict[tuple[str, int, int], int] = {}
        for first_node, second_node in unique_edges:
            node_edge_count[first_node] = node_edge_count.get(first_node, 0) + 1
            node_edge_count[second_node] = node_edge_count.get(second_node, 0) + 1
        if any(node_edge_count.get(node, 0) != 2 for node in component_nodes):
            continue
        component_points = tuple(
            point
            for candidate_index in component_routes
            for point in (
                axis_aligned_short_routes[candidate_index].start_point,
                axis_aligned_short_routes[candidate_index].end_point,
            )
        )
        bbox = _PadBBox(*_route_bbox(component_points))
        width = bbox.max_x - bbox.min_x
        height = bbox.max_y - bbox.min_y
        if width <= 0.0 or height <= 0.0:
            continue
        if max(width, height) > _PAD_MAX_SIDE or width * height > _PAD_MAX_AREA:
            continue
        pad_bboxes.append(bbox)
    return tuple(pad_bboxes)


def _collect_route_component(
    start_route_index: int,
    route_nodes: list[tuple[tuple[str, int, int], tuple[str, int, int]]],
    node_routes: dict[tuple[str, int, int], list[int]],
    visited_routes: set[int],
) -> tuple[set[int], set[tuple[str, int, int]]]:
    stack = [start_route_index]
    component_routes: set[int] = set()
    component_nodes: set[tuple[str, int, int]] = set()
    while stack:
        route_index = stack.pop()
        if route_index in visited_routes:
            continue
        visited_routes.add(route_index)
        component_routes.add(route_index)
        for node in route_nodes[route_index]:
            component_nodes.add(node)
            stack.extend(node_routes[node])
    return component_routes, component_nodes


def _dedupe_pad_bboxes(
    pad_bboxes: list[_PadBBox],
    *,
    tolerance: float,
) -> list[_PadBBox]:
    deduped: dict[tuple[int, int, int, int], _PadBBox] = {}
    for bbox in pad_bboxes:
        key = (
            int(round(bbox.min_x / tolerance)),
            int(round(bbox.min_y / tolerance)),
            int(round(bbox.max_x / tolerance)),
            int(round(bbox.max_y / tolerance)),
        )
        deduped[key] = bbox
    return list(deduped.values())


def _is_axis_aligned_segment(
    first_point: Point2D,
    second_point: Point2D,
    *,
    tolerance: float,
) -> bool:
    return (
        abs(first_point[0] - second_point[0]) <= tolerance
        or abs(first_point[1] - second_point[1]) <= tolerance
    )


def _is_short_pad_diagonal(first_point: Point2D, second_point: Point2D) -> bool:
    delta_x = second_point[0] - first_point[0]
    delta_y = second_point[1] - first_point[1]
    if delta_x == 0.0 or delta_y == 0.0:
        return False
    angle = abs(math.degrees(math.atan2(delta_y, delta_x))) % 180.0
    return (
        abs(angle - 45.0) <= _PAD_DIAGONAL_ANGLE_TOLERANCE_DEG
        or abs(angle - 135.0) <= _PAD_DIAGONAL_ANGLE_TOLERANCE_DEG
    )


def _merge_connected_route_candidates(
    route_candidates: list[_WireRouteCandidate],
    *,
    tolerance: float,
) -> list[_WireRouteCandidate]:
    if not route_candidates:
        return []

    node_routes: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    route_nodes: list[tuple[tuple[str, int, int], tuple[str, int, int]]] = []
    for route_index, route in enumerate(route_candidates):
        first_node = _endpoint_key(route.layer_name, route.start_point, tolerance=tolerance)
        second_node = _endpoint_key(route.layer_name, route.end_point, tolerance=tolerance)
        route_nodes.append((first_node, second_node))
        node_routes[first_node].append(route_index)
        node_routes[second_node].append(route_index)

    merged_routes: list[_WireRouteCandidate] = []
    visited_routes: set[int] = set()
    for route_index in sorted(
        range(len(route_candidates)),
        key=lambda index: (
            min(route_candidates[index].source_entity_indices),
            route_candidates[index].start_point,
            route_candidates[index].end_point,
        ),
    ):
        if route_index in visited_routes:
            continue
        start_node = _route_chain_start_node(route_index, route_nodes, node_routes)
        merged_routes.append(
            _trace_merged_route(
                route_index,
                start_node,
                route_candidates,
                route_nodes,
                node_routes,
                visited_routes,
            )
        )
    return merged_routes


def _route_chain_start_node(
    route_index: int,
    route_nodes: list[tuple[tuple[str, int, int], tuple[str, int, int]]],
    node_routes: dict[tuple[str, int, int], list[int]],
) -> tuple[str, int, int]:
    first_node, second_node = route_nodes[route_index]
    if len(node_routes[first_node]) != 2:
        return first_node
    if len(node_routes[second_node]) != 2:
        return second_node
    return first_node


def _trace_merged_route(
    start_route_index: int,
    start_node: tuple[str, int, int],
    route_candidates: list[_WireRouteCandidate],
    route_nodes: list[tuple[tuple[str, int, int], tuple[str, int, int]]],
    node_routes: dict[tuple[str, int, int], list[int]],
    visited_routes: set[int],
) -> _WireRouteCandidate:
    route_index = start_route_index
    current_node = start_node
    merged_points: list[Point2D] = []
    source_indices: list[int] = []
    source_types: list[str] = []
    layer_name = route_candidates[start_route_index].layer_name

    while True:
        route = route_candidates[route_index]
        first_node, second_node = route_nodes[route_index]
        oriented_points = (
            list(route.points)
            if current_node == first_node
            else list(reversed(route.points))
        )
        if merged_points:
            merged_points.extend(oriented_points[1:])
        else:
            merged_points.extend(oriented_points)
        source_indices.extend(route.source_entity_indices)
        source_types.append(route.source_type)
        visited_routes.add(route_index)

        next_node = second_node if current_node == first_node else first_node
        next_route_index = _next_merge_route_index(route_index, next_node, route_nodes, node_routes, visited_routes)
        if next_route_index is None:
            break
        route_index = next_route_index
        current_node = next_node

    source_type = source_types[0] if len(set(source_types)) == 1 else "MERGED_PATH"
    return _WireRouteCandidate(
        source_entity_indices=tuple(dict.fromkeys(source_indices)),
        layer_name=layer_name,
        source_type=source_type,
        points=tuple(_dedupe_neighbor_points(merged_points)),
    )


def _next_merge_route_index(
    current_route_index: int,
    shared_node: tuple[str, int, int],
    route_nodes: list[tuple[tuple[str, int, int], tuple[str, int, int]]],
    node_routes: dict[tuple[str, int, int], list[int]],
    visited_routes: set[int],
) -> int | None:
    if len(node_routes[shared_node]) != 2:
        return None
    route_ids = [
        route_index
        for route_index in node_routes[shared_node]
        if route_index != current_route_index and route_index not in visited_routes
    ]
    if len(route_ids) != 1:
        return None
    return route_ids[0]


def _find_merge_candidates_for_routes(
    route_candidates: list[_WireRouteCandidate],
    *,
    merge_tolerance: float,
) -> tuple[WireExtractionMergeCandidate, ...]:
    temporary_wires = [
        _build_wire_geometry_from_route(route_index + 1, route)
        for route_index, route in enumerate(route_candidates)
    ]
    return _find_merge_candidates(temporary_wires, merge_tolerance=merge_tolerance)


def _endpoint_key(
    layer_name: str,
    point: Point2D,
    *,
    tolerance: float,
) -> tuple[str, int, int]:
    return (
        layer_name,
        int(round(point[0] / tolerance)),
        int(round(point[1] / tolerance)),
    )


def _build_wire_geometry_from_route(
    wire_number: int,
    route: _WireRouteCandidate,
) -> WireGeometry | None:
    if len(route.points) < 2 or route.points[0] == route.points[-1]:
        return None
    first_point_xy = route.start_point
    second_point_xy = route.end_point
    wire_id = f"W{wire_number:04d}"
    return WireGeometry(
        wire_id=wire_id,
        layer_name=route.layer_name,
        source_type=route.source_type,
        source_entity_indices=route.source_entity_indices,
        route_points=route.points,
        first_point=WirePoint(
            point_id=f"{wire_id}-P1",
            wire_id=wire_id,
            role="first",
            x=first_point_xy[0],
            y=first_point_xy[1],
            source_entity_index=min(route.source_entity_indices),
        ),
        second_point=WirePoint(
            point_id=f"{wire_id}-P2",
            wire_id=wire_id,
            role="second",
            x=second_point_xy[0],
            y=second_point_xy[1],
            source_entity_index=max(route.source_entity_indices),
        ),
        length=_polyline_length(route.points),
        angle_deg=_wire_angle(first_point_xy, second_point_xy),
        bbox=_route_bbox(route.points),
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


def _dedupe_closing_point(points: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
    if len(points) >= 2 and points[0] == points[-1]:
        return points[:-1]
    return points


def _dedupe_neighbor_points(points: list[Point2D]) -> list[Point2D]:
    deduped: list[Point2D] = []
    for point in points:
        if deduped and point == deduped[-1]:
            continue
        deduped.append(point)
    return deduped


def _count_candidate_types(route_candidates: list[_WireRouteCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for route in route_candidates:
        counts[route.source_type] = counts.get(route.source_type, 0) + 1
    return counts


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


def format_wire_extraction_audit_report(audit: WireExtractionAudit) -> str:
    """Render a deterministic text report for reviewing wire extraction quality."""

    lines = [
        "Wire Extraction Audit",
        f"Wire layers: {', '.join(audit.wire_layers) if audit.wire_layers else '(none)'}",
        "06_wire entity stats:",
    ]
    for entity_type in _WIRE_LAYER_ENTITY_TYPES:
        lines.append(f"- {entity_type}: {audit.wire_layer_entity_type_counts.get(entity_type, 0)}")

    lines.extend(
        [
            "",
            f"Top-level candidate entities: {audit.candidate_entity_count}",
            f"Raw candidate wire paths: {audit.raw_candidate_wire_count}",
            f"Pad-symbol filtered paths: {audit.pad_filtered_wire_count}",
            f"Merged wire paths: {audit.pre_merge_wire_path_count} -> {audit.extracted_wire_count}",
        ]
    )
    lines.extend(
        [
        "",
        "Extracted entity types:",
        ]
    )
    if audit.extracted_counts_by_type:
        for entity_type, count in sorted(audit.extracted_counts_by_type.items()):
            lines.append(f"- {entity_type}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "Skipped entities:"])
    if audit.skipped_entities:
        for reason, count in sorted(audit.skipped_counts_by_reason.items()):
            lines.append(f"- {reason}: {count}")
        for item in audit.skipped_entities:
            lines.append(
                f"  - #{item.entity_index} layer={item.layer_name} "
                f"type={item.entity_type} reason={item.reason}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "Potential split-wire joins before merge:"])
    if audit.merge_candidates:
        for item in sorted(
            audit.merge_candidates,
            key=lambda candidate: (
                candidate.endpoint_alignment != "same_role_conflict",
                candidate.first_wire_id,
                candidate.second_wire_id,
                candidate.shared_x,
                candidate.shared_y,
            ),
        ):
            lines.append(
                f"- {item.first_wire_id}({item.first_endpoint_role}) <-> "
                f"{item.second_wire_id}({item.second_endpoint_role}) "
                f"@ ({item.shared_x:.6f}, {item.shared_y:.6f}) "
                f"[{item.endpoint_alignment}]"
            )
    else:
        lines.append("- none")

    lines.extend(["", "Suggested merge actions:"])
    proposals = build_wire_merge_proposals(audit)
    if proposals:
        for proposal in proposals:
            reverse_text = (
                "none"
                if not proposal.reverse_wire_ids
                else ", ".join(proposal.reverse_wire_ids)
            )
            lines.append(
                f"- {proposal.source_wire_id} -> {proposal.target_wire_id} "
                f"@ ({proposal.shared_x:.6f}, {proposal.shared_y:.6f}) "
                f"action={proposal.action} reverse={reverse_text}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "Final wire paths:"])
    if audit.final_wire_paths:
        for item in audit.final_wire_paths:
            lines.append(
                f"- {item.wire_id}: length={item.length:.6f} "
                f"start=({item.start_x:.6f}, {item.start_y:.6f}) "
                f"end=({item.end_x:.6f}, {item.end_y:.6f}) "
                f"bend_count={item.bend_count}"
            )
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def write_wire_extraction_audit_report(
    audit: WireExtractionAudit,
    output_path: str | Path,
) -> Path:
    """Write one wire extraction audit report and return the resolved path."""

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_wire_extraction_audit_report(audit), encoding="utf-8")
    return target_path


def build_wire_merge_proposals(
    audit: WireExtractionAudit,
) -> tuple[WireExtractionMergeProposal, ...]:
    """Build deterministic pairwise merge suggestions without changing wire data."""

    proposals: list[WireExtractionMergeProposal] = []
    for candidate in sorted(
        audit.merge_candidates,
        key=lambda item: (
            item.endpoint_alignment != "same_role_conflict",
            item.first_wire_id,
            item.second_wire_id,
            item.shared_x,
            item.shared_y,
        ),
    ):
        proposals.append(_build_merge_proposal(candidate))
    return tuple(proposals)


def _merge_endpoint_alignment(
    first_role: str,
    second_role: str,
) -> WireMergeEndpointAlignment:
    if first_role == second_role:
        return "same_role_conflict"
    return "continuous"


def _build_merge_proposal(
    candidate: WireExtractionMergeCandidate,
) -> WireExtractionMergeProposal:
    if candidate.first_endpoint_role == "second" and candidate.second_endpoint_role == "first":
        return WireExtractionMergeProposal(
            source_wire_id=candidate.first_wire_id,
            target_wire_id=candidate.second_wire_id,
            shared_x=candidate.shared_x,
            shared_y=candidate.shared_y,
            action="join_as_is",
            reverse_wire_ids=(),
            source_endpoint_role=candidate.first_endpoint_role,
            target_endpoint_role=candidate.second_endpoint_role,
        )
    if candidate.first_endpoint_role == "first" and candidate.second_endpoint_role == "second":
        return WireExtractionMergeProposal(
            source_wire_id=candidate.second_wire_id,
            target_wire_id=candidate.first_wire_id,
            shared_x=candidate.shared_x,
            shared_y=candidate.shared_y,
            action="join_as_is",
            reverse_wire_ids=(),
            source_endpoint_role=candidate.second_endpoint_role,
            target_endpoint_role=candidate.first_endpoint_role,
        )
    if candidate.first_endpoint_role == "first" and candidate.second_endpoint_role == "first":
        return WireExtractionMergeProposal(
            source_wire_id=candidate.first_wire_id,
            target_wire_id=candidate.second_wire_id,
            shared_x=candidate.shared_x,
            shared_y=candidate.shared_y,
            action="reverse_first_then_join",
            reverse_wire_ids=(candidate.first_wire_id,),
            source_endpoint_role=candidate.first_endpoint_role,
            target_endpoint_role=candidate.second_endpoint_role,
        )
    return WireExtractionMergeProposal(
        source_wire_id=candidate.first_wire_id,
        target_wire_id=candidate.second_wire_id,
        shared_x=candidate.shared_x,
        shared_y=candidate.shared_y,
        action="reverse_second_then_join",
        reverse_wire_ids=(candidate.second_wire_id,),
        source_endpoint_role=candidate.first_endpoint_role,
        target_endpoint_role=candidate.second_endpoint_role,
    )


__all__ = [
    "WireExtractionAudit",
    "WireExtractionMergeCandidate",
    "WireExtractionMergeProposal",
    "WireExtractionPathSummary",
    "WireExtractionSkippedEntity",
    "WireMergeAction",
    "WireMergeEndpointAlignment",
    "build_wire_merge_proposals",
    "extract_wire_geometries",
    "extract_wire_geometries_with_audit",
    "format_wire_extraction_audit_report",
    "write_wire_extraction_audit_report",
]
