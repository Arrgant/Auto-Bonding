"""Core domain and conversion pipeline for Auto-Bonding."""

from .export.coordinates import BondPoint, CoordinateExporter
from .geometry.converter import BondingDiagramConverter, BondingElement, WireLoop
from .parsing.dxf import DXFParser
from .pipeline import (
    build_conversion_artifacts,
    build_drc_report,
    extract_coordinates_from_raw_entities,
    infer_elements_from_raw_entities,
    load_raw_dxf_entities,
    prepare_document,
)
from .pipeline_types import DRCReport, PreparedDocument
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
    "WireLoop",
    "WireType",
    "build_conversion_artifacts",
    "build_drc_report",
    "extract_coordinates_from_raw_entities",
    "infer_elements_from_raw_entities",
    "load_raw_dxf_entities",
    "prepare_document",
]
