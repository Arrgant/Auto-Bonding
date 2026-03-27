"""Preview-oriented entity helpers for 2D DXF visualization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .layer_stack import build_layer_order_map
from .raw_dxf_types import LayerInfo, Point2D, RawEntity


@dataclass(frozen=True)
class PreviewEntity:
    """One display-ready preview entity, optionally merged from multiple sources."""

    entity_index: int
    entity: RawEntity
    source_indices: tuple[int, ...]


def _rounded_point(point: Point2D, precision: int = 4) -> tuple[float, float]:
    return round(float(point[0]), precision), round(float(point[1]), precision)


def _line_direction(start: Point2D, end: Point2D) -> tuple[float, float]:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 1e-9:
        return 0.0, 0.0
    return dx / length, dy / length


def _same_direction(first: tuple[float, float], second: tuple[float, float], tolerance: float = 1e-4) -> bool:
    dot = abs(first[0] * second[0] + first[1] * second[1])
    return abs(1.0 - dot) <= tolerance


def _other_endpoint(entity: RawEntity, point: Point2D) -> Point2D:
    start = entity["start"]
    end = entity["end"]
    if _rounded_point(start) == _rounded_point(point):
        return end
    return start


def _merge_line_group(group: list[tuple[int, RawEntity]]) -> list[PreviewEntity]:
    if len(group) <= 1:
        return [PreviewEntity(entity_index=index, entity=entity, source_indices=(index,)) for index, entity in group]

    endpoint_map: dict[tuple[float, float], set[int]] = {}
    line_records = {index: entity for index, entity in group}
    directions = {index: _line_direction(entity["start"], entity["end"]) for index, entity in group}

    for index, entity in group:
        endpoint_map.setdefault(_rounded_point(entity["start"]), set()).add(index)
        endpoint_map.setdefault(_rounded_point(entity["end"]), set()).add(index)

    visited: set[int] = set()
    merged_entities: list[PreviewEntity] = []

    for index, entity in group:
        if index in visited:
            continue

        direction = directions[index]
        if direction == (0.0, 0.0):
            visited.add(index)
            merged_entities.append(PreviewEntity(entity_index=index, entity=entity, source_indices=(index,)))
            continue

        chain_indices = {index}
        endpoints = [entity["start"], entity["end"]]
        visited.add(index)

        changed = True
        while changed:
            changed = False
            for edge_point in list(endpoints):
                candidates = endpoint_map.get(_rounded_point(edge_point), set())
                for candidate_index in list(candidates):
                    if candidate_index in chain_indices:
                        continue
                    candidate = line_records[candidate_index]
                    candidate_direction = directions[candidate_index]
                    if not _same_direction(direction, candidate_direction):
                        continue

                    chain_indices.add(candidate_index)
                    visited.add(candidate_index)
                    endpoints.append(_other_endpoint(candidate, edge_point))
                    changed = True

        chain_points = endpoints
        dominant_axis = 0 if abs(direction[0]) >= abs(direction[1]) else 1
        start_point = min(chain_points, key=lambda point: (point[dominant_axis], point[1 - dominant_axis]))
        end_point = max(chain_points, key=lambda point: (point[dominant_axis], point[1 - dominant_axis]))

        merged_entities.append(
            PreviewEntity(
                entity_index=min(chain_indices),
                entity={
                    "type": "LINE",
                    "start": start_point,
                    "end": end_point,
                    "layer": entity["layer"],
                },
                source_indices=tuple(sorted(chain_indices)),
            )
        )

    return merged_entities


def _group_lines_by_layer(indexed_entities: Iterable[tuple[int, RawEntity]]) -> tuple[dict[str, list[tuple[int, RawEntity]]], list[PreviewEntity]]:
    line_groups: dict[str, list[tuple[int, RawEntity]]] = {}
    passthrough: list[PreviewEntity] = []

    for index, entity in indexed_entities:
        if entity["type"] == "LINE":
            line_groups.setdefault(str(entity.get("layer", "0")), []).append((index, entity))
        else:
            passthrough.append(PreviewEntity(entity_index=index, entity=entity, source_indices=(index,)))

    return line_groups, passthrough


def build_preview_entities(raw_entities: list[RawEntity], layer_info: list[LayerInfo]) -> list[PreviewEntity]:
    """Build preview entities ordered by layer, with connected lines merged for display."""

    layer_order = build_layer_order_map(layer_info, raw_entities)
    indexed_entities = list(enumerate(raw_entities))
    line_groups, passthrough = _group_lines_by_layer(indexed_entities)

    merged: list[PreviewEntity] = []
    for layer_name, group in line_groups.items():
        merged.extend(_merge_line_group(group))

    preview_entities = passthrough + merged
    preview_entities.sort(
        key=lambda item: (
            layer_order.get(str(item.entity.get("layer", "0")), 10**9),
            item.entity_index,
        )
    )
    return preview_entities


__all__ = ["PreviewEntity", "build_preview_entities"]
