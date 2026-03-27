"""Shared type definitions for raw DXF payloads."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


Point2D = tuple[float, float]
SceneRect = tuple[float, float, float, float]


class RawLineEntity(TypedDict):
    type: Literal["LINE"]
    start: Point2D
    end: Point2D
    layer: str


class RawCircleEntity(TypedDict):
    type: Literal["CIRCLE"]
    center: Point2D
    radius: float
    layer: str


class RawArcEntity(TypedDict):
    type: Literal["ARC"]
    center: Point2D
    radius: float
    start_angle: float
    end_angle: float
    points: list[Point2D]
    layer: str


class RawLWPolylineEntity(TypedDict):
    type: Literal["LWPOLYLINE"]
    points: list[Point2D]
    closed: bool
    layer: str


class RawPointEntity(TypedDict):
    type: Literal["POINT"]
    location: Point2D
    layer: str


RawEntity = RawLineEntity | RawCircleEntity | RawArcEntity | RawLWPolylineEntity | RawPointEntity


class LayerInfo(TypedDict):
    name: str
    color: int
    linetype: str
    is_off: bool
    is_frozen: bool
    is_locked: bool
    is_visible: bool
    plot: bool
    mapped_type: str | None
    suggested_role: NotRequired[str | None]
    enabled: NotRequired[bool]
    entity_count: int
    entity_types: dict[str, int]


__all__ = [
    "LayerInfo",
    "Point2D",
    "RawArcEntity",
    "RawCircleEntity",
    "RawEntity",
    "RawLineEntity",
    "RawLWPolylineEntity",
    "RawPointEntity",
    "SceneRect",
]
