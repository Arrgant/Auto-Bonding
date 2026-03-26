"""Pure check helpers used by the DRC executor."""

from __future__ import annotations

import math
from typing import Any

from .helpers import shape_distance
from .models import DRCViolation


def check_wire_spacing(solids: list[Any], min_wire_spacing: float) -> list[DRCViolation]:
    """Validate minimum spacing between every solid pair."""

    violations: list[DRCViolation] = []

    for i, solid1 in enumerate(solids):
        for j, solid2 in enumerate(solids[i + 1 :], i + 1):
            try:
                distance = shape_distance(solid1, solid2)
                if distance < min_wire_spacing:
                    violations.append(
                        DRCViolation(
                            violation_type="spacing",
                            severity="error",
                            description=f"Wire spacing between solids {i} and {j} is too small.",
                            actual_value=distance,
                            required_value=min_wire_spacing,
                            location=None,
                        )
                    )
            except Exception:
                violations.append(
                    DRCViolation(
                        violation_type="spacing",
                        severity="error",
                        description=f"Unable to measure spacing between solids {i} and {j}; treating as overlap.",
                        actual_value=0.0,
                        required_value=min_wire_spacing,
                        location=None,
                    )
                )

    return violations


def check_loop_height(solids: list[Any], max_loop_height: float) -> list[DRCViolation]:
    """Validate maximum absolute height above the reference plane."""

    violations: list[DRCViolation] = []

    for i, solid in enumerate(solids):
        bbox = solid.BoundingBox()
        height = bbox.zmax
        if height > max_loop_height:
            violations.append(
                DRCViolation(
                    violation_type="height",
                    severity="warning",
                    description=f"Loop height for solid {i} exceeds the configured limit.",
                    actual_value=height,
                    required_value=max_loop_height,
                    location={"z_max": bbox.zmax},
                )
            )

    return violations


def check_standard_pad_size(solids: list[Any], min_pad_size: float) -> list[DRCViolation]:
    """Validate generic pad footprint dimensions."""

    violations: list[DRCViolation] = []

    for i, solid in enumerate(solids):
        bbox = solid.BoundingBox()
        min_dim = min(bbox.xlen, bbox.ylen)
        if min_dim < min_pad_size:
            violations.append(
                DRCViolation(
                    violation_type="pad_size",
                    severity="error",
                    description=f"Pad {i} is below the minimum size.",
                    actual_value=min_dim,
                    required_value=min_pad_size,
                )
            )

    return violations


def check_igbt_pad_size(solids: list[Any], rules: dict[str, Any]) -> list[DRCViolation]:
    """Validate IGBT-specific pad footprint dimensions."""

    violations: list[DRCViolation] = []

    for i, solid in enumerate(solids):
        bbox = solid.BoundingBox()
        min_dim = min(bbox.xlen, bbox.ylen)
        pad_type = getattr(solid, "pad_type", "emitter")
        if pad_type == "emitter" and min_dim < rules.get("min_pad_size_emitter", 0.3):
            violations.append(
                DRCViolation(
                    violation_type="pad_size",
                    severity="error",
                    description=f"Emitter pad {i} is below the minimum size.",
                    actual_value=min_dim,
                    required_value=rules["min_pad_size_emitter"],
                    rule_category="igbt",
                )
            )
        elif pad_type == "collector" and min_dim < rules.get("min_pad_size_collector", 0.5):
            violations.append(
                DRCViolation(
                    violation_type="pad_size",
                    severity="error",
                    description=f"Collector pad {i} is below the minimum size.",
                    actual_value=min_dim,
                    required_value=rules["min_pad_size_collector"],
                    rule_category="igbt",
                )
            )
        elif pad_type == "gate" and min_dim < rules.get("min_pad_size_gate", 0.2):
            violations.append(
                DRCViolation(
                    violation_type="pad_size",
                    severity="warning",
                    description=f"Gate pad {i} is below the recommended size.",
                    actual_value=min_dim,
                    required_value=rules["min_pad_size_gate"],
                    rule_category="igbt",
                )
            )

    return violations


