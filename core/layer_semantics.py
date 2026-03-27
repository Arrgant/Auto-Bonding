"""Semantic layer naming helpers derived from the 6-layer rule table."""

from __future__ import annotations

import re


SEMANTIC_ROLE_LABELS: dict[str, str] = {
    "substrate": "Substrate",
    "module_region": "Module Region",
    "lead_frame": "Lead Frame",
    "pad": "Pad",
    "die_region": "Die Region",
    "wire": "Wire",
    "die_pad": "Die Pad",
    "bond_point": "Bond Point",
}

RECOMMENDED_LAYER_ROLE_MAP: dict[str, str] = {
    "01_SUBSTRATE": "substrate",
    "02_MODULE_REGION": "module_region",
    "03_LEAD_FRAME": "lead_frame",
    "04_PAD": "pad",
    "05_DIE_REGION": "die_region",
    "06_WIRE": "wire",
}

# The current converter does not yet implement the full 6-layer semantic model.
# These aliases keep the exact recommended names useful in the existing import
# pipeline without over-promising unsupported behavior.
RECOMMENDED_IMPORT_MAPPING: dict[str, str] = {
    "03_LEAD_FRAME": "lead_frame",
    "04_PAD": "die_pad",
    "05_DIE_REGION": "die_pad",
    "06_WIRE": "wire",
}


def normalize_layer_name(layer_name: str) -> str:
    """Normalize a DXF layer name for semantic matching."""

    return re.sub(r"[^A-Z0-9]+", "_", str(layer_name).strip().upper()).strip("_")


def suggest_layer_semantic_role(layer_name: str) -> str | None:
    """Infer one of the recommended semantic roles from the layer name."""

    normalized = normalize_layer_name(layer_name)
    if not normalized:
        return None

    direct_match = RECOMMENDED_LAYER_ROLE_MAP.get(normalized)
    if direct_match is not None:
        return direct_match

    for prefix, role in RECOMMENDED_LAYER_ROLE_MAP.items():
        if normalized.startswith(prefix):
            return role

    return None


def format_layer_role(role_name: str | None) -> str:
    """Return a short user-facing label for one semantic or internal role name."""

    if not role_name:
        return "-"
    return SEMANTIC_ROLE_LABELS.get(role_name, role_name.replace("_", " ").title())


def apply_layer_role_overrides(
    layer_info: list[dict[str, object]],
    overrides: dict[str, str],
) -> list[dict[str, object]]:
    """Return layer metadata with user-confirmed semantic overrides applied."""

    resolved: list[dict[str, object]] = []
    for layer in layer_info:
        item = dict(layer)
        override = overrides.get(str(layer["name"]))
        if override:
            item["suggested_role"] = override
        resolved.append(item)
    return resolved


__all__ = [
    "apply_layer_role_overrides",
    "RECOMMENDED_IMPORT_MAPPING",
    "RECOMMENDED_LAYER_ROLE_MAP",
    "SEMANTIC_ROLE_LABELS",
    "format_layer_role",
    "normalize_layer_name",
    "suggest_layer_semantic_role",
]
