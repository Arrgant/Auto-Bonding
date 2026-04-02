"""Core domain and conversion pipeline for Auto-Bonding."""

from .export.coordinates import BondPoint, CoordinateExporter
from .export.wb1_writer import WB1Writer
from .export.wire_extraction import extract_wire_geometries
from .export.xlsm_writer import XLSMWriter
from .export.wire_models import OrderedWireRecord, WireGeometry, WireOrderingConfig, WirePoint
from .export.wire_production_exporter import WireProductionExporter, WireProductionExportResult
from .export.wire_recipe_models import WireRecipeTemplate
from .export.wire_ordering import order_wire_geometries
from .geometry.converter import BondingDiagramConverter, BondingElement, WireLoop
from .parsing.dxf import DXFParser
from .pipeline import (
    build_conversion_artifacts,
    build_drc_report,
    extract_coordinates_from_raw_entities,
    infer_elements_from_raw_entities,
    load_import_preview,
    load_raw_dxf_entities,
    prepare_document,
    prepare_document_from_preview,
)
from .pipeline_types import DRCReport, PreparedDocument, RawImportPreview
from .semantic import (
    RelationNote,
    SemanticCandidate,
    SemanticClassificationResult,
    SemanticEntity,
    classify_semantic_layers,
)
from .validation.drc import DRCChecker, DRCMode, DRCViolation
from .validation.igbt_rules import (
    IGBTPadType,
    IGBTRules,
    IGBT_RULES_AUTOMOTIVE,
    IGBT_RULES_DEFAULT,
    IGBT_RULES_HIGH_VOLTAGE,
    WireType,
)

__all__ = [
    "BondPoint",
    "BondingDiagramConverter",
    "BondingElement",
    "CoordinateExporter",
    "DRCReport",
    "DRCChecker",
    "DRCMode",
    "DRCViolation",
    "DXFParser",
    "IGBTPadType",
    "IGBTRules",
    "IGBT_RULES_AUTOMOTIVE",
    "IGBT_RULES_DEFAULT",
    "IGBT_RULES_HIGH_VOLTAGE",
    "PreparedDocument",
    "RelationNote",
    "RawImportPreview",
    "SemanticCandidate",
    "SemanticClassificationResult",
    "SemanticEntity",
    "OrderedWireRecord",
    "WB1Writer",
    "XLSMWriter",
    "WireProductionExporter",
    "WireProductionExportResult",
    "WireGeometry",
    "WireLoop",
    "WireOrderingConfig",
    "WirePoint",
    "WireRecipeTemplate",
    "WireType",
    "build_conversion_artifacts",
    "build_drc_report",
    "extract_coordinates_from_raw_entities",
    "infer_elements_from_raw_entities",
    "load_import_preview",
    "load_raw_dxf_entities",
    "order_wire_geometries",
    "prepare_document",
    "prepare_document_from_preview",
    "classify_semantic_layers",
    "extract_wire_geometries",
]