def check_wire_span(elements: list[Any] | None, rules: dict[str, Any]) -> list[DRCViolation]:
    """Validate unsupported span lengths for IGBT-oriented inputs."""

    violations: list[DRCViolation] = []
    if not elements:
        return violations

    for element in elements:
        if element.element_type != "wire":
            continue

        p1 = element.geometry.get("p1", [0, 0, 0])
        p2 = element.geometry.get("p2", [0, 0, 0])
        span = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        wire_type = element.properties.get("wire_type", "al_wire")
        max_span = rules.get("max_ribbon_span" if wire_type == "al_ribbon" else "max_wire_span", 8.0)
        if span > max_span:
            violations.append(
                DRCViolation(
                    violation_type="span",
                    severity="error",
                    description=f"Wire span exceeds limit ({span:.2f}mm); add support or use ribbon.",
                    actual_value=span,
                    required_value=max_span,
                    rule_category="igbt",
                )
            )

    return violations


def check_current_capacity(elements: list[Any] | None, rules: dict[str, Any]) -> list[DRCViolation]:
    """Validate estimated current demand against rough conductor capacity."""

    violations: list[DRCViolation] = []
    if not elements:
        return violations

    for element in elements:
        if element.element_type != "wire":
            continue

        wire_diameter = element.properties.get("wire_diameter", 0.3)
        wire_type = element.properties.get("wire_type", "al_wire")
        expected_current = element.properties.get("expected_current", 0)

        if wire_type == "al_ribbon":
            width = element.properties.get("ribbon_width", 1.0)
            thickness = element.properties.get("ribbon_thickness", 0.1)
            cross_section = width * thickness
            density = rules.get("current_density_al_ribbon", 400.0)
        else:
            cross_section = math.pi * (wire_diameter / 2) ** 2
            density = rules.get("current_density_al_wire", 300.0)

        max_current = cross_section * density
        if expected_current > 0 and expected_current > max_current:
            violations.append(
                DRCViolation(
                    violation_type="current",
                    severity="error",
                    description=f"Current demand exceeds capacity: {expected_current:.1f}A > {max_current:.1f}A",
                    actual_value=expected_current,
                    required_value=max_current,
                    rule_category="electrical",
                )
            )

    return violations


def check_voltage_spacing(elements: list[Any] | None, rules: dict[str, Any]) -> list[DRCViolation]:
    """Validate spacing against the inferred operating voltage class."""

    violations: list[DRCViolation] = []
    if not elements:
        return violations

    operating_voltage = max([element.properties.get("operating_voltage", 0) for element in elements], default=600)
    if operating_voltage <= 100:
        min_spacing = rules.get("min_spacing_low_voltage", 0.5)
    elif operating_voltage <= 600:
        min_spacing = rules.get("min_spacing_medium_voltage", 1.0)
    elif operating_voltage <= 1200:
        min_spacing = rules.get("min_spacing_high_voltage", 2.0)
    else:
        min_spacing = rules.get("min_spacing_ultra_high_voltage", 3.0)

    for i, element1 in enumerate(elements):
        for j, element2 in enumerate(elements[i + 1 :], i + 1):
            if element1.element_type == "wire" and element2.element_type == "wire":
                p1 = element1.geometry.get("p1", [0, 0, 0])
                p2 = element2.geometry.get("p1", [0, 0, 0])
                distance = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if distance < min_spacing:
                    violations.append(
                        DRCViolation(
                            violation_type="voltage_spacing",
                            severity="error",
                            description=(
                                f"Voltage spacing below rule ({operating_voltage}V): "
                                f"{distance:.2f}mm < {min_spacing:.2f}mm"
                            ),
                            actual_value=distance,
                            required_value=min_spacing,
                            rule_category="electrical",
                        )
                    )

    return violations


__all__ = [
    "check_current_capacity",
    "check_igbt_pad_size",
    "check_loop_height",
    "check_standard_pad_size",
    "check_voltage_spacing",
    "check_wire_spacing",
    "check_wire_span",
]
