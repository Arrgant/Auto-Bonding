"""Shared typed payloads used by the conversion pipeline."""

from __future__ import annotations

from collections import Counter
from typing import Any, NotRequired, TypedDict

from .export.coordinates import BondPoint
from .geometry.converter import BondingElement
from .raw_dxf_types import LayerInfo, RawEntity, SceneRect


class DRCReport(TypedDict):
    """Typed report shape returned by DRC helpers."""

    passed: bool
    total_violations: int
    errors: int
    warnings: int
    violations: list[Any]
    info: NotRequired[int]


class RawImportPreview(TypedDict):
    """Typed payload returned by the raw preview stage."""

    raw_entities: list[RawEntity]
    scene_rect: SceneRect
    raw_counts: Counter[str]
    layer_info: list[LayerInfo]
    parser_elements: list[BondingElement]


class PreparedDocument(TypedDict):
    """Typed payload returned by ``prepare_document()``."""

    raw_entities: list[RawEntity]
    scene_rect: SceneRect
    raw_counts: Counter[str]
    layer_info: list[LayerInfo]
    parser_elements: list[BondingElement]
    elements: list[BondingElement]
    converted_counts: Counter[str]
    coordinates: list[BondPoint]
    drc_report: DRCReport
    assembly: Any
    used_fallback: bool
    note: str


__all__ = ["DRCReport", "PreparedDocument", "RawImportPreview"]
