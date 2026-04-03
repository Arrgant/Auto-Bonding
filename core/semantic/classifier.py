"""Rule-based semantic classifier driven by the 6-layer rule table."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from ..hole_rules import classify_substrate_round_feature
from ..layer_semantics import mapped_type_to_semantic_role, suggest_layer_semantic_role
from ..raw_dxf_types import LayerInfo, Point2D, RawEntity
from .candidates import SemanticCandidate
from .confidence import bump_confidence
from .entities import SemanticEntity
from .fallback import finalize_candidates
from .layer_summary import LayerSemanticSummary, summarize_layers
from .relations import RelationNote, apply_cross_layer_relations


@dataclass(frozen=True)
class SemanticClassificationResult:
    """Complete semantic classification payload for one imported DXF file."""

    candidates: list[SemanticCandidate]
    entities: list[SemanticEntity]
    review: list[SemanticCandidate]
    relation_notes: list[RelationNote]

    @property
    def entity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entity in self.entities:
            counts[entity.kind] = counts.get(entity.kind, 0) + 1
        return counts

    @property
    def review_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for candidate in self.review:
            counts[candidate.kind] = counts.get(candidate.kind, 0) + 1
        return counts

    @property
    def layer_summaries(self) -> list[LayerSemanticSummary]:
        return summarize_layers(self.entities, self.review)


def classify_semantic_layers(
    raw_entities: list[RawEntity],
    layer_info: list[LayerInfo],
) -> SemanticClassificationResult:
    """Classify raw DXF entities into staged semantic candidates and entities."""

    layer_roles = _resolve_layer_roles(raw_entities, layer_info)
    candidates: list[SemanticCandidate] = []

    candidates.extend(_classify_substrate(raw_entities, layer_roles))
    candidates.extend(_classify_holes(raw_entities, layer_roles))
    candidates.extend(_classify_module_regions(raw_entities, layer_roles))
    candidates.extend(_classify_lead_frames(raw_entities, layer_roles))
    candidates.extend(_classify_pads(raw_entities, layer_roles))
    candidates.extend(_classify_die_regions(raw_entities, layer_roles))
    candidates.extend(_classify_wires(raw_entities, layer_roles))

    weighted_candidates, relation_notes = apply_cross_layer_relations(candidates)
    entities, review = finalize_candidates(weighted_candidates)
    return SemanticClassificationResult(weighted_candidates, entities, review, relation_notes)


def _resolve_layer_roles(raw_entities: list[RawEntity], layer_info: list[LayerInfo]) -> dict[str, str | None]:
    roles: dict[str, str | None] = {}
    for layer in layer_info:
        layer_name = str(layer["name"])
        roles[layer_name] = (
            layer.get("suggested_role")
            or mapped_type_to_semantic_role(layer.get("mapped_type"))
            or suggest_layer_semantic_role(layer_name)
        )
    for entity in raw_entities:
        layer_name = str(entity.get("layer", "0"))
        roles.setdefault(layer_name, suggest_layer_semantic_role(layer_name))
    return roles


def _classify_substrate(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    candidates: list[SemanticCandidate] = []
    closed = _closed_entities_for_role(raw_entities, layer_roles, "substrate")
    if not closed:
        return candidates

    ranked = sorted(closed, key=lambda item: _entity_area(item[1]), reverse=True)
    substrate_index, substrate_entity = ranked[0]
    substrate_bbox = _entity_bbox(substrate_entity)
    holes = _substrate_internal_rounds(raw_entities, layer_roles, substrate_index, substrate_bbox)
    confidence = bump_confidence(
        0.78,
        0.08 if not ranked[1:] or _entity_area(substrate_entity) > _entity_area(ranked[1][1]) * 1.1 else 0.0,
        0.06 if holes else 0.0,
    )
    candidates.append(
        SemanticCandidate(
            id=f"substrate_candidate_{substrate_index}",
            kind="substrate_candidate",
            layer_name=str(substrate_entity.get("layer", "0")),
            confidence=confidence,
            source_indices=(substrate_index,),
            geometry={
                "bbox": substrate_bbox,
                "area": _entity_area(substrate_entity),
                "holes": tuple(index for index, _ in holes),
            },
            properties={"hole_count": len(holes)},
        )
    )

    repeated_counts = _round_feature_repeat_counts(holes)
    concentric_counts = _concentric_round_counts(holes)

    for hole_order, (hole_index, hole_entity) in enumerate(holes, start=1):
        hole_bbox = _entity_bbox(hole_entity)
        hole_center = _entity_center(hole_entity)
        repeated_count = repeated_counts.get(hole_index, 1)
        concentric_count = concentric_counts.get(hole_index, 1)
        hole_kind, edge_contacts = classify_substrate_round_feature(
            hole_bbox,
            substrate_bbox,
            repeated_count=repeated_count,
            concentric_count=concentric_count,
        )
        rule_source = _substrate_round_rule_source(
            hole_kind,
            edge_contacts=edge_contacts,
            repeated_count=repeated_count,
            concentric_count=concentric_count,
            feature_bbox=hole_bbox,
            substrate_bbox=substrate_bbox,
        )
        if hole_kind in {"mounting", "tooling"}:
            hole_confidence = bump_confidence(0.86, 0.06, 0.02 if edge_contacts else 0.0)
            candidates.append(
                SemanticCandidate(
                    id=f"hole_candidate_{hole_order}_{hole_index}",
                    kind="hole_candidate",
                    layer_name=str(hole_entity.get("layer", "0")),
                    confidence=hole_confidence,
                    source_indices=(hole_index,),
                    geometry={"center": hole_center, "bbox": hole_bbox},
                    properties={
                        "parent": f"substrate_candidate_{substrate_index}",
                        "hole_kind": hole_kind,
                        "edge_contacts": edge_contacts,
                        "rule_source": rule_source,
                    },
                )
            )
            continue

        candidates.append(
            SemanticCandidate(
                id=f"round_feature_candidate_{hole_order}_{hole_index}",
                kind="round_feature_candidate",
                layer_name=str(hole_entity.get("layer", "0")),
                confidence=bump_confidence(0.84, 0.03 if edge_contacts else 0.0),
                source_indices=(hole_index,),
                geometry={"center": hole_center, "bbox": hole_bbox},
                properties={
                    "parent": f"substrate_candidate_{substrate_index}",
                    "feature_kind": "substrate_round",
                    "edge_contacts": edge_contacts,
                    "rule_source": rule_source,
                },
            )
        )

    return candidates


def _substrate_internal_rounds(
    raw_entities: list[RawEntity],
    layer_roles: dict[str, str | None],
    substrate_index: int,
    substrate_bbox: tuple[float, float, float, float],
) -> list[tuple[int, RawEntity]]:
    ignored_roles = {"pad", "die_region", "module_region", "wire", "hole", "bond_point"}
    rounds: list[tuple[int, RawEntity]] = []
    for index, entity in enumerate(raw_entities):
        if index == substrate_index:
            continue
        role = layer_roles.get(str(entity.get("layer", "0")))
        if role in ignored_roles:
            continue
        # Skip unsupported raw entities like HATCH/TEXT before asking for a bbox.
        if _round_entity_diameter(entity) is None:
            continue
        bbox = _optional_entity_bbox(entity)
        if bbox is None or not _bbox_inside(bbox, substrate_bbox):
            continue
        rounds.append((index, entity))
    return rounds


def _classify_holes(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    """Promote hole-like layers or circular contours into explicit hole semantics."""

    candidates: list[SemanticCandidate] = []
    for index, entity in _closed_entities_for_role(raw_entities, layer_roles, "hole"):
        diameter = _round_entity_diameter(entity)
        if diameter is not None:
            candidates.append(
                SemanticCandidate(
                    id=f"hole_candidate_layer_{index}",
                    kind="hole_candidate",
                    layer_name=str(entity.get("layer", "0")),
                    confidence=0.88,
                    source_indices=(index,),
                    geometry={"center": _entity_center(entity), "bbox": _entity_bbox(entity)},
                    properties={
                        "hole_kind": "layer_defined",
                        "edge_contacts": tuple(),
                        "hole_shape": "round",
                        "rule_source": "explicit_hole_layer_round",
                    },
                )
            )
            continue
        slot_profile = _slot_profile(entity)
        if slot_profile is None:
            continue
        candidates.append(
            SemanticCandidate(
                id=f"hole_candidate_layer_{index}",
                kind="hole_candidate",
                layer_name=str(entity.get("layer", "0")),
                confidence=0.78,
                source_indices=(index,),
                geometry={
                    "center": _entity_center(entity),
                    "bbox": _entity_bbox(entity),
                    "slot_size": slot_profile["size"],
                },
                properties={
                    "hole_kind": "layer_defined",
                    "edge_contacts": tuple(),
                    "hole_shape": "slot",
                    "slot_aspect_ratio": slot_profile["aspect_ratio"],
                    "rule_source": "explicit_hole_layer_slot",
                },
            )
        )
    return candidates


def _classify_module_regions(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    rectangles = [
        (index, entity)
        for index, entity in _closed_entities_for_role(raw_entities, layer_roles, "module_region")
        if _is_rectangle_like(entity)
    ]
    rectangles.sort(key=lambda item: _entity_area(item[1]), reverse=True)
    if not rectangles:
        return []

    selected = rectangles[:2]
    if len(selected) == 2:
        first_bbox = _entity_bbox(selected[0][1])
        second_bbox = _entity_bbox(selected[1][1])
        size_similarity = _bbox_size_similarity(first_bbox, second_bbox)
    else:
        size_similarity = 0.0

    candidates: list[SemanticCandidate] = []
    ordered = sorted(selected, key=lambda item: _entity_center(item[1])[0])
    for order, (index, entity) in enumerate(ordered):
        side = "left" if order == 0 else "right"
        confidence = bump_confidence(0.74, 0.12 if len(selected) == 2 else 0.0, 0.04 if size_similarity >= 0.8 else 0.0)
        candidates.append(
            SemanticCandidate(
                id=f"module_region_candidate_{index}",
                kind="module_region_candidate",
                layer_name=str(entity.get("layer", "0")),
                confidence=confidence,
                source_indices=(index,),
                geometry={"bbox": _entity_bbox(entity), "center": _entity_center(entity)},
                properties={"side": side},
            )
        )
    return candidates


def _classify_lead_frames(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    candidates: list[SemanticCandidate] = []
    for index, entity in _entities_for_role(raw_entities, layer_roles, "lead_frame"):
        bbox = _optional_entity_bbox(entity)
        if bbox is None:
            continue
        aspect = _bbox_aspect_ratio(bbox)
        if aspect < 2.5 and entity["type"] != "LINE":
            continue
        mode = "contour" if _is_closed(entity) else "path"
        confidence = bump_confidence(0.70, 0.12 if aspect >= 4.0 else 0.0, 0.06 if mode == "contour" else 0.0)
        candidates.append(
            SemanticCandidate(
                id=f"lead_frame_candidate_{index}",
                kind="lead_frame_candidate",
                layer_name=str(entity.get("layer", "0")),
                confidence=confidence,
                source_indices=(index,),
                geometry={"bbox": bbox, "center": _entity_center(entity), "aspect_ratio": aspect},
                properties={"mode": mode},
            )
        )
    return candidates


def _classify_pads(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    rectangles = [
        (index, entity)
        for index, entity in _closed_entities_for_role(raw_entities, layer_roles, "pad")
        if _is_rectangle_like(entity)
    ]
    if not rectangles:
        return []

    size_clusters = _cluster_rectangles_by_dimensions(rectangles)
    candidates: list[SemanticCandidate] = []
    for cluster_name, cluster_payload in size_clusters.items():
        cluster_members = cluster_payload["members"]
        cluster_size = len(cluster_members)
        repeated_bonus = min(0.02 * max(cluster_size - 1, 0), 0.12)
        signature = cluster_payload["signature"]
        for index, entity in cluster_members:
            bbox = _entity_bbox(entity)
            width, height = _bbox_size(bbox)
            aspect_ratio = _bbox_aspect_ratio(bbox)
            regularity_bonus = 0.04 if aspect_ratio <= 1.8 else 0.0
            candidates.append(
                SemanticCandidate(
                    id=f"pad_candidate_{index}",
                    kind="pad_candidate",
                    layer_name=str(entity.get("layer", "0")),
                    confidence=bump_confidence(0.77, 0.08, repeated_bonus, regularity_bonus),
                    source_indices=(index,),
                    geometry={"bbox": bbox, "center": _entity_center(entity), "size": (width, height)},
                    properties={
                        "pad_kind": cluster_name,
                        "shape": "rectangle",
                        "cluster_size": cluster_size,
                        "size_signature": signature,
                        "aspect_ratio": round(aspect_ratio, 3),
                    },
                )
            )
    return candidates


def _classify_die_regions(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    regions = [
        (index, entity)
        for index, entity in _closed_entities_for_role(raw_entities, layer_roles, "die_region")
        if not _is_circle_entity(entity)
    ]
    if not regions:
        return []

    areas = sorted(_entity_area(entity) for _, entity in regions)
    median_area = areas[len(areas) // 2]

    candidates: list[SemanticCandidate] = []
    for index, entity in regions:
        area = _entity_area(entity)
        rectangular_bonus = 0.06 if _is_rectangle_like(entity) else 0.0
        size_bonus = 0.08 if area >= median_area else 0.0
        confidence = bump_confidence(0.72, size_bonus, rectangular_bonus)
        candidates.append(
            SemanticCandidate(
                id=f"die_region_candidate_{index}",
                kind="die_region_candidate",
                layer_name=str(entity.get("layer", "0")),
                confidence=confidence,
                source_indices=(index,),
                geometry={"bbox": _entity_bbox(entity), "center": _entity_center(entity), "area": area},
                properties={
                    "shape": "rectangle" if _is_rectangle_like(entity) else "region",
                    "relative_area_band": "large" if area >= median_area else "small",
                },
            )
        )
    return candidates


def _classify_wires(raw_entities: list[RawEntity], layer_roles: dict[str, str | None]) -> list[SemanticCandidate]:
    candidates: list[SemanticCandidate] = []
    for index, entity in _open_entities_for_role(raw_entities, layer_roles, "wire"):
        path = _entity_points(entity)
        if len(path) < 2:
            continue
        length = _polyline_length(path)
        if length < 0.5:
            continue
        segment_count = len(path) - 1
        bend_count, max_turn_degrees, direction_consistency = _polyline_turn_metrics(path)
        consistency_bonus = 0.06 if direction_consistency >= 0.9 else 0.03 if direction_consistency >= 0.72 else 0.0
        bend_bonus = 0.04 if bend_count == 0 else 0.02 if max_turn_degrees <= 35.0 else 0.0
        candidates.append(
            SemanticCandidate(
                id=f"wire_candidate_{index}",
                kind="wire_candidate",
                layer_name=str(entity.get("layer", "0")),
                confidence=bump_confidence(0.66, 0.08 if length > 5.0 else 0.0, consistency_bonus, bend_bonus),
                source_indices=(index,),
                geometry={
                    "path": tuple(path),
                    "start_point": path[0],
                    "end_point": path[-1],
                    "bbox": _entity_bbox(entity),
                },
                properties={
                    "path_length": length,
                    "segment_count": segment_count,
                    "bend_count": bend_count,
                    "max_turn_degrees": round(max_turn_degrees, 2),
                    "direction_consistency": round(direction_consistency, 3),
                },
            )
        )
    return candidates


def _entities_for_role(
    raw_entities: list[RawEntity],
    layer_roles: dict[str, str | None],
    role_name: str,
) -> list[tuple[int, RawEntity]]:
    return [
        (index, entity)
        for index, entity in enumerate(raw_entities)
        if layer_roles.get(str(entity.get("layer", "0"))) == role_name
    ]


def _closed_entities_for_role(
    raw_entities: list[RawEntity],
    layer_roles: dict[str, str | None],
    role_name: str,
) -> list[tuple[int, RawEntity]]:
    return [(index, entity) for index, entity in _entities_for_role(raw_entities, layer_roles, role_name) if _is_closed(entity)]


def _open_entities_for_role(
    raw_entities: list[RawEntity],
    layer_roles: dict[str, str | None],
    role_name: str,
) -> list[tuple[int, RawEntity]]:
    return [(index, entity) for index, entity in _entities_for_role(raw_entities, layer_roles, role_name) if not _is_closed(entity)]


def _is_closed(entity: RawEntity) -> bool:
    return entity["type"] == "CIRCLE" or (entity["type"] == "LWPOLYLINE" and bool(entity.get("closed")))


def _is_circle_entity(entity: RawEntity) -> bool:
    return entity["type"] == "CIRCLE"


def _entity_points(entity: RawEntity) -> list[Point2D]:
    if entity["type"] == "LINE":
        return [entity["start"], entity["end"]]
    if entity["type"] == "LWPOLYLINE":
        return [tuple(point) for point in entity.get("points", [])]
    if entity["type"] == "ARC":
        return [tuple(point) for point in entity.get("points", [])]
    if entity["type"] == "CIRCLE":
        center_x, center_y = entity["center"]
        radius = float(entity["radius"])
        return [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y + radius),
        ]
    if entity["type"] == "POINT":
        return [entity["location"]]
    return []


def _optional_entity_bbox(entity: RawEntity) -> tuple[float, float, float, float] | None:
    if entity["type"] == "CIRCLE":
        center_x, center_y = entity["center"]
        radius = float(entity["radius"])
        return center_x - radius, center_y - radius, center_x + radius, center_y + radius

    points = _entity_points(entity)
    if not points:
        return None

    x_values = [float(point[0]) for point in points]
    y_values = [float(point[1]) for point in points]
    return min(x_values), min(y_values), max(x_values), max(y_values)


def _entity_bbox(entity: RawEntity) -> tuple[float, float, float, float]:
    bbox = _optional_entity_bbox(entity)
    if bbox is None:
        raise ValueError(f"Entity {entity.get('type', 'UNKNOWN')} has no bounding box points")
    return bbox


def _entity_center(entity: RawEntity) -> tuple[float, float]:
    if entity["type"] == "CIRCLE":
        center_x, center_y = entity["center"]
        return float(center_x), float(center_y)
    min_x, min_y, max_x, max_y = _entity_bbox(entity)
    return (min_x + max_x) / 2.0, (min_y + max_y) / 2.0


def _entity_area(entity: RawEntity) -> float:
    if entity["type"] == "CIRCLE":
        radius = float(entity["radius"])
        return math.pi * radius * radius
    if entity["type"] == "LWPOLYLINE" and entity.get("closed"):
        points = _entity_points(entity)
        if len(points) < 3:
            return 0.0
        area = 0.0
        for current, next_point in zip(points, points[1:] + points[:1]):
            area += current[0] * next_point[1] - next_point[0] * current[1]
        return abs(area) / 2.0
    return 0.0


def _round_entity_diameter(entity: RawEntity) -> float | None:
    if entity["type"] == "CIRCLE":
        return float(entity["radius"]) * 2.0
    if entity["type"] == "LWPOLYLINE" and entity.get("closed"):
        bbox = _entity_bbox(entity)
        width, height = _bbox_size(bbox)
        if max(width, height, 1e-6) <= 0:
            return None
        if abs(width - height) / max(width, height, 1e-6) > 0.20:
            return None
        points = _entity_points(entity)
        if len(points) < 8:
            return None
        return (width + height) / 2.0
    return None


def _slot_profile(entity: RawEntity) -> dict[str, object] | None:
    if entity["type"] != "LWPOLYLINE" or not entity.get("closed"):
        return None
    bbox = _entity_bbox(entity)
    width, height = _bbox_size(bbox)
    if min(width, height) <= 0:
        return None
    aspect_ratio = _bbox_aspect_ratio(bbox)
    if aspect_ratio < 1.8 or aspect_ratio > 8.0:
        return None
    area = _entity_area(entity)
    bbox_area = max(width * height, 1e-6)
    fill_ratio = area / bbox_area
    if fill_ratio < 0.45 or fill_ratio > 0.95:
        return None
    return {
        "aspect_ratio": round(aspect_ratio, 3),
        "size": (round(width, 4), round(height, 4)),
        "fill_ratio": round(fill_ratio, 3),
    }


def _substrate_round_rule_source(
    hole_kind: str,
    *,
    edge_contacts: tuple[str, ...],
    repeated_count: int,
    concentric_count: int,
    feature_bbox: tuple[float, float, float, float],
    substrate_bbox: tuple[float, float, float, float],
) -> str:
    if concentric_count >= 2:
        return "substrate_concentric_round"
    if len(edge_contacts) >= 2:
        return "substrate_corner_mounting_hole"
    if len(edge_contacts) == 1:
        return "substrate_edge_tooling_hole"

    feature_diameter = max(feature_bbox[2] - feature_bbox[0], feature_bbox[3] - feature_bbox[1], 0.0)
    substrate_span = max(substrate_bbox[2] - substrate_bbox[0], substrate_bbox[3] - substrate_bbox[1], 1.0)
    relative_diameter = feature_diameter / substrate_span

    if repeated_count >= 2 and relative_diameter <= 0.20:
        return "substrate_repeated_round_hole"
    if hole_kind == "tooling" and relative_diameter <= 0.06:
        return "substrate_small_round_hole"
    return "substrate_round_feature"


def _bbox_size(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bbox
    return abs(max_x - min_x), abs(max_y - min_y)


def _bbox_aspect_ratio(bbox: tuple[float, float, float, float]) -> float:
    width, height = _bbox_size(bbox)
    smaller = max(min(width, height), 1e-6)
    larger = max(width, height)
    return larger / smaller


def _is_rectangle_like(entity: RawEntity) -> bool:
    if entity["type"] != "LWPOLYLINE" or not entity.get("closed"):
        return False
    points = _entity_points(entity)
    unique_points = list(dict.fromkeys(points))
    return len(unique_points) in {4, 5}


def _bbox_inside(inner: tuple[float, float, float, float], outer: tuple[float, float, float, float]) -> bool:
    return (
        inner[0] >= outer[0]
        and inner[1] >= outer[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _round_feature_repeat_counts(
    round_entities: list[tuple[int, RawEntity]],
) -> dict[int, int]:
    counts: dict[int, int] = {}
    sizes = {
        index: round(max(abs(_entity_bbox(entity)[2] - _entity_bbox(entity)[0]), abs(_entity_bbox(entity)[3] - _entity_bbox(entity)[1])), 3)
        for index, entity in round_entities
    }
    for index, size in sizes.items():
        counts[index] = sum(1 for other_size in sizes.values() if abs(other_size - size) <= max(size * 0.15, 0.2))
    return counts


def _concentric_round_counts(
    round_entities: list[tuple[int, RawEntity]],
) -> dict[int, int]:
    counts: dict[int, int] = {}
    profiles = {
        index: {
            "center": _entity_center(entity),
            "diameter": _round_entity_diameter(entity),
        }
        for index, entity in round_entities
    }
    for index, profile in profiles.items():
        diameter = profile["diameter"]
        if diameter is None:
            counts[index] = 1
            continue
        tolerance = max(diameter * 0.08, 0.15)
        center_x, center_y = profile["center"]
        counts[index] = sum(
            1
            for other in profiles.values()
            if other["diameter"] is not None
            and abs(center_x - other["center"][0]) <= tolerance
            and abs(center_y - other["center"][1]) <= tolerance
        )
    return counts


def _bbox_size_similarity(
    first_bbox: tuple[float, float, float, float],
    second_bbox: tuple[float, float, float, float],
) -> float:
    first_width, first_height = _bbox_size(first_bbox)
    second_width, second_height = _bbox_size(second_bbox)
    width_ratio = min(first_width, second_width) / max(first_width, second_width, 1e-6)
    height_ratio = min(first_height, second_height) / max(first_height, second_height, 1e-6)
    return min(width_ratio, height_ratio)


def _cluster_rectangles_by_area(
    rectangles: Iterable[tuple[int, RawEntity]],
) -> dict[str, list[tuple[int, RawEntity]]]:
    ordered = sorted(rectangles, key=lambda item: _entity_area(item[1]))
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {"medium": ordered}
    if len(ordered) == 2:
        return {"small": [ordered[0]], "large": [ordered[1]]}

    first_cut = max(1, len(ordered) // 3)
    second_cut = max(first_cut + 1, (len(ordered) * 2) // 3)
    return {
        "small": ordered[:first_cut],
        "medium": ordered[first_cut:second_cut],
        "large": ordered[second_cut:],
    }


def _cluster_rectangles_by_dimensions(
    rectangles: Iterable[tuple[int, RawEntity]],
) -> dict[str, dict[str, object]]:
    records = [
        {
            "index": index,
            "entity": entity,
            "bbox": _entity_bbox(entity),
            "area": _entity_area(entity),
        }
        for index, entity in rectangles
    ]
    if not records:
        return {}

    clusters: list[dict[str, object]] = []
    for record in sorted(records, key=lambda item: item["area"]):
        width, height = _bbox_size(record["bbox"])
        matched_cluster: dict[str, object] | None = None
        for cluster in clusters:
            signature = cluster["signature"]
            if _dimensions_match((width, height), signature):
                matched_cluster = cluster
                break

        if matched_cluster is None:
            clusters.append(
                {
                    "members": [(record["index"], record["entity"])],
                    "widths": [width],
                    "heights": [height],
                    "areas": [record["area"]],
                    "signature": (round(width, 3), round(height, 3)),
                }
            )
            continue

        matched_cluster["members"].append((record["index"], record["entity"]))
        matched_cluster["widths"].append(width)
        matched_cluster["heights"].append(height)
        matched_cluster["areas"].append(record["area"])
        matched_cluster["signature"] = (
            round(sum(matched_cluster["widths"]) / len(matched_cluster["widths"]), 3),
            round(sum(matched_cluster["heights"]) / len(matched_cluster["heights"]), 3),
        )

    clusters.sort(key=lambda cluster: sum(cluster["areas"]) / max(len(cluster["areas"]), 1))
    labels = _cluster_labels(len(clusters))
    return {
        label: {
            "members": list(cluster["members"]),
            "signature": cluster["signature"],
        }
        for label, cluster in zip(labels, clusters)
    }


def _cluster_labels(count: int) -> list[str]:
    if count <= 0:
        return []
    if count == 1:
        return ["medium"]
    if count == 2:
        return ["small", "large"]
    if count == 3:
        return ["small", "medium", "large"]
    labels = ["xsmall", "small", "medium", "large", "xlarge"]
    if count <= len(labels):
        return labels[:count]
    return [f"group_{index + 1}" for index in range(count)]


def _dimensions_match(
    current: tuple[float, float],
    signature: tuple[float, float],
    *,
    tolerance_ratio: float = 0.18,
) -> bool:
    current_dims = sorted((float(current[0]), float(current[1])))
    signature_dims = sorted((float(signature[0]), float(signature[1])))
    for current_dim, signature_dim in zip(current_dims, signature_dims):
        baseline = max(abs(signature_dim), 1.0)
        if abs(current_dim - signature_dim) / baseline > tolerance_ratio:
            return False
    return True


def _polyline_length(points: list[Point2D]) -> float:
    return sum(
        math.hypot(float(next_point[0]) - float(current[0]), float(next_point[1]) - float(current[1]))
        for current, next_point in zip(points, points[1:])
    )


def _polyline_turn_metrics(points: list[Point2D]) -> tuple[int, float, float]:
    vectors = [
        _normalize_vector(
            float(next_point[0]) - float(current[0]),
            float(next_point[1]) - float(current[1]),
        )
        for current, next_point in zip(points, points[1:])
    ]
    vectors = [vector for vector in vectors if vector != (0.0, 0.0)]
    if len(vectors) <= 1:
        return 0, 0.0, 1.0

    bend_count = 0
    max_turn_degrees = 0.0
    consistency_scores: list[float] = []

    for first, second in zip(vectors, vectors[1:]):
        dot = max(-1.0, min(1.0, first[0] * second[0] + first[1] * second[1]))
        angle = math.degrees(math.acos(dot))
        if angle >= 12.0:
            bend_count += 1
        max_turn_degrees = max(max_turn_degrees, angle)
        consistency_scores.append(max(dot, 0.0))

    if not consistency_scores:
        return bend_count, max_turn_degrees, 1.0
    return bend_count, max_turn_degrees, sum(consistency_scores) / len(consistency_scores)


def _normalize_vector(dx: float, dy: float) -> tuple[float, float]:
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return 0.0, 0.0
    return dx / length, dy / length


__all__ = ["SemanticClassificationResult", "classify_semantic_layers"]
