"""Shared DXF-to-model pipeline helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .export.coordinates import CoordinateExporter
from .fallback import infer_elements_from_raw_entities
from .geometry.converter import BondingDiagramConverter, BondingElement
from .parsing.dxf import DXFParser
from .pipeline_types import DRCReport, PreparedDocument
from .raw_dxf import extract_coordinates_from_raw_entities, load_raw_dxf_entities
from .validation.drc import DRCChecker, DRCMode
from .validation.helpers import build_violation_report


def _mode_to_drc(mode_name: str) -> DRCMode:
    mapping = {
        "standard": DRCMode.STANDARD,
        "igbt": DRCMode.IGBT,
        "automotive": DRCMode.AUTOMOTIVE,
    }
    return mapping.get(mode_name, DRCMode.STANDARD)


def build_conversion_artifacts(file_path: Path, config: dict[str, Any]) -> tuple[list[BondingElement], Any, bool]:
    parser = DXFParser()
    converter = BondingDiagramConverter(config)
    parser_elements = parser.parse_file(str(file_path))
    used_fallback = False

    if parser_elements:
        elements = parser_elements
    else:
        raw_entities, _, _, _ = load_raw_dxf_entities(file_path, parser.layer_mapping)
        elements = infer_elements_from_raw_entities(raw_entities, config)
        used_fallback = True

    assembly = converter.convert_elements(elements)
    return elements, assembly, used_fallback


def build_drc_report(checker: DRCChecker, assembly: Any, elements: list[BondingElement]) -> DRCReport:
    violations = checker.check_all(assembly, elements)
    return build_violation_report(violations, include_info=True)


def prepare_document(file_path: Path, config: dict[str, Any]) -> PreparedDocument:
    parser = DXFParser()
    raw_entities, scene_rect, raw_counts, layer_info = load_raw_dxf_entities(file_path, parser.layer_mapping)
    parser_elements = parser.parse_file(str(file_path))
    converter = BondingDiagramConverter(config)
    exporter = CoordinateExporter()

    used_fallback = False
    if parser_elements:
        elements = parser_elements
    else:
        elements = infer_elements_from_raw_entities(raw_entities, config)
        used_fallback = True

    assembly = converter.convert_elements(elements)

    coordinates = exporter.extract_bond_points(assembly)
    if len(coordinates) <= 2:
        coordinates = extract_coordinates_from_raw_entities(raw_entities)

    checker = DRCChecker(mode=_mode_to_drc(str(config.get("mode", "standard"))))
    drc_report = build_drc_report(checker, assembly, elements)
    populated_layers = [layer for layer in layer_info if layer.get("entity_count", 0) > 0]
    mapped_layers = [layer for layer in populated_layers if layer.get("mapped_type")]
    if used_fallback:
        note = (
            f"Detected {len(populated_layers)} populated layers, "
            f"but none matched the bonding layer mapping; used simplified geometric fallback."
        )
    else:
        note = (
            f"Parsed DXF with {len(mapped_layers)} mapped layers "
            f"across {len(populated_layers)} populated layers."
        )

    return {
        "raw_entities": raw_entities,
        "scene_rect": scene_rect,
        "raw_counts": raw_counts,
        "layer_info": layer_info,
        "parser_elements": parser_elements,
        "elements": elements,
        "converted_counts": Counter(element.element_type for element in elements),
        "coordinates": coordinates,
        "drc_report": drc_report,
        "assembly": assembly,
        "used_fallback": used_fallback,
        "note": note,
    }
