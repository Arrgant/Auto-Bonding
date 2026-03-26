"""Geometry fallback inference for loosely structured DXF input."""

from __future__ import annotations

from typing import Any

from .fallback_helpers import (
    FallbackConfig,
    classify_polyline_entity,
    detect_circle_like_profile,
    infer_arc_entity,
    infer_circle_entity,
    infer_line_entity,
    polyline_bbox,
    polyline_length,
)
from .geometry.converter import BondingElement
from .raw_dxf_types import Point2D, RawEntity


def _polyline_length(points: list[Point2D]) -> float:
    return polyline_length(points)


def _polyline_bbox(points: list[Point2D]) -> tuple[float, float, float, float]:
    return polyline_bbox(points)


def _detect_circle_like_profile(
    points: list[Point2D],
    aspect_tolerance: float = 0.18,
    radial_tolerance: float = 0.18,
) -> tuple[float, float, float] | None:
    return detect_circle_like_profile(points, aspect_tolerance=aspect_tolerance, radial_tolerance=radial_tolerance)


def infer_elements_from_raw_entities(raw_entities: list[RawEntity], config: dict[str, Any]) -> list[BondingElement]:
    inferred: list[BondingElement] = []
    closed_poly_candidates: list[tuple[float, BondingElement]] = []
    open_poly_candidates: list[tuple[float, BondingElement]] = []
    round_candidates: list[tuple[float, BondingElement]] = []

    fallback_config = FallbackConfig.from_mapping(config)

    for entity in raw_entities:
        entity_type = entity["type"]
        if entity_type == "LINE":
            inferred.append(infer_line_entity(entity, fallback_config))
        elif entity_type == "ARC":
            inferred_arc = infer_arc_entity(entity, fallback_config)
            if inferred_arc is not None:
                inferred.append(inferred_arc)
        elif entity_type == "CIRCLE":
            inferred.append(infer_circle_entity(entity))
        elif entity_type == "LWPOLYLINE":
            candidate = classify_polyline_entity(entity, fallback_config)
            if candidate is None:
                continue

            group, score, element = candidate
            if group == "closed":
                closed_poly_candidates.append((score, element))
            elif group == "round":
                round_candidates.append((score, element))
            else:
                open_poly_candidates.append((score, element))

    inferred.extend(
        element
        for _, element in sorted(closed_poly_candidates, key=lambda item: item[0], reverse=True)[
            : fallback_config.max_closed
        ]
    )
    inferred.extend(
        element
        for _, element in sorted(open_poly_candidates, key=lambda item: item[0], reverse=True)[
            : fallback_config.max_open
        ]
    )
    inferred.extend(
        element
        for _, element in sorted(round_candidates, key=lambda item: item[0], reverse=True)[
            : fallback_config.max_round
        ]
    )
    return inferred
