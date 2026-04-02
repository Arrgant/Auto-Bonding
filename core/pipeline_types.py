"""Shared typed payloads used by the conversion pipeline."""

from __future__ import annotations

from collections import Counter
from typing import Any, NotRequired, TypedDict

from .export.coordinates import BondPoint
from .export.wire_models import WireGeometry
from .geometry.converter import BondingElement
from .raw_dxf_types import LayerInfo, RawEntity, SceneRect
from .semantic import SemanticClassificationResult


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
    semantic_result: SemanticClassificationResult
    wire_geometries: list[WireGeometry]


class LayerMeshPayload(TypedDict):
    """Typed mesh payload for one preview layer."""

    layer_name: str
    color_hex: str
    mesh_bytes: Any
    vertex_count: int
    diagonal: float


class PreparedDocument(TypedDict):
    """Typed payload returned by ``prepare_document()``."""

    raw_entities: list[RawEntity]
    scene_rect: SceneRect
    raw_counts: Counter[str]
    layer_info: list[LayerInfo]
    parser_elements: list[BondingElement]
    semantic_result: SemanticClassificationResult
    elements: list[BondingElement]
    converted_counts: Counter[str]
    coordinates: list[BondPoint]
    wire_geometries: list[WireGeometry]
    drc_report: DRCReport
    assembly: Any
    layer_meshes: NotRequired[list[LayerMeshPayload]]
    mesh_bytes: NotRequired[Any]
    mesh_vertex_count: NotRequired[int]
    mesh_diagonal: NotRequired[float]
    used_fallback: bool
    note: str


__all__ = ["DRCReport", "LayerMeshPayload", "PreparedDocument", "RawImportPreview"]
