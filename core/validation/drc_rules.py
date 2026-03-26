"""Default DRC rule sets and rule resolution helpers."""

from __future__ import annotations

from typing import Any

from .models import DRCMode


IGBT_RULE_DEFAULTS = {
    "min_spacing_low_voltage": 0.5,
    "min_spacing_medium_voltage": 1.0,
    "min_spacing_high_voltage": 2.0,
    "min_spacing_ultra_high_voltage": 3.0,
    "max_loop_height_wire": 3.0,
    "max_loop_height_ribbon": 2.0,
    "min_loop_height": 0.5,
    "min_pad_size_emitter": 0.3,
    "min_pad_size_collector": 0.5,
    "min_pad_size_gate": 0.2,
    "current_density_al_wire": 300.0,
    "current_density_al_ribbon": 400.0,
    "max_wire_span": 8.0,
    "max_ribbon_span": 5.0,
}

STANDARD_RULE_DEFAULTS = {
    "min_wire_spacing": 0.1,
    "max_loop_height": 1.0,
    "min_pad_size": 0.2,
}


def resolve_drc_rules(rules: dict[str, Any] | None, mode: DRCMode) -> dict[str, Any]:
    """Resolve DRC rules for the active validation mode."""

    resolved_rules = rules or {}
    is_igbt = mode in {DRCMode.IGBT, DRCMode.AUTOMOTIVE}

    if not is_igbt:
        return {**STANDARD_RULE_DEFAULTS, **resolved_rules}

    merged = {**IGBT_RULE_DEFAULTS, **resolved_rules}
    merged.setdefault("min_wire_spacing", merged.get("min_spacing_medium_voltage", 1.0))
    merged.setdefault("max_loop_height", merged.get("max_loop_height_wire", 3.0))
    merged.setdefault("min_pad_size", merged.get("min_pad_size_emitter", 0.3))
    return merged


__all__ = ["IGBT_RULE_DEFAULTS", "STANDARD_RULE_DEFAULTS", "resolve_drc_rules"]
