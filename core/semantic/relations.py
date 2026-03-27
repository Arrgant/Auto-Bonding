"""Cross-layer relation weighting for semantic candidates."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .candidates import SemanticCandidate
from .confidence import bump_confidence


@dataclass(frozen=True)
class RelationNote:
    """One applied cross-layer relationship and its confidence impact."""

    source_id: str
    target_id: str
    relation: str
    weight: float


def apply_cross_layer_relations(
    candidates: list[SemanticCandidate],
) -> tuple[list[SemanticCandidate], list[RelationNote]]:
    """Boost candidate confidence using simple cross-layer spatial hints."""

    notes: list[RelationNote] = []
    pad_candidates = [candidate for candidate in candidates if candidate.kind == "pad_candidate"]
    module_candidates = [candidate for candidate in candidates if candidate.kind == "module_region_candidate"]
    updated: list[SemanticCandidate] = []
    for candidate in candidates:
        current = candidate

        if candidate.kind == "wire_candidate":
            endpoints = _extract_wire_endpoints(candidate)
            if endpoints:
                path = candidate.geometry.get("path") or ()
                start_anchor = _nearest_pad_anchor(
                    endpoints[0],
                    pad_candidates,
                    inward_direction=_endpoint_inward_direction(path, endpoint="start"),
                )
                end_anchor = _nearest_pad_anchor(
                    endpoints[1],
                    pad_candidates,
                    inward_direction=_endpoint_inward_direction(path, endpoint="end"),
                )
                current = _apply_wire_anchor_properties(current, start_anchor, end_anchor)
                if start_anchor is not None:
                    notes.append(RelationNote(candidate.id, start_anchor["candidate"].id, "wire_start_snapped", 0.06))
                if end_anchor is not None:
                    notes.append(RelationNote(candidate.id, end_anchor["candidate"].id, "wire_end_snapped", 0.06))
                if start_anchor is not None and end_anchor is not None:
                    same_pad = start_anchor["candidate"].id == end_anchor["candidate"].id
                    pair_bonus = 0.20 if not same_pad else 0.10
                    precision_bonus = 0.04 if max(start_anchor["distance"], end_anchor["distance"]) <= 0.25 else 0.0
                    current = replace(current, confidence=bump_confidence(current.confidence, pair_bonus, precision_bonus))
                    notes.append(
                        RelationNote(
                            candidate.id,
                            "pad-pair" if not same_pad else start_anchor["candidate"].id,
                            "wire_to_pad_pair" if not same_pad else "wire_self_loop",
                            pair_bonus + precision_bonus,
                        )
                    )
                elif start_anchor is not None or end_anchor is not None:
                    current = replace(current, confidence=bump_confidence(current.confidence, 0.10))
                    notes.append(RelationNote(candidate.id, "pad-group", "wire_to_pad_partial", 0.10))

        elif candidate.kind == "pad_candidate":
            containing_modules = [
                module for module in module_candidates if _center_inside_bbox(_candidate_center(candidate), module)
            ]
            cluster_size = int(candidate.properties.get("cluster_size", 1))
            bonuses: list[float] = []
            if containing_modules:
                bonuses.append(0.08)
                notes.append(RelationNote(candidate.id, "module-region", "pad_inside_module", 0.08))
            if cluster_size >= 3:
                bonuses.append(0.04)
                notes.append(RelationNote(candidate.id, "pad-cluster", "pad_repeated_cluster", 0.04))
            if bonuses:
                current = replace(current, confidence=bump_confidence(current.confidence, *bonuses))

        elif candidate.kind == "die_region_candidate":
            bonuses, relation_notes, properties = _die_region_relation_details(candidate, module_candidates, pad_candidates)
            if bonuses:
                current = replace(
                    current,
                    confidence=bump_confidence(current.confidence, *bonuses),
                    properties=dict(current.properties) | properties,
                )
                notes.extend(relation_notes)

        updated.append(current)

    return updated, notes


def _extract_wire_endpoints(candidate: SemanticCandidate) -> tuple[tuple[float, float], tuple[float, float]] | None:
    start_point = candidate.geometry.get("start_point")
    end_point = candidate.geometry.get("end_point")
    if start_point is None or end_point is None:
        return None
    return (float(start_point[0]), float(start_point[1])), (float(end_point[0]), float(end_point[1]))


def _candidate_center(candidate: SemanticCandidate) -> tuple[float, float]:
    if "center" in candidate.geometry:
        center = candidate.geometry["center"]
        return float(center[0]), float(center[1])
    bbox = candidate.geometry.get("bbox") or (0.0, 0.0, 0.0, 0.0)
    min_x, min_y, max_x, max_y = bbox
    return (float(min_x + max_x) / 2.0, float(min_y + max_y) / 2.0)


def _point_near_candidate(point: tuple[float, float], candidate: SemanticCandidate) -> bool:
    center_x, center_y = _candidate_center(candidate)
    bbox = candidate.geometry.get("bbox") or (center_x, center_y, center_x, center_y)
    min_x, min_y, max_x, max_y = bbox
    tolerance = max(abs(max_x - min_x), abs(max_y - min_y), 1.0) * 1.2
    return abs(point[0] - center_x) <= tolerance and abs(point[1] - center_y) <= tolerance


def _nearest_pad_anchor(
    point: tuple[float, float],
    pad_candidates: list[SemanticCandidate],
    *,
    inward_direction: tuple[float, float] | None = None,
) -> dict[str, object] | None:
    best: dict[str, object] | None = None
    for candidate in pad_candidates:
        bbox = candidate.geometry.get("bbox")
        if bbox is None:
            continue
        snapped = _snap_point_to_bbox(point, bbox)
        distance = _distance(point, snapped)
        center = _candidate_center(candidate)
        width = abs(bbox[2] - bbox[0])
        height = abs(bbox[3] - bbox[1])
        tolerance = max(min(width, height) * 1.4, max(width, height) * 0.55, 0.9)
        if distance > tolerance:
            continue
        alignment = _direction_alignment(
            inward_direction,
            _normalize_vector(center[0] - point[0], center[1] - point[1]),
        )
        cluster_bonus = min(int(candidate.properties.get("cluster_size", 1)), 4) * 0.015
        score = distance - alignment * 0.35 - cluster_bonus
        if best is None or score < best["score"]:
            best = {
                "candidate": candidate,
                "snapped": snapped,
                "distance": distance,
                "alignment": alignment,
                "score": score,
            }
    return best


def _apply_wire_anchor_properties(
    candidate: SemanticCandidate,
    start_anchor: dict[str, object] | None,
    end_anchor: dict[str, object] | None,
) -> SemanticCandidate:
    geometry = dict(candidate.geometry)
    properties = dict(candidate.properties)

    if start_anchor is not None:
        geometry["snapped_start_point"] = start_anchor["snapped"]
        properties["start_pad_id"] = start_anchor["candidate"].id
        properties["start_snap_distance"] = round(float(start_anchor["distance"]), 4)
        properties["start_anchor_alignment"] = round(float(start_anchor["alignment"]), 3)
    if end_anchor is not None:
        geometry["snapped_end_point"] = end_anchor["snapped"]
        properties["end_pad_id"] = end_anchor["candidate"].id
        properties["end_snap_distance"] = round(float(end_anchor["distance"]), 4)
        properties["end_anchor_alignment"] = round(float(end_anchor["alignment"]), 3)
    return replace(candidate, geometry=geometry, properties=properties)


def _die_region_relation_details(
    candidate: SemanticCandidate,
    module_candidates: list[SemanticCandidate],
    pad_candidates: list[SemanticCandidate],
) -> tuple[list[float], list[RelationNote], dict[str, object]]:
    bonuses: list[float] = []
    notes: list[RelationNote] = []
    properties: dict[str, object] = {}
    bbox = candidate.geometry.get("bbox")
    if bbox is None:
        return bonuses, notes, properties

    overlap_ratios = [
        _bbox_overlap_ratio(bbox, module.geometry.get("bbox"))
        for module in module_candidates
        if module.geometry.get("bbox") is not None
    ]
    best_overlap = max(overlap_ratios, default=0.0)
    properties["module_overlap_ratio"] = round(best_overlap, 3)

    if best_overlap >= 0.9 or any(_center_inside_bbox(_candidate_center(candidate), module) for module in module_candidates):
        bonuses.append(0.12)
        notes.append(RelationNote(candidate.id, "module-region", "die_inside_module", 0.12))
    elif best_overlap >= 0.5:
        bonuses.append(0.06)
        notes.append(RelationNote(candidate.id, "module-region", "die_overlap_module", 0.06))

    nearby_pads = [
        pad
        for pad in pad_candidates
        if _bbox_gap_distance(bbox, pad.geometry.get("bbox")) <= _die_pad_distance_limit(bbox, pad.geometry.get("bbox"))
    ]
    properties["nearby_pad_count"] = len(nearby_pads)
    if nearby_pads:
        properties["nearby_pad_ids"] = tuple(pad.id for pad in nearby_pads[:4])

    if len(nearby_pads) >= 2:
        bonuses.append(0.10)
        notes.append(RelationNote(candidate.id, "pad-group", "die_near_pad_group", 0.10))
    elif len(nearby_pads) == 1:
        bonuses.append(0.04)
        notes.append(RelationNote(candidate.id, nearby_pads[0].id, "die_near_pad", 0.04))

    side_contacts = _die_pad_side_contacts(bbox, nearby_pads)
    properties["pad_side_coverage"] = tuple(sorted(side_contacts))
    properties["pad_side_count"] = len(side_contacts)
    if len(side_contacts) >= 3:
        bonuses.append(0.08)
        notes.append(RelationNote(candidate.id, "pad-group", "die_surrounded_by_pads", 0.08))
    elif {"left", "right"} <= side_contacts or {"top", "bottom"} <= side_contacts:
        bonuses.append(0.05)
        notes.append(RelationNote(candidate.id, "pad-group", "die_bridged_by_opposite_pads", 0.05))

    best_module_bbox = None
    best_module_overlap = 0.0
    for module in module_candidates:
        module_bbox = module.geometry.get("bbox")
        if module_bbox is None:
            continue
        overlap = _bbox_overlap_ratio(bbox, module_bbox)
        if overlap > best_module_overlap:
            best_module_overlap = overlap
            best_module_bbox = module_bbox
    edge_contacts = _module_edge_contacts(bbox, best_module_bbox)
    properties["module_edge_contacts"] = tuple(edge_contacts)
    properties["touches_module_edge"] = bool(edge_contacts)

    return bonuses, notes, properties


def _snap_point_to_bbox(point: tuple[float, float], bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bbox
    return (
        min(max(point[0], min_x), max_x),
        min(max(point[1], min_y), max_y),
    )


def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return ((first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2) ** 0.5


def _normalize_vector(dx: float, dy: float) -> tuple[float, float]:
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 1e-9:
        return 0.0, 0.0
    return dx / length, dy / length


def _direction_alignment(
    first: tuple[float, float] | None,
    second: tuple[float, float],
) -> float:
    if first is None or first == (0.0, 0.0) or second == (0.0, 0.0):
        return 0.0
    return max(-1.0, min(1.0, first[0] * second[0] + first[1] * second[1]))


def _endpoint_inward_direction(
    path: tuple[tuple[float, float], ...] | tuple[()],
    *,
    endpoint: str,
) -> tuple[float, float] | None:
    if len(path) < 2:
        return None
    if endpoint == "start":
        return _normalize_vector(path[1][0] - path[0][0], path[1][1] - path[0][1])
    return _normalize_vector(path[-2][0] - path[-1][0], path[-2][1] - path[-1][1])


def _bbox_overlap_ratio(
    first_bbox: tuple[float, float, float, float],
    second_bbox: tuple[float, float, float, float] | None,
) -> float:
    if second_bbox is None:
        return 0.0
    left = max(first_bbox[0], second_bbox[0])
    top = max(first_bbox[1], second_bbox[1])
    right = min(first_bbox[2], second_bbox[2])
    bottom = min(first_bbox[3], second_bbox[3])
    if right <= left or bottom <= top:
        return 0.0
    overlap_area = (right - left) * (bottom - top)
    first_area = max((first_bbox[2] - first_bbox[0]) * (first_bbox[3] - first_bbox[1]), 1e-6)
    return overlap_area / first_area


def _bbox_gap_distance(
    first_bbox: tuple[float, float, float, float],
    second_bbox: tuple[float, float, float, float] | None,
) -> float:
    if second_bbox is None:
        return float("inf")
    dx = max(first_bbox[0] - second_bbox[2], second_bbox[0] - first_bbox[2], 0.0)
    dy = max(first_bbox[1] - second_bbox[3], second_bbox[1] - first_bbox[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def _die_pad_distance_limit(
    die_bbox: tuple[float, float, float, float],
    pad_bbox: tuple[float, float, float, float] | None,
) -> float:
    if pad_bbox is None:
        return 0.0
    die_width = abs(die_bbox[2] - die_bbox[0])
    die_height = abs(die_bbox[3] - die_bbox[1])
    pad_width = abs(pad_bbox[2] - pad_bbox[0])
    pad_height = abs(pad_bbox[3] - pad_bbox[1])
    return max(min(die_width, die_height) * 0.45, max(pad_width, pad_height) * 1.25, 0.8)


def _die_pad_side_contacts(
    die_bbox: tuple[float, float, float, float],
    pad_candidates: list[SemanticCandidate],
) -> set[str]:
    contacts: set[str] = set()
    die_width = abs(die_bbox[2] - die_bbox[0])
    die_height = abs(die_bbox[3] - die_bbox[1])
    edge_limit = max(min(die_width, die_height) * 0.35, 0.75)

    for pad in pad_candidates:
        pad_bbox = pad.geometry.get("bbox")
        if pad_bbox is None:
            continue
        gap = _bbox_gap_distance(die_bbox, pad_bbox)
        if gap > edge_limit:
            continue

        pad_center = _candidate_center(pad)
        horizontal_overlap = _axis_overlap_ratio((die_bbox[0], die_bbox[2]), (pad_bbox[0], pad_bbox[2]))
        vertical_overlap = _axis_overlap_ratio((die_bbox[1], die_bbox[3]), (pad_bbox[1], pad_bbox[3]))

        if pad_center[0] <= die_bbox[0] and vertical_overlap >= 0.2:
            contacts.add("left")
        elif pad_center[0] >= die_bbox[2] and vertical_overlap >= 0.2:
            contacts.add("right")
        elif pad_center[1] <= die_bbox[1] and horizontal_overlap >= 0.2:
            contacts.add("bottom")
        elif pad_center[1] >= die_bbox[3] and horizontal_overlap >= 0.2:
            contacts.add("top")

    return contacts


def _module_edge_contacts(
    die_bbox: tuple[float, float, float, float],
    module_bbox: tuple[float, float, float, float] | None,
) -> list[str]:
    if module_bbox is None:
        return []
    die_width = abs(die_bbox[2] - die_bbox[0])
    die_height = abs(die_bbox[3] - die_bbox[1])
    threshold = max(min(die_width, die_height) * 0.2, 0.35)
    contacts: list[str] = []
    if abs(die_bbox[0] - module_bbox[0]) <= threshold:
        contacts.append("left")
    if abs(die_bbox[2] - module_bbox[2]) <= threshold:
        contacts.append("right")
    if abs(die_bbox[1] - module_bbox[1]) <= threshold:
        contacts.append("bottom")
    if abs(die_bbox[3] - module_bbox[3]) <= threshold:
        contacts.append("top")
    return contacts


def _axis_overlap_ratio(
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    left = max(min(first), min(second))
    right = min(max(first), max(second))
    if right <= left:
        return 0.0
    overlap = right - left
    baseline = max(min(abs(first[1] - first[0]), abs(second[1] - second[0])), 1e-6)
    return overlap / baseline


def _center_inside_bbox(center: tuple[float, float], candidate: SemanticCandidate) -> bool:
    bbox = candidate.geometry.get("bbox")
    if bbox is None:
        return False
    min_x, min_y, max_x, max_y = bbox
    return min_x <= center[0] <= max_x and min_y <= center[1] <= max_y


__all__ = ["RelationNote", "apply_cross_layer_relations"]
