"""
Core 2D to 3D conversion helpers for Auto-Bonding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import cadquery as cq
import numpy as np

from .converter_helpers import (
    ConverterSettings,
    resolve_die_pad_spec,
    resolve_hole_spec,
    resolve_lead_frame_spec,
    resolve_substrate_spec,
    resolve_wire_element_spec,
)


@dataclass
class BondingElement:
    element_type: str
    layer: str
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


@dataclass
class WireLoop:
    p1: cq.Vector
    p2: cq.Vector
    loop_height: float
    wire_diameter: float
    material: str


class BondingDiagramConverter:
    IGBT_MODES = ["standard", "igbt", "automotive"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        settings = ConverterSettings.from_mapping(self.config)
        self.mode = settings.mode
        self.is_igbt = settings.is_igbt
        self.loop_height_coefficient = settings.loop_height_coefficient
        self.default_wire_diameter = settings.default_wire_diameter
        self.default_material = settings.default_material
        self.wire_type = settings.wire_type
        self.material_coefficients = settings.material_coefficients

    def calculate_loop_height(self, span: float, wire_diameter: float, material: str) -> float:
        factor = self.material_coefficients.get(material, self.loop_height_coefficient)
        return float(factor * np.sqrt(span * wire_diameter))

    def create_wire_loop(self, wire: WireLoop) -> cq.Workplane:
        dx = wire.p2.x - wire.p1.x
        dy = wire.p2.y - wire.p1.y
        span_2d = float(np.hypot(dx, dy))

        if span_2d <= 1e-9:
            return cq.Workplane("XY")

        mid_point = (wire.p1 + wire.p2) / 2
        perpendicular = cq.Vector(-dy / span_2d, dx / span_2d, 0)
        lateral_offset = max(wire.loop_height, wire.wire_diameter * 4)
        arc_control = mid_point + (perpendicular * lateral_offset)

        try:
            wire_path = (
                cq.Workplane("XY")
                .moveTo(wire.p1.x, wire.p1.y)
                .threePointArc((arc_control.x, arc_control.y), (wire.p2.x, wire.p2.y))
            )
        except Exception:
            wire_path = (
                cq.Workplane("XY")
                .moveTo(wire.p1.x, wire.p1.y)
                .lineTo(wire.p2.x, wire.p2.y)
            )

        if wire.wire_diameter <= 0:
            return wire_path

        try:
            profile = cq.Workplane("XY").circle(wire.wire_diameter / 2)
            return wire_path.wire().sweep(profile)
        except Exception:
            return wire_path

    def create_die_pad(
        self,
        x: float,
        y: float,
        z: float,
        width: float,
        height: float,
        thickness: float,
        radius: float | None = None,
    ) -> cq.Workplane:
        del z
        if radius is not None and radius > 0:
            return cq.Workplane("XY").center(x, y).circle(radius).extrude(thickness)
        return cq.Workplane("XY").center(x, y).rect(width, height).extrude(thickness)

    def create_lead_frame(self, points: List[cq.Vector], width: float, thickness: float) -> cq.Workplane:
        if len(points) < 2:
            return cq.Workplane("XY")

        path = cq.Workplane("XY").moveTo(points[0].x, points[0].y)
        for point in points[1:]:
            path = path.lineTo(point.x, point.y)

        try:
            profile = cq.Workplane("XY").rect(width, thickness)
            return path.wire().sweep(profile)
        except Exception:
            return path

    def create_substrate(
        self,
        *,
        points: list[tuple[float, float]] | None,
        center: tuple[float, float, float] | None,
        radius: float | None,
        thickness: float,
    ) -> cq.Workplane:
        if points:
            profile = cq.Workplane("XY").polyline(points).close().extrude(thickness)
            return profile
        if center is not None and radius is not None and radius > 0:
            return cq.Workplane("XY").center(center[0], center[1]).circle(radius).extrude(thickness)
        return cq.Workplane("XY")

    def create_hole_tool(self, center: tuple[float, float, float], radius: float, depth: float) -> cq.Workplane:
        if radius <= 0 or depth <= 0:
            return cq.Workplane("XY")
        tool = cq.Workplane("XY").center(center[0], center[1]).circle(radius).extrude(depth * 2.0)
        return tool.translate((0.0, 0.0, center[2] - depth * 0.5))

    def _append_element(self, assembly: cq.Assembly, element: BondingElement) -> None:
        if element.element_type == "wire":
            wire_spec = resolve_wire_element_spec(
                element.geometry,
                element.properties,
                self.default_wire_diameter,
                self.default_material,
                self.calculate_loop_height,
            )
            wire = WireLoop(
                p1=cq.Vector(wire_spec.start),
                p2=cq.Vector(wire_spec.end),
                loop_height=wire_spec.loop_height,
                wire_diameter=wire_spec.wire_diameter,
                material=wire_spec.material,
            )
            assembly.add(
                self.create_wire_loop(wire),
                name=f"wire_{len(assembly.objects)}",
                metadata={"layer": element.layer, "element_type": element.element_type},
            )
        elif element.element_type == "substrate":
            substrate_spec = resolve_substrate_spec(element.geometry, element.properties)
            assembly.add(
                self.create_substrate(
                    points=substrate_spec.points,
                    center=substrate_spec.center,
                    radius=substrate_spec.radius,
                    thickness=substrate_spec.thickness,
                ),
                name=f"substrate_{len(assembly.objects)}",
                metadata={"layer": element.layer, "element_type": element.element_type},
            )
        elif element.element_type in {"die_pad", "round_feature"}:
            pad_spec = resolve_die_pad_spec(element.geometry, element.properties)
            assembly.add(
                self.create_die_pad(
                    x=pad_spec.x,
                    y=pad_spec.y,
                    z=pad_spec.z,
                    width=pad_spec.width,
                    height=pad_spec.height,
                    thickness=pad_spec.thickness,
                    radius=pad_spec.radius,
                ),
                name=f"{element.element_type}_{len(assembly.objects)}",
                metadata={"layer": element.layer, "element_type": element.element_type},
            )
        elif element.element_type == "lead_frame":
            lead_frame_spec = resolve_lead_frame_spec(element.geometry, element.properties)
            assembly.add(
                self.create_lead_frame(
                    points=lead_frame_spec.points,
                    width=lead_frame_spec.width,
                    thickness=lead_frame_spec.thickness,
                ),
                name=f"lead_frame_{len(assembly.objects)}",
                metadata={"layer": element.layer, "element_type": element.element_type},
            )

    def append_elements(self, assembly: cq.Assembly, elements: List[BondingElement]) -> cq.Assembly:
        """Append converted elements into an existing assembly."""

        substrates = [element for element in elements if element.element_type == "substrate"]
        holes = [element for element in elements if element.element_type == "hole"]
        others = [element for element in elements if element.element_type not in {"substrate", "hole"}]

        hole_tools = []
        for element in holes:
            if not bool(element.properties.get("cut", False)):
                continue
            hole_spec = resolve_hole_spec(element.geometry, element.properties)
            tool = self.create_hole_tool(hole_spec.center, hole_spec.radius, hole_spec.depth)
            if tool.val() is not None:
                hole_tools.append((element, tool))

        for element in substrates:
            substrate_spec = resolve_substrate_spec(element.geometry, element.properties)
            solid = self.create_substrate(
                points=substrate_spec.points,
                center=substrate_spec.center,
                radius=substrate_spec.radius,
                thickness=substrate_spec.thickness,
            )
            substrate_bbox = solid.val().BoundingBox() if solid.val() is not None else None
            if substrate_bbox is not None:
                for hole_element, tool in hole_tools:
                    hole_spec = resolve_hole_spec(hole_element.geometry, hole_element.properties)
                    if (
                        substrate_bbox.xmin <= hole_spec.center[0] <= substrate_bbox.xmax
                        and substrate_bbox.ymin <= hole_spec.center[1] <= substrate_bbox.ymax
                    ):
                        try:
                            solid = solid.cut(tool)
                        except Exception:
                            pass
            assembly.add(
                solid,
                name=f"substrate_{len(assembly.objects)}",
                metadata={"layer": element.layer, "element_type": element.element_type},
            )

        for element in others:
            self._append_element(assembly, element)

        return assembly

    def convert_elements(self, elements: List[BondingElement]) -> cq.Assembly:
        assembly = cq.Assembly()
        return self.append_elements(assembly, elements)

    def export_step(self, assembly: cq.Assembly, output_path: str) -> bool:
        try:
            if hasattr(assembly, "toCompound"):
                cq.exporters.export(assembly.toCompound(), output_path)
            elif hasattr(assembly, "save"):
                assembly.save(output_path)
            else:
                cq.exporters.export(assembly, output_path)
            return True
        except Exception as exc:
            print(f"STEP export failed: {exc}")
            return False

    def convert_file(self, input_path: str, output_path: str) -> bool:
        print(f"Convert file: {input_path} -> {output_path}")
        return True
