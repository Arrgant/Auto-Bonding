"""Internal helpers for geometry conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import cadquery as cq
import numpy as np


@dataclass(frozen=True)
class ConverterSettings:
    """Resolved converter mode settings and material defaults."""

    mode: str
    is_igbt: bool
    loop_height_coefficient: float
    default_wire_diameter: float
    default_material: str
    wire_type: str
    material_coefficients: dict[str, float]

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "ConverterSettings":
        mode = str(config.get("mode", "standard"))
        is_igbt = mode in {"igbt", "automotive"}

        if is_igbt:
            loop_height_coefficient = float(config.get("loop_height_coefficient", 2.0))
            default_wire_diameter = float(config.get("default_wire_diameter", 0.3))
            default_material = str(config.get("default_material", "aluminum"))
            wire_type = str(config.get("wire_type", "al_wire"))
        else:
            loop_height_coefficient = float(config.get("loop_height_coefficient", 1.5))
            default_wire_diameter = float(config.get("default_wire_diameter", 0.025))
            default_material = str(config.get("default_material", "gold"))
            wire_type = "au_wire"

        material_coefficients = {
            "gold": 1.5,
            "copper": 1.2,
            "aluminum": 1.8,
            "silver": 1.4,
        }
        if is_igbt:
            material_coefficients["aluminum"] = 2.0
            if mode == "automotive":
                material_coefficients["aluminum"] *= 1.2

        return cls(
            mode=mode,
            is_igbt=is_igbt,
            loop_height_coefficient=loop_height_coefficient,
            default_wire_diameter=default_wire_diameter,
            default_material=default_material,
            wire_type=wire_type,
            material_coefficients=material_coefficients,
        )


@dataclass(frozen=True)
class WireElementSpec:
    """Normalized wire conversion inputs."""

    start: list[float]
    end: list[float]
    loop_height: float
    wire_diameter: float
    material: str


@dataclass(frozen=True)
class DiePadSpec:
    """Normalized die-pad conversion inputs."""

    x: float
    y: float
    z: float
    width: float
    height: float
    thickness: float
    radius: float | None


@dataclass(frozen=True)
class LeadFrameSpec:
    """Normalized lead-frame conversion inputs."""

    points: list[cq.Vector]
    width: float
    thickness: float


def resolve_wire_element_spec(
    geometry: dict[str, Any],
    properties: dict[str, Any],
    default_wire_diameter: float,
    default_material: str,
    loop_height_resolver: Callable[[float, float, str], float],
) -> WireElementSpec:
    """Resolve wire geometry and defaults into a stable spec."""

    start = list(geometry.get("p1", [0, 0, 0]))
    end = list(geometry.get("p2", [5, 0, 0]))
    wire_diameter = float(properties.get("wire_diameter", default_wire_diameter))
    material = str(properties.get("material", default_material))
    span = float(np.hypot(end[0] - start[0], end[1] - start[1])) or 5.0
    loop_height = float(
        properties.get(
            "loop_height",
            loop_height_resolver(span, default_wire_diameter, default_material),
        )
    )
    return WireElementSpec(
        start=start,
        end=end,
        loop_height=loop_height,
        wire_diameter=wire_diameter,
        material=material,
    )


def resolve_die_pad_spec(geometry: dict[str, Any], properties: dict[str, Any]) -> DiePadSpec:
    """Resolve die-pad geometry and defaults into a stable spec."""

    center = geometry.get("center", [0.0, 0.0, 0.0])
    radius = geometry.get("radius")
    return DiePadSpec(
        x=float(geometry.get("x", center[0] if len(center) > 0 else 0.0)),
        y=float(geometry.get("y", center[1] if len(center) > 1 else 0.0)),
        z=float(geometry.get("z", center[2] if len(center) > 2 else 0.0)),
        width=float(geometry.get("width", (radius * 2.0) if radius else 1.0)),
        height=float(geometry.get("height", (radius * 2.0) if radius else 1.0)),
        thickness=float(properties.get("thickness", 0.1)),
        radius=float(radius) if radius is not None else None,
    )


def resolve_lead_frame_spec(geometry: dict[str, Any], properties: dict[str, Any]) -> LeadFrameSpec:
    """Resolve lead-frame geometry and defaults into a stable spec."""

    return LeadFrameSpec(
        points=[cq.Vector(point) for point in geometry.get("points", [])],
        width=float(properties.get("width", 0.5)),
        thickness=float(properties.get("thickness", 0.1)),
    )


__all__ = [
    "ConverterSettings",
    "DiePadSpec",
    "LeadFrameSpec",
    "WireElementSpec",
    "resolve_die_pad_spec",
    "resolve_lead_frame_spec",
    "resolve_wire_element_spec",
]
