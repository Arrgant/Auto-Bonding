"""Low-level DXF entity loading helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

from .export.coordinates import BondPoint
from .raw_dxf_helpers import build_layer_info, build_scene_rect, extract_raw_entity
from .raw_dxf_types import LayerInfo, RawEntity, SceneRect


def _update_bounds(bounds: dict[str, float] | None, x_value: float, y_value: float) -> dict[str, float]:
    if bounds is None:
        return {"min_x": x_value, "max_x": x_value, "min_y": y_value, "max_y": y_value}

    bounds["min_x"] = min(bounds["min_x"], x_value)
    bounds["max_x"] = max(bounds["max_x"], x_value)
    bounds["min_y"] = min(bounds["min_y"], y_value)
    bounds["max_y"] = max(bounds["max_y"], y_value)
    return bounds


def load_raw_dxf_entities(
    file_path: Path,
    layer_mapping: dict[str, str] | None = None,
) -> tuple[list[RawEntity], SceneRect, Counter, list[LayerInfo]]:
    document = ezdxf.readfile(str(file_path))
    modelspace = document.modelspace()
    normalized_mapping = {str(name).upper(): value for name, value in (layer_mapping or {}).items()}

    entities: list[RawEntity] = []
    counts: Counter = Counter()
    bounds: dict[str, float] | None = None
    layer_entity_counts: Counter = Counter()
    layer_type_counts: dict[str, Counter] = defaultdict(Counter)

    for entity in modelspace:
        entity_type = entity.dxftype()
        layer_name = str(entity.dxf.layer)
        counts[entity_type] += 1
        layer_entity_counts[layer_name] += 1
        layer_type_counts[layer_name][entity_type] += 1

        raw_entity, bound_points = extract_raw_entity(entity, entity_type, layer_name)
        if raw_entity is None:
            continue

        entities.append(raw_entity)
        for x_value, y_value in bound_points:
            bounds = _update_bounds(bounds, x_value, y_value)

    scene_rect = build_scene_rect(bounds)
    layer_info = build_layer_info(document, layer_entity_counts, layer_type_counts, normalized_mapping)
    return entities, scene_rect, counts, layer_info


def extract_coordinates_from_raw_entities(raw_entities: list[RawEntity]) -> list[BondPoint]:
    points: list[BondPoint] = []
    seen: set[tuple[float, float, float]] = set()

    def add_point(x_value: float, y_value: float, z_value: float = 0.0) -> None:
        key = (round(x_value, 4), round(y_value, 4), round(z_value, 4))
        if key in seen:
            return
        seen.add(key)
        points.append(BondPoint(x=x_value, y=y_value, z=z_value))

    for entity in raw_entities:
        entity_type = entity["type"]
        if entity_type == "LINE":
            add_point(entity["start"][0], entity["start"][1])
            add_point(entity["end"][0], entity["end"][1])
        elif entity_type in {"LWPOLYLINE", "ARC"}:
            for x_value, y_value in entity.get("points", []):
                add_point(x_value, y_value)
        elif entity_type == "POINT":
            add_point(entity["location"][0], entity["location"][1])
        elif entity_type == "CIRCLE":
            add_point(entity["center"][0], entity["center"][1])

    return points
