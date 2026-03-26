"""Internal helpers for geometric fallback inference."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .geometry.converter import BondingElement
from .raw_dxf_types import Point2D, RawArcEntity, RawCircleEntity, RawLWPolylineEntity, RawLineEntity


@dataclass(frozen=True)
class FallbackConfig:
    """Resolved fallback thresholds and default element properties."""

    default_wire_diameter: float
    default_material: str
    min_closed_area: float
    min_open_length: float
    min_round_radius: float
    max_closed: int
    max_open: int
    max_round: int

    @classmethod
    def from_mapping(cls, config: dict[str, Any]) -> "FallbackConfig":
        return cls(
            default_wire_diameter=float(config["default_wire_diameter"]),
            default_material=str(config["default_material"]),
            min_closed_area=float(config.get("fallback_closed_polyline_min_area", 0.02)),
            min_open_length=float(config.get("fallback_open_polyline_min_length", 0.10)),
            min_round_radius=float(config.get("fallback_min_round_radius", 0.03)),
            max_closed=int(config.get("fallback_max_closed_polylines", 60)),
            max_open=int(config.get("fallback_max_open_polylines", 120)),
            max_round=int(config.get("fallback_max_round_features", 120)),
        )


def polyline_length(points: list[Point2D]) -> float:
    """Return the polyline path length."""

    length = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        dx = float(x2) - float(x1)
        dy = float(y2) - float(y1)
        length += math.hypot(dx, dy)
    return length


def polyline_bbox(points: list[Point2D]) -> tuple[float, float, float, float]:
    """Return a polyline bounding box."""

    xs = [float(x_value) for x_value, _ in points]
    ys = [float(y_value) for _, y_value in points]
    return min(xs), min(ys), max(xs), max(ys)


def detect_circle_like_profile(
    points: list[Point2D],
    aspect_tolerance: float = 0.18,
    radial_tolerance: float = 0.18,
) -> tuple[float, float, float] | None:
    """Detect whether a closed polyline approximates a circle."""

    if len(points) < 8:
        return None

    min_x, min_y, max_x, max_y = polyline_bbox(points)
    width = max_x - min_x
    height = max_y - min_y
    if width <= 1e-9 or height <= 1e-9:
        return None

    ratio = abs(width - height) / max(width, height)
    if ratio > aspect_tolerance:
        return None

    center_x = min_x + width / 2.0
    center_y = min_y + height / 2.0
    distances = [math.hypot(x_value - center_x, y_value - center_y) for x_value, y_value in points]
    average_radius = sum(distances) / len(distances)
    if average_radius <= 1e-9:
        return None

    max_deviation = max(abs(distance - average_radius) for distance in distances)
    if max_deviation / average_radius > radial_tolerance:
        return None

    return center_x, center_y, average_radius


def build_wire_element(
    layer: str,
    start: Point2D,
    end: Point2D,
    config: FallbackConfig,
) -> BondingElement:
    """Build a simple wire element using fallback defaults."""

    return BondingElement(
        element_type="wire",
        layer=layer,
        geometry={
            "p1": [start[0], start[1], 0.0],
            "p2": [end[0], end[1], 0.0],
        },
        properties={
            "wire_diameter": config.default_wire_diameter,
            "material": config.default_material,
        },
    )


def build_circle_pad_element(
    layer: str,
    center_x: float,
    center_y: float,
    radius: float,
    thickness: float,
) -> BondingElement:
    """Build a circular die-pad fallback element."""

    diameter = radius * 2.0
    return BondingElement(
        element_type="die_pad",
        layer=layer,
        geometry={
            "x": center_x,
            "y": center_y,
            "z": 0.0,
            "radius": radius,
            "width": diameter,
            "height": diameter,
        },
        properties={"thickness": thickness, "shape": "circle"},
    )


def build_rect_pad_element(
    layer: str,
    min_x: float,
    min_y: float,
    width: float,
    height: float,
    thickness: float,
) -> BondingElement:
    """Build a rectangular die-pad fallback element."""

    return BondingElement(
        element_type="die_pad",
        layer=layer,
        geometry={
            "x": min_x + width / 2.0,
            "y": min_y + height / 2.0,
            "z": 0.0,
            "width": max(width, 0.02),
            "height": max(height, 0.02),
        },
        properties={"thickness": thickness},
    )


def infer_line_entity(entity: RawLineEntity, config: FallbackConfig) -> BondingElement:
    """Infer a wire from a raw LINE entity."""

    return build_wire_element(entity.get("layer", "0"), entity["start"], entity["end"], config)


def infer_arc_entity(entity: RawArcEntity, config: FallbackConfig) -> BondingElement | None:
    """Infer a wire from a raw ARC entity using sampled start/end points."""

    points = entity.get("points") or []
    if len(points) < 2:
        return None
    return build_wire_element(entity.get("layer", "0"), points[0], points[-1], config)


def infer_circle_entity(entity: RawCircleEntity) -> BondingElement:
    """Infer a circular die-pad from a raw CIRCLE entity."""

    center_x, center_y = entity["center"]
    return build_circle_pad_element(
        entity.get("layer", "0"),
        center_x,
        center_y,
        float(entity["radius"]),
        thickness=0.08,
    )


def classify_polyline_entity(
    entity: RawLWPolylineEntity,
    config: FallbackConfig,
) -> tuple[str, float, BondingElement] | None:
    """Classify a polyline fallback candidate as round, closed, or open."""

    points = entity.get("points") or []
    if len(points) < 2:
        return None

    layer = entity.get("layer", "0")

    if entity.get("closed") and len(points) >= 3:
        min_x, min_y, max_x, max_y = polyline_bbox(points)
        width = max_x - min_x
        height = max_y - min_y
        area = width * height

        circle_feature = detect_circle_like_profile(points)
        if circle_feature is not None:
            center_x, center_y, radius = circle_feature
            if radius >= config.min_round_radius:
                return (
                    "round",
                    radius,
                    build_circle_pad_element(layer, center_x, center_y, radius, thickness=0.05),
                )

        if area >= config.min_closed_area:
            return (
                "closed",
                area,
                build_rect_pad_element(layer, min_x, min_y, width, height, thickness=0.05),
            )

        return None

    path_length = polyline_length(points)
    if path_length < config.min_open_length:
        return None

    return (
        "open",
        path_length,
        build_wire_element(layer, points[0], points[-1], config),
    )


__all__ = [
    "FallbackConfig",
    "build_circle_pad_element",
    "build_rect_pad_element",
    "build_wire_element",
    "classify_polyline_entity",
    "detect_circle_like_profile",
    "infer_arc_entity",
    "infer_circle_entity",
    "infer_line_entity",
    "polyline_bbox",
    "polyline_length",
]
