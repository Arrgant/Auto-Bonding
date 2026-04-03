from __future__ import annotations

from core.layer_semantics import format_layer_role_ui, mapped_type_to_semantic_role, suggest_layer_semantic_role


def test_suggest_layer_semantic_role_supports_common_numeric_aliases():
    assert suggest_layer_semantic_role("05_chip") == "die_region"
    assert suggest_layer_semantic_role("06_wirebond") == "wire"
    assert suggest_layer_semantic_role("03_leadframe_hole") == "lead_frame"


def test_suggest_layer_semantic_role_supports_generic_hole_names_without_number_prefix():
    assert suggest_layer_semantic_role("mount_hole") == "hole"
    assert suggest_layer_semantic_role("tooling_drill") == "hole"
    assert suggest_layer_semantic_role("slot_npth") == "hole"


def test_mapped_type_to_semantic_role_supports_import_layer_fallbacks():
    assert mapped_type_to_semantic_role("die_pad") == "pad"
    assert mapped_type_to_semantic_role("wire") == "wire"
    assert mapped_type_to_semantic_role("unknown") is None


def test_format_layer_role_ui_returns_short_chinese_labels():
    assert format_layer_role_ui("pad") == "焊盘"
    assert format_layer_role_ui("wire") == "金线"
    assert format_layer_role_ui(None) == "未识别"
