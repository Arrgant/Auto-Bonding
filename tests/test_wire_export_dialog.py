from __future__ import annotations

from core.export import extract_wire_geometries_with_audit
from core.export.wire_models import WireOrderingConfig
from core.export.wire_recipe_models import WireRecipeTemplate
from ui.wire_export_dialog import (
    build_template_health_text,
    build_wire_extraction_health_text,
    format_preview_point,
    merge_rx2000_common_pfile_fields,
)


def test_merge_rx2000_common_pfile_fields_overlays_form_values_and_seeds_field_map():
    named_defaults = {"custom_value": 7, "search_force": 10}
    field_map = {"custom_value": "Z1"}
    field_values = {"search_force": 25.0, "h1_cutter": 1170.0}
    default_field_map = {"search_force": "A8", "h1_cutter": "A10"}

    merged_named_defaults, merged_field_map = merge_rx2000_common_pfile_fields(
        named_defaults,
        field_map,
        field_values,
        default_field_map,
    )

    assert merged_named_defaults["custom_value"] == 7
    assert merged_named_defaults["search_force"] == 25
    assert merged_named_defaults["h1_cutter"] == 1170
    assert merged_field_map["custom_value"] == "Z1"
    assert merged_field_map["search_force"] == "A8"
    assert merged_field_map["h1_cutter"] == "A10"


def test_format_preview_point_uses_default_z_only_when_point_z_is_missing():
    assert format_preview_point(1.0, 2.0, None, 7.5) == "1.000, 2.000, 7.500"
    assert format_preview_point(1.0, 2.0, 0.0, 7.5) == "1.000, 2.000, 0.000"


def test_build_template_health_text_summarizes_current_wb1_export_mode():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        ordering=WireOrderingConfig(group_mode="clustered"),
        bond_angle_mode="wire_vector",
        wb1_field_map={
            "role_code": 0,
            "bond_x": 38,
            "bond_y": 40,
            "group_no": 19,
            "bond_z": 42,
            "camera_x": 32,
            "camera_y": 34,
            "camera_z": 36,
        },
    )

    text = build_template_health_text(template)

    assert "Missing required WB1 J fields: bond_angle." in text
    assert "Current DXF-driven J fields: role_code, bond_x, bond_y, group_no." in text
    assert "bond_z uses explicit point Z when available, otherwise template default_z." in text
    assert "camera_x/y/z currently export as 0 until camera calibration is modeled." in text


def test_build_wire_extraction_health_text_reports_missing_and_partial_extraction_states():
    _, no_layer_audit = extract_wire_geometries_with_audit(
        [{"type": "LINE", "start": (0.0, 0.0), "end": (1.0, 0.0), "layer": "06_wire"}],
        [{"name": "06_wire", "mapped_type": None, "suggested_role": None}],
    )
    assert build_wire_extraction_health_text(no_layer_audit) == "No wire-semantic layers are mapped yet."

    _wires, audit = extract_wire_geometries_with_audit(
        [
            {"type": "LINE", "start": (0.0, 0.0), "end": (1.0, 0.0), "layer": "06_wire"},
            {"type": "POINT", "location": (2.0, 2.0), "layer": "06_wire"},
            {"type": "LINE", "start": (1.0, 0.0), "end": (2.0, 0.0), "layer": "06_wire"},
        ],
        [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}],
    )

    text = build_wire_extraction_health_text(audit)

    assert "Wire extraction: 2/3 candidate entities converted from 06_wire." in text
    assert "Skipped wire-layer entities: unsupported_entity_type=1." in text
    assert "Skipped examples: #1 POINT unsupported_entity_type." in text
    assert "Potential split-wire joins: 1 endpoint pair(s)." in text
    assert "Join examples: W0001(second) <-> W0003(first) @ (1.000, 0.000) [continuous]." in text
    assert "Merge suggestions: W0001->W0003 join_as_is reverse=none." in text


def test_build_wire_extraction_health_text_marks_same_role_direction_conflicts():
    _wires, audit = extract_wire_geometries_with_audit(
        [
            {"type": "LINE", "start": (0.0, 0.0), "end": (1.0, 0.0), "layer": "06_wire"},
            {"type": "LINE", "start": (2.0, 0.0), "end": (1.0, 0.0), "layer": "06_wire"},
        ],
        [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}],
    )

    text = build_wire_extraction_health_text(audit)

    assert "Direction conflicts at shared endpoints: 1 pair(s)." in text
    assert "Join examples: W0001(second) <-> W0002(second) @ (1.000, 0.000) [same_role_conflict]." in text
    assert "Merge suggestions: W0001->W0002 reverse_second_then_join reverse=W0002." in text
