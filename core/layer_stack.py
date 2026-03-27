"""Layer ordering and stacked preview helpers for DXF import workflows."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import cadquery as cq

from .raw_dxf_types import LayerInfo, RawEntity


def layer_sort_key(layer_name: str) -> tuple[int, str]:
    """Sort by leading numeric marker first, then by layer name."""

    match = re.match(r"\s*(\d+)", layer_name)
    if match:
        return int(match.group(1)), layer_name.upper()
    return 10**9, layer_name.upper()


def build_layer_order_map(layer_info: list[LayerInfo], raw_entities: list[RawEntity]) -> dict[str, int]:
    """Build a stable layer order map for display and stacking."""

    names = {str(layer["name"]) for layer in layer_info}
    names.update(str(entity.get("layer", "0")) for entity in raw_entities)
    ordered_names = sorted(names, key=layer_sort_key)
    return {name: index for index, name in enumerate(ordered_names)}


def sort_entities_by_layer(raw_entities: list[RawEntity], layer_order: dict[str, int]) -> list[tuple[int, RawEntity]]:
    """Return raw entities ordered by layer stack and source index."""

    indexed = list(enumerate(raw_entities))
    indexed.sort(key=lambda item: (layer_order.get(str(item[1].get("layer", "0")), 10**9), item[0]))
    return indexed


def _is_supported_closed_entity(entity: RawEntity) -> bool:
    entity_type = entity["type"]
    if entity_type == "CIRCLE":
        return True
    if entity_type == "LWPOLYLINE":
        return bool(entity.get("closed"))
    return False


def _build_entity_solid(entity: RawEntity, thickness: float, base_z: float) -> cq.Workplane | None:
    if thickness <= 0:
        return None

    entity_type = entity["type"]
    try:
        if entity_type == "CIRCLE":
            center_x, center_y = entity["center"]
            solid = cq.Workplane("XY").center(center_x, center_y).circle(entity["radius"]).extrude(thickness)
            return solid.translate((0.0, 0.0, base_z))

        if entity_type == "LWPOLYLINE" and entity.get("closed"):
            points = entity.get("points") or []
            if len(points) < 3:
                return None
            solid = cq.Workplane("XY").polyline(points).close().extrude(thickness)
            return solid.translate((0.0, 0.0, base_z))
    except Exception:
        return None

    return None


def build_stacked_preview_assembly(
    raw_entities: list[RawEntity],
    layer_info: list[LayerInfo],
    entity_thicknesses: dict[int, float],
) -> cq.Assembly | None:
    """Build a simple per-layer stacked preview assembly from selected closed entities."""

    positive_assignments = {index: float(thickness) for index, thickness in entity_thicknesses.items() if thickness > 0}
    if not positive_assignments:
        return None

    layer_order = build_layer_order_map(layer_info, raw_entities)
    entities_by_layer: dict[str, list[tuple[int, RawEntity, float]]] = defaultdict(list)

    for entity_index, thickness in positive_assignments.items():
        if entity_index < 0 or entity_index >= len(raw_entities):
            continue
        entity = raw_entities[entity_index]
        if not _is_supported_closed_entity(entity):
            continue
        layer_name = str(entity.get("layer", "0"))
        entities_by_layer[layer_name].append((entity_index, entity, thickness))

    if not entities_by_layer:
        return None

    assembly = cq.Assembly()
    current_z = 0.0

    ordered_layers = sorted(entities_by_layer, key=lambda name: layer_order.get(name, 10**9))
    for layer_name in ordered_layers:
        layer_entities = entities_by_layer[layer_name]
        layer_height = max(thickness for _, _, thickness in layer_entities)
        for entity_index, entity, thickness in layer_entities:
            solid = _build_entity_solid(entity, thickness, current_z)
            if solid is not None:
                assembly.add(solid, name=f"layer_{layer_order.get(layer_name, 0)}_entity_{entity_index}")
        current_z += layer_height

    return assembly if getattr(assembly, "objects", {}) else None


__all__ = [
    "build_layer_order_map",
    "build_stacked_preview_assembly",
    "layer_sort_key",
    "sort_entities_by_layer",
]
