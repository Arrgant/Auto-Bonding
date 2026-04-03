from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.export import extract_wire_geometries_with_audit
from core.export.wire_models import WireGeometry, WireOrderingConfig, WirePoint
from core.export.wire_recipe_models import WireRecipeTemplate
from services import ProjectDocument, WireRecipeTemplateStore
from ui.wire_export_dialog import (
    build_template_health_text,
    build_wire_extraction_health_text,
    compact_path_text,
    format_count_label,
    format_preview_point,
    format_preview_point_tooltip,
    format_preview_xy_lines,
    merge_rx2000_common_pfile_fields,
    WireExportDialog,
)


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _wire_geometry(wire_id: str, first_xy: tuple[float, float], second_xy: tuple[float, float], *, group_hint: str) -> WireGeometry:
    first_point = WirePoint(point_id=f"{wire_id}-P1", wire_id=wire_id, role="first", x=first_xy[0], y=first_xy[1])
    second_point = WirePoint(point_id=f"{wire_id}-P2", wire_id=wire_id, role="second", x=second_xy[0], y=second_xy[1])
    return WireGeometry(
        wire_id=wire_id,
        layer_name="06_wire",
        source_type="LINE",
        source_entity_indices=(0,),
        route_points=(first_xy, second_xy),
        first_point=first_point,
        second_point=second_point,
        length=3.5,
        angle_deg=45.0,
        bbox=(min(first_xy[0], second_xy[0]), min(first_xy[1], second_xy[1]), max(first_xy[0], second_xy[0]), max(first_xy[1], second_xy[1])),
        cluster_id=group_hint,
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


def test_preview_coordinate_helpers_use_compact_cell_text_and_full_tooltip():
    assert format_preview_xy_lines(1.0, 2.0) == "X 1.000\nY 2.000"
    assert format_preview_point_tooltip(1.0, 2.0, None, 7.5) == "X 1.000\nY 2.000\nZ 7.500"
    assert format_count_label(1, "group") == "1 group"
    assert format_count_label(2, "wire") == "2 wires"
    assert compact_path_text("C:/short/path") == "C:/short/path"
    assert compact_path_text("C:/Users/demo/Desktop/Auto-Bonding/output/templates") == "C:/Users/demo/Desk...g/output/templates"


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

    assert "Wire extraction: 1 final path(s) from 2 raw path candidate(s) in 06_wire." in text
    assert "06_wire entity stats: LINE=2, LWPOLYLINE=0, POLYLINE=0, INSERT=0, ARC=0, SPLINE=0." in text
    assert "Pad-filtered paths: 0. Merged wire paths: 2->1." in text
    assert "Skipped wire-layer entities: unsupported_entity_type=1." in text
    assert "Skipped examples: #1 POINT unsupported_entity_type." in text
    assert "Potential split-wire joins: 1 endpoint pair(s)." in text
    assert "Join examples: W0001(second) <-> W0002(first) @ (1.000, 0.000) [continuous]." in text
    assert "Merge suggestions: W0001->W0002 join_as_is reverse=none." in text


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


def test_wire_export_dialog_defaults_to_compact_overview(tmp_path):
    _app()
    document = ProjectDocument(
        path=Path("preview.dxf"),
        size_bytes=0,
        raw_entities=[],
        scene_rect=(0.0, 0.0, 10.0, 10.0),
        raw_counts=Counter(),
        layer_info=[{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}],
        wire_geometries=[
            _wire_geometry("W0001", (1.0, 2.0), (3.0, 4.0), group_hint="A"),
            _wire_geometry("W0002", (5.0, 6.0), (7.0, 8.0), group_hint="B"),
        ],
    )
    store = WireRecipeTemplateStore(tmp_path / "wire_templates.json")

    dialog = WireExportDialog(document, store, tmp_path)

    assert dialog.advanced_json_toggle.isChecked() is False
    assert dialog.advanced_json_container.isHidden() is True
    assert dialog.preview_table.horizontalHeaderItem(3).text() == "First Bond"
    assert dialog.preview_table.horizontalHeaderItem(4).text() == "Second Bond"
    assert dialog.preview_summary_label.text().startswith("2 wires across ")
    assert dialog.preview_summary_label.text().endswith("Showing the first 2 rows.")
    assert dialog.wire_card_value.text().startswith("2 wires / ")
    first_cell = dialog.preview_table.item(0, 3)
    assert first_cell is not None
    assert first_cell.text() == "X 1.000\nY 2.000"
    assert first_cell.toolTip() == "X 1.000\nY 2.000\nZ 1455.200"

    dialog.close()
