"""Shared DXF geometry sampling helpers."""

from __future__ import annotations

import math
from typing import Any

from ezdxf.math import bulge_to_arc


def sample_arc_points(
    center_x: float,
    center_y: float,
    radius: float,
    start_deg: float,
    end_deg: float,
    steps: int = 24,
) -> list[tuple[float, float]]:
    """Sample an ARC entity into XY points."""

    if end_deg < start_deg:
        end_deg += 360.0

    span = end_deg - start_deg
    return [
        (
            center_x + math.cos(math.radians(start_deg + span * index / steps)) * radius,
            center_y + math.sin(math.radians(start_deg + span * index / steps)) * radius,
        )
        for index in range(steps + 1)
    ]


def sample_bulge_segment(
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    bulge: float,
) -> list[tuple[float, float]]:
    """Sample a bulge segment into intermediate XY points."""

    if abs(bulge) <= 1e-9:
        return [end_point]

    center, start_angle, end_angle, radius = bulge_to_arc(start_point, end_point, bulge)
    if bulge > 0 and end_angle <= start_angle:
        end_angle += math.tau
    elif bulge < 0 and end_angle >= start_angle:
        end_angle -= math.tau

    sweep = end_angle - start_angle
    steps = max(8, min(48, int(abs(sweep) / (math.pi / 18.0)) + 1))
    points = [
        (
            center.x + math.cos(start_angle + sweep * step / steps) * radius,
            center.y + math.sin(start_angle + sweep * step / steps) * radius,
        )
        for step in range(1, steps)
    ]
    points.append(end_point)
    return points


def expand_lwpolyline_points(entity: Any) -> list[tuple[float, float]]:
    """Expand an LWPOLYLINE entity into XY points, preserving bulge arcs."""

    vertices = list(entity.get_points("xyb"))
    if not vertices:
        return []

    points: list[tuple[float, float]] = [(float(vertices[0][0]), float(vertices[0][1]))]
    pairs = list(zip(vertices, vertices[1:]))
    if entity.closed:
        pairs.append((vertices[-1], vertices[0]))

    for start_vertex, end_vertex in pairs:
        start_point = (float(start_vertex[0]), float(start_vertex[1]))
        end_point = (float(end_vertex[0]), float(end_vertex[1]))
        bulge = float(start_vertex[2]) if len(start_vertex) > 2 else 0.0
        points.extend(sample_bulge_segment(start_point, end_point, bulge))

    if entity.closed and len(points) > 1:
        first_x, first_y = points[0]
        last_x, last_y = points[-1]
        if math.isclose(first_x, last_x, abs_tol=1e-9) and math.isclose(first_y, last_y, abs_tol=1e-9):
            points.pop()

    return points


__all__ = ["expand_lwpolyline_points", "sample_arc_points", "sample_bulge_segment"]
