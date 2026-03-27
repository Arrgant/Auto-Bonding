"""DXF parsing helpers for mapping 2D entities into domain elements."""

from __future__ import annotations

from typing import Any

import ezdxf

from ..geometry.converter import BondingElement
from .dxf_entities import (
    expand_polyline_points,
    parse_dxf_entity,
    resolve_element_type,
    sample_bulge_segment,
)

DEFAULT_LAYER_MAPPING: dict[str, str] = {
    "DIE": "die_pad",
    "PAD": "die_pad",
    "WIRE": "wire",
    "LEAD": "lead_frame",
    "LF": "lead_frame",
    "BOND": "bond_point",
    "FINGER": "lead_frame",
}


class DXFParser:
    """Parse DXF entities into bonding domain elements based on layer mapping."""

    def __init__(
        self,
        layer_mapping: dict[str, str] | None = None,
        enabled_layers: set[str] | None = None,
    ):
        self.layer_mapping = dict(DEFAULT_LAYER_MAPPING)
        if layer_mapping:
            self.layer_mapping.update({str(name).upper(): value for name, value in layer_mapping.items()})
        self.enabled_layers = {str(name) for name in enabled_layers} if enabled_layers is not None else None

    def parse_file(self, file_path: str) -> list[BondingElement]:
        """Parse a DXF file and return mapped bonding elements."""

        document = ezdxf.readfile(file_path)
        return self.parse_document(document)

    def parse_document(self, document: ezdxf.document.Drawing) -> list[BondingElement]:
        """Parse an already-open DXF document and return mapped bonding elements."""

        modelspace = document.modelspace()
        elements: list[BondingElement] = []

        for entity in modelspace:
            layer = entity.dxf.layer
            if self.enabled_layers is not None and str(layer) not in self.enabled_layers:
                continue
            element_type = resolve_element_type(layer, self.layer_mapping)
            if element_type == "unknown":
                continue

            element = self._parse_entity(entity, element_type, layer)
            if element is not None:
                elements.append(element)

        return elements

    def _parse_entity(self, entity: Any, element_type: str, layer: str) -> BondingElement | None:
        """Dispatch DXF entity parsing by entity type."""

        return parse_dxf_entity(entity, element_type, layer)

    def _expand_polyline_points(self, entity: Any) -> list[list[float]]:
        """Expand polyline vertices into sampled XY points, preserving bulge arcs."""

        return expand_polyline_points(entity)

    def _sample_bulge_segment(
        self,
        start_point: tuple[float, float],
        end_point: tuple[float, float],
        bulge: float,
    ) -> list[list[float]]:
        """Sample a bulge segment into intermediate points."""

        return sample_bulge_segment(start_point, end_point, bulge)
