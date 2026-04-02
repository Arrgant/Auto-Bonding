from __future__ import annotations

from core.export.wb1_field_sources import (
    RX2000_WB1_FIELD_SOURCES,
    rx2000_fields_available_from_dxf,
    rx2000_fields_currently_written_from_dxf,
)
from core.export.wire_recipe_defaults import RX2000_STARTER_WB1_FIELD_MAP


def test_rx2000_field_source_map_covers_every_known_j_field():
    assert set(RX2000_WB1_FIELD_SOURCES) == set(RX2000_STARTER_WB1_FIELD_MAP)


def test_rx2000_dxf_field_classification_matches_current_plan():
    assert rx2000_fields_available_from_dxf() == (
        "role_code",
        "group_no",
        "bond_x",
        "bond_y",
        "bond_z",
        "bond_angle",
    )
    assert rx2000_fields_currently_written_from_dxf() == (
        "role_code",
        "bond_x",
        "bond_y",
    )


def test_rx2000_selected_field_sources_capture_current_behavior():
    assert RX2000_WB1_FIELD_SOURCES["bond_x"].dxf_availability == "direct"
    assert RX2000_WB1_FIELD_SOURCES["bond_x"].current_from_dxf is True

    assert RX2000_WB1_FIELD_SOURCES["group_no"].dxf_availability == "derived"
    assert RX2000_WB1_FIELD_SOURCES["group_no"].current_from_dxf is False

    assert RX2000_WB1_FIELD_SOURCES["bond_z"].dxf_availability == "3d_only"
    assert RX2000_WB1_FIELD_SOURCES["bond_z"].current_source == "default_z fallback"

    assert RX2000_WB1_FIELD_SOURCES["camera_x"].dxf_availability == "no"
    assert RX2000_WB1_FIELD_SOURCES["camera_x"].current_source == "hardcoded zero / future transform"

    assert RX2000_WB1_FIELD_SOURCES["bond_angle"].dxf_availability == "derived"
    assert RX2000_WB1_FIELD_SOURCES["bond_angle"].current_from_dxf is False
