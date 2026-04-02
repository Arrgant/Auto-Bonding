"""DXF parsing helpers for mapping 2D entities into domain elements."""

from __future__ import annotations

from typing import Any

import ezdxf

from ..fallback_helpers import detect_circle_like_profile
from ..hole_rules import classify_substrate_round_feature
from ..geometry.converter import BondingElement
from ..layer_semantics import RECOMMENDED_IMPORT_MAPPING, suggest_layer_semantic_role
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
    **RECOMMENDED_IMPORT_MAPPING,
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
        entities = [
            entity
            for entity in modelspace
            if self.enabled_layers is None or str(entity.dxf.layer) in self.enabled_layers
        ]
        substrate_contexts = self._build_substrate_contexts(entities)
        elements: list[BondingElement] = []

        for entity in entities:
            layer = entity.dxf.layer
            element_type = self._resolve_entity_element_type(entity, substrate_contexts)
            if element_type == "unknown":
                continue

            element = self._parse_entity(entity, element_type, layer)
            if element is not None and element.element_type == "hole":
                element.properties["cut"] = True
            if element is not None:
                elements.append(element)

        return elements

    def _resolve_entity_element_type(
        self,
        entity: Any,
        substrate_contexts: list[dict[str, Any]],
    ) -> str:
        layer = str(entity.dxf.layer)
        base_type = resolve_element_type(layer, self.layer_mapping)
        if base_type not in {"substrate", "unknown", "lead_frame"}:
            return base_type

        context = self._matching_substrate_context(entity, substrate_contexts)
        if context is None:
            return base_type

        entity_id = id(entity)
        if entity_id == context["outline_id"]:
            return "substrate"

        feature_info = self._substrate_round_feature_info(
            entity,
            context["bbox"],
            context["diameter_counts"],
            context["round_profiles"],
        )
        if feature_info is None:
            return base_type

        kind, _contacts = feature_info
        if kind in {"mounting", "tooling"}:
            return "hole"
        return "round_feature"

    def _build_substrate_contexts(self, entities: list[Any]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for entity in entities:
            layer = str(entity.dxf.layer)
            if resolve_element_type(layer, self.layer_mapping) != "substrate":
                continue

            bbox = self._entity_bbox(entity)
            if bbox is None:
                continue
            grouped.setdefault(layer, []).append(
                {
                    "id": id(entity),
                    "entity": entity,
                    "bbox": bbox,
                    "area": max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 0.0),
                }
            )

        contexts: list[dict[str, Any]] = []
        for layer, items in grouped.items():
            if not items:
                continue
            outline = max(items, key=lambda item: item["area"])
            contexts.append(
                {
                    "layer": layer,
                    "outline_id": outline["id"],
                    "bbox": outline["bbox"],
                    "diameter_counts": {},
                    "round_profiles": [],
                }
            )
        for context in contexts:
            round_profiles = self._collect_substrate_round_profiles(
                entities,
                context["outline_id"],
                context["bbox"],
            )
            context["round_profiles"] = round_profiles
            context["diameter_counts"] = self._build_diameter_counts(round_profiles)
        return contexts

    def _collect_substrate_round_profiles(
        self,
        entities: list[Any],
        outline_id: int,
        substrate_bbox: tuple[float, float, float, float],
    ) -> list[dict[str, Any]]:
        profiles: list[dict[str, Any]] = []
        ignored_roles = {"pad", "die_region", "module_region", "wire", "bond_point"}
        for entity in entities:
            if id(entity) == outline_id:
                continue
            role = suggest_layer_semantic_role(str(entity.dxf.layer))
            if role in ignored_roles:
                continue
            bbox = self._entity_bbox(entity)
            if bbox is None or not self._bbox_inside(bbox, substrate_bbox):
                continue
            diameter = self._round_feature_diameter(entity)
            if diameter is not None:
                profiles.append(
                    {
                        "id": id(entity),
                        "diameter": round(diameter, 3),
                        "center": self._bbox_center(bbox),
                    }
                )
        return profiles

    def _build_diameter_counts(self, round_profiles: list[dict[str, Any]]) -> dict[float, int]:
        diameter_values = [float(profile["diameter"]) for profile in round_profiles]
        return {
            diameter: sum(1 for other in diameter_values if abs(other - diameter) <= max(diameter * 0.15, 0.2))
            for diameter in diameter_values
        }

    def _matching_substrate_context(
        self,
        entity: Any,
        substrate_contexts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        feature_bbox = self._entity_bbox(entity)
        if feature_bbox is None:
            return None

        entity_layer = str(entity.dxf.layer)
        if resolve_element_type(entity_layer, self.layer_mapping) == "substrate":
            for context in substrate_contexts:
                if context["layer"] == entity_layer:
                    return context

        containing_contexts = [
            context
            for context in substrate_contexts
            if self._bbox_inside(feature_bbox, context["bbox"])
        ]
        if not containing_contexts:
            return None
        return max(containing_contexts, key=lambda item: self._bbox_area(item["bbox"]))

    def _substrate_round_feature_info(
        self,
        entity: Any,
        substrate_bbox: tuple[float, float, float, float],
        diameter_counts: dict[float, int],
        round_profiles: list[dict[str, Any]],
    ) -> tuple[str, tuple[str, ...]] | None:
        feature_bbox = self._entity_bbox(entity)
        if feature_bbox is None:
            return None
        if not self._bbox_inside(feature_bbox, substrate_bbox):
            return None

        diameter = self._round_feature_diameter(entity)
        if diameter is None:
            return None
        repeated_count = 1
        rounded_diameter = round(diameter, 3)
        for key, value in diameter_counts.items():
            if abs(key - rounded_diameter) <= max(rounded_diameter * 0.15, 0.2):
                repeated_count = max(repeated_count, int(value))
        concentric_count = self._concentric_round_count(entity, round_profiles)
        return classify_substrate_round_feature(
            feature_bbox,
            substrate_bbox,
            repeated_count=repeated_count,
            concentric_count=concentric_count,
        )

    def _entity_bbox(self, entity: Any) -> tuple[float, float, float, float] | None:
        entity_type = entity.dxftype()
        if entity_type == "CIRCLE":
            center = entity.dxf.center
            radius = float(entity.dxf.radius)
            return center.x - radius, center.y - radius, center.x + radius, center.y + radius
        if entity_type == "LWPOLYLINE" and entity.closed:
            points = self._expand_polyline_points(entity)
            if len(points) < 3:
                return None
            x_values = [float(point[0]) for point in points]
            y_values = [float(point[1]) for point in points]
            return min(x_values), min(y_values), max(x_values), max(y_values)
        return None

    def _round_feature_diameter(self, entity: Any) -> float | None:
        entity_type = entity.dxftype()
        if entity_type == "CIRCLE":
            return float(entity.dxf.radius) * 2.0
        if entity_type == "LWPOLYLINE" and entity.closed:
            points = [(float(point[0]), float(point[1])) for point in self._expand_polyline_points(entity)]
            circle_feature = detect_circle_like_profile(points)
            if circle_feature is None:
                if len(points) < 8:
                    return None
                bbox = self._entity_bbox(entity)
                if bbox is None:
                    return None
                width = abs(bbox[2] - bbox[0])
                height = abs(bbox[3] - bbox[1])
                if max(width, height, 1e-6) <= 0:
                    return None
                if abs(width - height) / max(width, height, 1e-6) > 0.20:
                    return None
                return (width + height) / 2.0
            return float(circle_feature[2]) * 2.0
        return None

    def _bbox_inside(
        self,
        inner: tuple[float, float, float, float],
        outer: tuple[float, float, float, float],
    ) -> bool:
        return (
            inner[0] >= outer[0]
            and inner[1] >= outer[1]
            and inner[2] <= outer[2]
            and inner[3] <= outer[3]
        )

    def _bbox_area(self, bbox: tuple[float, float, float, float]) -> float:
        return max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 0.0)

    def _bbox_center(self, bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def _concentric_round_count(self, entity: Any, round_profiles: list[dict[str, Any]]) -> int:
        diameter = self._round_feature_diameter(entity)
        bbox = self._entity_bbox(entity)
        if diameter is None or bbox is None:
            return 1
        center = self._bbox_center(bbox)
        tolerance = max(diameter * 0.08, 0.15)
        count = 0
        for profile in round_profiles:
            other_center = profile["center"]
            if abs(center[0] - other_center[0]) <= tolerance and abs(center[1] - other_center[1]) <= tolerance:
                count += 1
        return max(count, 1)

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
