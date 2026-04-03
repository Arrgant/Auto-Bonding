"""Helpers for extracting structured wire geometry from raw DXF entities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..raw_dxf_types import LayerInfo, Point2D, RawArcEntity, RawEntity, RawLWPolylineEntity, RawLineEntity
from .wire_models import WireGeometry, WirePoint


WireMergeEndpointAlignment = Literal["continuous", "same_role_conflict"]
WireMergeAction = Literal["join_as_is", "reverse_first_then_join", "reverse_second_then_join"]


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


def format_wire_extraction_audit_report(audit: WireExtractionAudit) -> str:
    """Render a deterministic text report for reviewing wire extraction quality."""

    lines = [
        "Wire Extraction Audit",
        f"Wire layers: {', '.join(audit.wire_layers) if audit.wire_layers else '(none)'}",
        f"Converted entities: {audit.extracted_wire_count}/{audit.candidate_entity_count}",
        "",
        "Extracted entity types:",
    ]
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

    lines.extend(["", "Potential split-wire joins:"])
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
    "WireExtractionSkippedEntity",
    "WireMergeAction",
    "WireMergeEndpointAlignment",
    "build_wire_merge_proposals",
    "extract_wire_geometries",
    "extract_wire_geometries_with_audit",
    "format_wire_extraction_audit_report",
    "write_wire_extraction_audit_report",
]
