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


class RawEllipseEntity(TypedDict):
    type: Literal["ELLIPSE"]
    points: list[Point2D]
    closed: bool
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


class RawTextEntity(TypedDict):
    type: Literal["TEXT", "MTEXT", "ATTRIB", "ATTDEF"]
    text: str
    insert: Point2D
    height: float
    rotation: float
    box_width: float
    layer: str


class RawHatchEntity(TypedDict):
    type: Literal["HATCH"]
    paths: list[list[Point2D]]
    solid_fill: bool
    layer: str


class RawSolidEntity(TypedDict):
    type: Literal["SOLID"]
    points: list[Point2D]
    layer: str


class RawInsertEntity(TypedDict):
    type: Literal["INSERT"]
    name: str
    insert: Point2D
    rotation: float
    xscale: float
    yscale: float
    entities: list["RawEntity"]
    layer: str


RawEntity = (
    RawLineEntity
    | RawCircleEntity
    | RawArcEntity
    | RawEllipseEntity
    | RawLWPolylineEntity
    | RawPointEntity
    | RawTextEntity
    | RawHatchEntity
    | RawSolidEntity
    | RawInsertEntity
)


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
    "RawEllipseEntity",
    "RawEntity",
    "RawHatchEntity",
    "RawInsertEntity",
    "RawLineEntity",
    "RawLWPolylineEntity",
    "RawPointEntity",
    "RawSolidEntity",
    "RawTextEntity",
    "SceneRect",
]
