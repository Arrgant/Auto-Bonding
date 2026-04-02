from __future__ import annotations

from ui.wire_export_dialog import merge_rx2000_common_pfile_fields


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
