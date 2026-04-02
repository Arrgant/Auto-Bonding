from __future__ import annotations

from core.layer_semantics import suggest_layer_semantic_role


def test_suggest_layer_semantic_role_supports_common_numeric_aliases():
    assert suggest_layer_semantic_role("05_chip") == "die_region"
    assert suggest_layer_semantic_role("06_wirebond") == "wire"
    assert suggest_layer_semantic_role("03_leadframe_hole") == "lead_frame"


def test_suggest_layer_semantic_role_supports_generic_hole_names_without_number_prefix():
    assert suggest_layer_semantic_role("mount_hole") == "hole"
    assert suggest_layer_semantic_role("tooling_drill") == "hole"
    assert suggest_layer_semantic_role("slot_npth") == "hole"
