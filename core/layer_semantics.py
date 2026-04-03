"""Semantic layer naming helpers derived from the 6-layer rule table."""

from __future__ import annotations

import re


SEMANTIC_ROLE_LABELS: dict[str, str] = {
    "substrate": "Substrate",
    "hole": "Hole",
    "round_feature": "Round Feature",
    "module_region": "Module Region",
    "lead_frame": "Lead Frame",
    "pad": "Pad",
    "die_region": "Die Region",
    "wire": "Wire",
    "die_pad": "Die Pad",
    "bond_point": "Bond Point",
}

SEMANTIC_ROLE_UI_LABELS: dict[str, str] = {
    "substrate": "基板",
    "hole": "孔",
    "round_feature": "圆特征",
    "module_region": "模块区",
    "lead_frame": "引线框",
    "pad": "焊盘",
    "die_region": "芯片区",
    "wire": "金线",
    "die_pad": "焊盘",
    "bond_point": "焊点",
}

INTERNAL_TYPE_ROLE_MAP: dict[str, str] = {
    "substrate": "substrate",
    "hole": "hole",
    "round_feature": "round_feature",
    "lead_frame": "lead_frame",
    "wire": "wire",
    "bond_point": "bond_point",
    "die_pad": "pad",
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
    "01_SUBSTRATE": "substrate",
    "03_LEAD_FRAME": "lead_frame",
    "04_PAD": "die_pad",
    "05_DIE_REGION": "die_pad",
    "06_WIRE": "wire",
}

NUMERIC_LAYER_HINTS: dict[str, tuple[str, set[str]]] = {
    "01": ("substrate", {"SUBSTRATE", "BOARD", "BASE", "CARRIER", "CORE"}),
    "02": ("module_region", {"MODULE", "REGION", "MODULE_REGION", "MODULEAREA"}),
    "03": ("lead_frame", {"LEAD", "FRAME", "LEADFRAME", "LF"}),
    "04": ("pad", {"PAD", "PADS", "LAND", "ELECTRODE"}),
    "05": ("die_region", {"DIE", "DIES", "CHIP", "CHIPS", "DIE_REGION", "CHIP_REGION"}),
    "06": ("wire", {"WIRE", "WIRES", "WIREBOND", "BONDWIRE"}),
}

GENERIC_LAYER_HINTS: tuple[tuple[str, set[str]], ...] = (
    ("substrate", {"SUBSTRATE", "BOARD", "BASE", "CARRIER", "CORE"}),
    ("module_region", {"MODULE", "MODULES", "MODULE_REGION", "REGION"}),
    ("lead_frame", {"LEADFRAME", "LEAD", "FRAME", "LF"}),
    ("pad", {"PAD", "PADS", "LAND", "ELECTRODE"}),
    ("die_region", {"DIE", "DIES", "CHIP", "CHIPS", "DIE_REGION", "CHIP_REGION"}),
    ("wire", {"WIRE", "WIRES", "WIREBOND", "BONDWIRE"}),
    (
        "hole",
        {
            "HOLE",
            "HOLES",
            "MOUNT",
            "MOUNTING",
            "SCREW",
            "DRILL",
            "TOOL",
            "TOOLING",
            "SLOT",
            "SLOTS",
            "OBLONG",
            "LONGHOLE",
            "NPTH",
            "PTH",
        },
    ),
)


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

    tokens = [token for token in normalized.split("_") if token]
    if tokens and tokens[0].isdigit():
        numeric_hint = NUMERIC_LAYER_HINTS.get(tokens[0])
        if numeric_hint is not None:
            role, keywords = numeric_hint
            if any(token in keywords for token in tokens[1:]):
                return role

    for role, keywords in GENERIC_LAYER_HINTS:
        if any(token in keywords for token in tokens):
            return role

    return None


def format_layer_role(role_name: str | None) -> str:
    """Return a short user-facing label for one semantic or internal role name."""

    if not role_name:
        return "-"
    return SEMANTIC_ROLE_LABELS.get(role_name, role_name.replace("_", " ").title())


def format_layer_role_ui(role_name: str | None) -> str:
    """Return a short UI-facing label for one semantic role."""

    if not role_name:
        return "未识别"
    return SEMANTIC_ROLE_UI_LABELS.get(role_name, format_layer_role(role_name))


def mapped_type_to_semantic_role(mapped_type: str | None) -> str | None:
    """Translate one internal import-mapping type into a semantic role."""

    if not mapped_type:
        return None
    return INTERNAL_TYPE_ROLE_MAP.get(str(mapped_type).strip().lower())


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
    "mapped_type_to_semantic_role",
    "RECOMMENDED_IMPORT_MAPPING",
    "RECOMMENDED_LAYER_ROLE_MAP",
    "SEMANTIC_ROLE_LABELS",
    "SEMANTIC_ROLE_UI_LABELS",
    "format_layer_role",
    "format_layer_role_ui",
    "normalize_layer_name",
    "suggest_layer_semantic_role",
]
