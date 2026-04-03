"""Layer import dialog tests."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.layer_config_dialog import LayerConfigDialog


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _layer_info() -> list[dict[str, object]]:
    return [
        {
            "name": "01_base",
            "entity_count": 8,
            "mapped_type": "die_pad",
            "suggested_role": "die_pad",
        },
        {
            "name": "02_wire",
            "entity_count": 5,
            "mapped_type": "wire",
            "suggested_role": "wire",
        },
        {
            "name": "03_notes",
            "entity_count": 0,
            "mapped_type": None,
            "suggested_role": None,
        },
    ]


def test_layer_config_dialog_summary_updates_with_scope_changes():
    _app()
    dialog = LayerConfigDialog(
        _layer_info(),
        enabled_layers={"01_base", "02_wire"},
        layer_mapping_overrides={},
    )

    assert dialog.scope_badge.text() == "2 enabled"
    assert dialog.mapping_badge.text() == "0 remapped"
    assert "1 skipped" in dialog.detail_label.text()
    assert "2/2 populated" in dialog.detail_label.text()

    notes_row = next(row for row in dialog._rows if row[0] == "03_notes")
    notes_row[2].setChecked(True)
    notes_row[3].setCurrentIndex(4)

    assert dialog.scope_badge.text() == "3 enabled"
    assert dialog.mapping_badge.text() == "1 remapped"
    assert "0 skipped" in dialog.detail_label.text()
    assert "1 explicit role overrides" in dialog.detail_label.text()

    dialog.deleteLater()


def test_layer_config_dialog_payload_preserves_enabled_layers_and_overrides():
    _app()
    dialog = LayerConfigDialog(
        _layer_info(),
        enabled_layers={"01_base", "03_notes"},
        layer_mapping_overrides={"03_notes": "bond_point"},
    )

    payload = dialog.result_payload()

    assert payload["enabled_layers"] == {"01_base", "03_notes"}
    assert payload["layer_mapping_overrides"] == {"03_notes": "bond_point"}
    assert payload["effective_layer_mapping"]["03_NOTES"] == "bond_point"

    dialog.deleteLater()


def test_layer_config_dialog_respects_explicit_empty_enabled_layers():
    _app()
    dialog = LayerConfigDialog(
        _layer_info(),
        enabled_layers=set(),
        layer_mapping_overrides={},
    )

    assert dialog.scope_badge.text() == "0 enabled"
    assert all(not row[2].isChecked() for row in dialog._rows)
    assert dialog.detail_label.text().endswith("Enable at least one layer to continue.")

    dialog.deleteLater()


def test_layer_config_dialog_bulk_actions_refresh_summary_and_payload():
    _app()
    dialog = LayerConfigDialog(
        _layer_info(),
        enabled_layers={"01_base", "03_notes"},
        layer_mapping_overrides={"03_notes": "bond_point"},
    )

    dialog._set_all_layers_enabled(False)
    assert dialog.scope_badge.text() == "0 enabled"

    dialog._enable_populated_layers()
    assert dialog.scope_badge.text() == "2 enabled"
    assert {row[0] for row in dialog._rows if row[2].isChecked()} == {"01_base", "02_wire"}

    dialog._reset_mappings()
    payload = dialog.result_payload()
    assert dialog.mapping_badge.text() == "0 remapped"
    assert payload["enabled_layers"] == {"01_base", "02_wire"}
    assert payload["layer_mapping_overrides"] == {}

    dialog.deleteLater()


def test_layer_config_dialog_filters_rows_by_name_role_and_empty_state():
    _app()
    dialog = LayerConfigDialog(
        _layer_info(),
        enabled_layers={"01_base", "02_wire", "03_notes"},
        layer_mapping_overrides={},
    )

    dialog.filter_input.setText("wire")
    visible_rows = [index for index in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(index)]
    assert visible_rows == [1]
    assert "showing 1/3" in dialog.detail_label.text()

    dialog.filter_input.clear()
    dialog.hide_empty_checkbox.setChecked(True)
    visible_rows = [index for index in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(index)]
    assert visible_rows == [0, 1]

    dialog.filter_input.setText("bond point")
    visible_rows = [index for index in range(dialog.table.rowCount()) if not dialog.table.isRowHidden(index)]
    assert visible_rows == []
    assert dialog.detail_label.text().endswith("No layers match the current filter.")

    dialog.deleteLater()
