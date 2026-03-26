"""IGBT-specific validation presets and helper rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IGBTPadType(Enum):
    """Pad roles commonly used in IGBT packages."""

    EMITTER = "emitter"
    COLLECTOR = "collector"
    GATE = "gate"
    SENSE = "sense"
    DUMMY = "dummy"


class WireType(Enum):
    """Supported IGBT conductor types."""

    AL_WIRE = "al_wire"
    AL_RIBBON = "al_ribbon"
    CU_WIRE = "cu_wire"
    AU_WIRE = "au_wire"


@dataclass
class IGBTRules:
    """Rule bundle for IGBT-specific spacing, pad, and conductor checks."""

    min_spacing_low_voltage: float = 0.5
    min_spacing_medium_voltage: float = 1.0
    min_spacing_high_voltage: float = 2.0
    min_spacing_ultra_high_voltage: float = 3.0

    voltage_threshold_low: float = 100.0
    voltage_threshold_medium: float = 600.0
    voltage_threshold_high: float = 1200.0

    loop_height_coefficient_al_wire: float = 2.0
    loop_height_coefficient_al_ribbon: float = 1.5
    loop_height_coefficient_cu_wire: float = 1.8

    max_loop_height_wire: float = 3.0
    max_loop_height_ribbon: float = 2.0
    min_loop_height: float = 0.5

    min_pad_size_emitter: float = 0.3
    min_pad_size_collector: float = 0.5
    min_pad_size_gate: float = 0.2

    min_pad_spacing_same_net: float = 0.3
    min_pad_spacing_diff_net: float = 0.8

    standard_wire_diameters: list[float] = field(
        default_factory=lambda: [0.100, 0.150, 0.200, 0.250, 0.300, 0.375, 0.400, 0.500]
    )
    standard_ribbon_sizes: list[tuple[float, float]] = field(
        default_factory=lambda: [
            (0.5, 0.05),
            (1.0, 0.075),
            (1.5, 0.10),
            (2.0, 0.125),
            (2.5, 0.15),
            (3.0, 0.20),
        ]
    )

    max_wire_span: float = 8.0
    max_ribbon_span: float = 5.0

    current_density_al_wire: float = 300.0
    current_density_al_ribbon: float = 400.0
    current_density_cu_wire: float = 500.0
    current_density_au_wire: float = 200.0

    max_temperature_rise: float = 50.0

    min_bond_strength_wire: float = 50.0
    min_bond_strength_ribbon: float = 200.0

    fatigue_factor_al: float = 1.0
    fatigue_factor_cu: float = 1.2
    fatigue_factor_au: float = 0.8

    cte_aluminum: float = 23.0
    cte_copper: float = 17.0
    cte_gold: float = 14.0
    cte_silicon: float = 2.6
    cte_al2o3: float = 7.0
    max_cte_mismatch: float = 15.0

    def get_min_spacing_for_voltage(self, voltage: float) -> float:
        """Return the spacing requirement for the given operating voltage."""

        if voltage <= self.voltage_threshold_low:
            return self.min_spacing_low_voltage
        if voltage <= self.voltage_threshold_medium:
            return self.min_spacing_medium_voltage
        if voltage <= self.voltage_threshold_high:
            return self.min_spacing_high_voltage
        return self.min_spacing_ultra_high_voltage

    def get_current_capacity(self, wire_diameter: float, wire_type: WireType) -> float:
        """Estimate current capacity from cross section and conductor density."""

        cross_section = 3.14159 * (wire_diameter / 2) ** 2

        if wire_type == WireType.AL_WIRE:
            density = self.current_density_al_wire
        elif wire_type == WireType.AL_RIBBON:
            density = self.current_density_al_ribbon
        elif wire_type == WireType.CU_WIRE:
            density = self.current_density_cu_wire
        else:
            density = self.current_density_au_wire

        return cross_section * density

    def get_loop_height_coefficient(self, wire_type: WireType) -> float:
        """Return the loop-height coefficient for the conductor type."""

        if wire_type == WireType.AL_WIRE:
            return self.loop_height_coefficient_al_wire
        if wire_type == WireType.AL_RIBBON:
            return self.loop_height_coefficient_al_ribbon
        if wire_type == WireType.CU_WIRE:
            return self.loop_height_coefficient_cu_wire
        return 1.5

    def validate_pad_type(self, pad_type: IGBTPadType, pad_size: float) -> list[str]:
        """Return messages when the pad is smaller than the configured minimum."""

        violations: list[str] = []

        if pad_type == IGBTPadType.EMITTER and pad_size < self.min_pad_size_emitter:
            violations.append(
                f"Emitter pad size {pad_size:.3f}mm < minimum {self.min_pad_size_emitter:.3f}mm"
            )
        elif pad_type == IGBTPadType.COLLECTOR and pad_size < self.min_pad_size_collector:
            violations.append(
                f"Collector pad size {pad_size:.3f}mm < minimum {self.min_pad_size_collector:.3f}mm"
            )
        elif pad_type == IGBTPadType.GATE and pad_size < self.min_pad_size_gate:
            violations.append(
                f"Gate pad size {pad_size:.3f}mm < minimum {self.min_pad_size_gate:.3f}mm"
            )

        return violations


IGBT_RULES_DEFAULT = IGBTRules()

IGBT_RULES_HIGH_VOLTAGE = IGBTRules(
    min_spacing_high_voltage=2.5,
    min_spacing_ultra_high_voltage=4.0,
    max_loop_height_wire=4.0,
)

IGBT_RULES_AUTOMOTIVE = IGBTRules(
    min_spacing_medium_voltage=1.2,
    min_spacing_high_voltage=2.2,
    fatigue_factor_al=1.2,
    max_temperature_rise=40.0,
)


__all__ = [
    "IGBTPadType",
    "IGBTRules",
    "IGBT_RULES_AUTOMOTIVE",
    "IGBT_RULES_DEFAULT",
    "IGBT_RULES_HIGH_VOLTAGE",
    "WireType",
]
