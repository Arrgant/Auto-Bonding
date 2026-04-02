"""Dialog for template-driven WB1/XLSM wire production export."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.export import (
    WireProductionExporter,
    WireRecipeTemplate,
    WireOrderingConfig,
    build_rx2000_default_template,
)
from services import ProjectDocument, WireRecipeTemplateStore

@dataclass(frozen=True)
class WireExportRequest:
    """Resolved export request returned by the dialog."""

    template: WireRecipeTemplate
    output_directory: Path
    base_name: str
    export_wb1: bool
    export_xlsm: bool


class WireExportDialog(QDialog):
    """Edit wire export templates and choose one export action."""

    def __init__(
        self,
        document: ProjectDocument,
        template_store: WireRecipeTemplateStore,
        output_directory: Path,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Wire Production Export")
        self.resize(1080, 820)

        self.document = document
        self.template_store = template_store
        self.output_directory = Path(output_directory)
        self._production_exporter = WireProductionExporter()
        self._loading_template = False
        self._template_ids_by_index: list[str] = []
        self._current_template_id: str | None = None
        self._current_header_defaults: dict[str, Any] = {}
        self._export_request: WireExportRequest | None = None

        self._build_ui()
        self._reload_templates()

    def export_request(self) -> WireExportRequest | None:
        """Return the chosen export request after the dialog is accepted."""

        return self._export_request

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        summary = QLabel(
            "Choose a saved machine template or create a new one. "
            "WB1 export uses the sample template path plus the field mapping JSON, "
            "while XLSM export copies the macro workbook and adds a safe coordinate sheet."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.addWidget(QLabel("Template"))

        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._handle_template_changed)
        top_row.addWidget(self.template_combo, stretch=1)

        self.new_template_button = QPushButton("New")
        self.new_template_button.clicked.connect(self._new_template)
        top_row.addWidget(self.new_template_button)

        self.save_template_button = QPushButton("Save")
        self.save_template_button.clicked.connect(self._save_template)
        top_row.addWidget(self.save_template_button)

        self.save_as_template_button = QPushButton("Save As")
        self.save_as_template_button.clicked.connect(self._save_template_as)
        top_row.addWidget(self.save_as_template_button)

        layout.addLayout(top_row)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        layout.addLayout(body, stretch=1)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(12)
        body.addLayout(left_column, stretch=3)

        left_column.addWidget(self._build_general_group())
        left_column.addWidget(self._build_json_group(), stretch=1)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(12)
        body.addLayout(right_column, stretch=2)

        right_column.addWidget(self._build_output_group())
        right_column.addWidget(self._build_preview_group(), stretch=1)

        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        action_row.addStretch(1)

        self.export_wb1_button = QPushButton("Export WB1")
        self.export_wb1_button.clicked.connect(lambda: self._accept_export(export_wb1=True, export_xlsm=False))
        action_row.addWidget(self.export_wb1_button)

        self.export_xlsm_button = QPushButton("Export XLSM")
        self.export_xlsm_button.clicked.connect(lambda: self._accept_export(export_wb1=False, export_xlsm=True))
        action_row.addWidget(self.export_xlsm_button)

        self.export_both_button = QPushButton("Export Both")
        self.export_both_button.clicked.connect(lambda: self._accept_export(export_wb1=True, export_xlsm=True))
        action_row.addWidget(self.export_both_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        action_row.addWidget(self.cancel_button)

        layout.addLayout(action_row)

    def _build_general_group(self) -> QWidget:
        group = QGroupBox("Template Settings")
        form = QFormLayout(group)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)

        self.template_name_edit = QLineEdit()
        self.template_name_edit.textChanged.connect(self._refresh_preview)
        form.addRow("Template Name", self.template_name_edit)

        self.machine_type_edit = QLineEdit()
        self.machine_type_edit.textChanged.connect(self._refresh_preview)
        form.addRow("Machine Type", self.machine_type_edit)

        self.wb1_template_path_edit = QLineEdit()
        self.wb1_template_path_edit.textChanged.connect(self._refresh_preview)
        form.addRow("WB1 Template", self._with_browse_button(self.wb1_template_path_edit, self._browse_wb1_template))

        self.xlsm_template_path_edit = QLineEdit()
        self.xlsm_template_path_edit.textChanged.connect(self._refresh_preview)
        form.addRow(
            "XLSM Template",
            self._with_browse_button(self.xlsm_template_path_edit, self._browse_xlsm_template),
        )

        self.coord_scale_spin = QDoubleSpinBox()
        self.coord_scale_spin.setDecimals(6)
        self.coord_scale_spin.setRange(0.000001, 1000000.0)
        self.coord_scale_spin.setValue(1.0)
        self.coord_scale_spin.valueChanged.connect(self._refresh_preview)
        form.addRow("Coord Scale", self.coord_scale_spin)

        self.default_z_spin = QDoubleSpinBox()
        self.default_z_spin.setDecimals(6)
        self.default_z_spin.setRange(-1000000.0, 1000000.0)
        self.default_z_spin.valueChanged.connect(self._refresh_preview)
        form.addRow("Default Z", self.default_z_spin)

        ordering_row = QWidget()
        ordering_layout = QGridLayout(ordering_row)
        ordering_layout.setContentsMargins(0, 0, 0, 0)
        ordering_layout.setHorizontalSpacing(8)
        ordering_layout.setVerticalSpacing(6)

        self.primary_axis_combo = QComboBox()
        self.primary_axis_combo.addItem("X", "x")
        self.primary_axis_combo.addItem("Y", "y")
        self.primary_axis_combo.currentIndexChanged.connect(self._refresh_preview)
        ordering_layout.addWidget(QLabel("Primary Axis"), 0, 0)
        ordering_layout.addWidget(self.primary_axis_combo, 0, 1)

        self.primary_direction_combo = QComboBox()
        self.primary_direction_combo.addItem("Ascending", "asc")
        self.primary_direction_combo.addItem("Descending", "desc")
        self.primary_direction_combo.currentIndexChanged.connect(self._refresh_preview)
        ordering_layout.addWidget(QLabel("Direction"), 0, 2)
        ordering_layout.addWidget(self.primary_direction_combo, 0, 3)

        self.secondary_direction_combo = QComboBox()
        self.secondary_direction_combo.addItem("Ascending", "asc")
        self.secondary_direction_combo.addItem("Descending", "desc")
        self.secondary_direction_combo.currentIndexChanged.connect(self._refresh_preview)
        ordering_layout.addWidget(QLabel("Tie Break"), 1, 0)
        ordering_layout.addWidget(self.secondary_direction_combo, 1, 1)

        self.start_role_combo = QComboBox()
        self.start_role_combo.addItem("First Bond First", "first")
        self.start_role_combo.addItem("Second Bond First", "second")
        self.start_role_combo.currentIndexChanged.connect(self._refresh_preview)
        ordering_layout.addWidget(QLabel("Point Order"), 1, 2)
        ordering_layout.addWidget(self.start_role_combo, 1, 3)

        self.group_no_spin = QSpinBox()
        self.group_no_spin.setRange(1, 999999)
        self.group_no_spin.setValue(1)
        self.group_no_spin.valueChanged.connect(self._refresh_preview)
        ordering_layout.addWidget(QLabel("Group No"), 2, 0)
        ordering_layout.addWidget(self.group_no_spin, 2, 1)

        form.addRow("Ordering", ordering_row)
        return group

    def _build_json_group(self) -> QWidget:
        group = QGroupBox("Advanced JSON")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.record_defaults_edit = self._build_json_editor(
            layout,
            "Record Defaults",
            "Named non-coordinate defaults that match WB1 field names when available.",
        )
        self.role_record_defaults_edit = self._build_json_editor(
            layout,
            "Role Record Defaults",
            "Per-role named overrides, for example {\"first\": {...}, \"second\": {...}}.",
        )
        self.header_defaults_edit = self._build_json_editor(
            layout,
            "Header Defaults",
            "WB1 header word overrides using PRE:line:word or G/H/I:line:word, for example {\"PRE:1:2\": 45, \"H:0:5\": 1}.",
        )
        self.wb1_field_map_edit = self._build_json_editor(
            layout,
            "WB1 Field Map",
            "Machine-specific word positions, for example role_code / bond_x / bond_y / bond_z / wire_seq.",
        )
        self.wb1_record_defaults_edit = self._build_json_editor(
            layout,
            "WB1 Record Defaults",
            "Raw word-index overrides applied before coordinates are written.",
        )
        self.wb1_role_codes_edit = self._build_json_editor(
            layout,
            "WB1 Role Codes",
            "Usually {\"first\": 0, \"second\": 2}.",
        )
        return group

    def _build_json_editor(self, parent_layout: QVBoxLayout, title: str, help_text: str) -> QPlainTextEdit:
        label = QLabel(title)
        parent_layout.addWidget(label)
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #8E8E8E; font-size: 12px;")
        parent_layout.addWidget(help_label)
        editor = QPlainTextEdit()
        editor.setMinimumHeight(92)
        editor.textChanged.connect(self._refresh_preview)
        parent_layout.addWidget(editor)
        return editor

    def _build_output_group(self) -> QWidget:
        group = QGroupBox("Export Output")
        form = QFormLayout(group)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)

        self.output_directory_edit = QLineEdit(str(self.output_directory))
        form.addRow("Output Directory", self._with_browse_button(self.output_directory_edit, self._browse_output_directory))

        self.base_name_edit = QLineEdit(self.document.path.stem)
        form.addRow("Base Name", self.base_name_edit)
        return group

    def _build_preview_group(self) -> QWidget:
        group = QGroupBox("Order Preview")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.preview_summary_label = QLabel("No preview yet.")
        layout.addWidget(self.preview_summary_label)

        self.preview_table = QTableWidget(0, 7, self)
        self.preview_table.setHorizontalHeaderLabels(
            ["Wire Seq", "Wire ID", "Group", "First (X,Y,Z)", "Second (X,Y,Z)", "Length", "Angle"]
        )
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.preview_table, stretch=1)
        return group

    def _with_browse_button(self, line_edit: QLineEdit, handler) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(line_edit, stretch=1)
        button = QPushButton("Browse...")
        button.clicked.connect(handler)
        layout.addWidget(button)
        return row

    def _browse_wb1_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose WB1 template",
            self.wb1_template_path_edit.text().strip(),
            "WB1 Files (*.WB1);;All Files (*)",
        )
        if path:
            self.wb1_template_path_edit.setText(path)

    def _browse_xlsm_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose XLSM template",
            self.xlsm_template_path_edit.text().strip(),
            "Excel Macro Files (*.xlsm);;All Files (*)",
        )
        if path:
            self.xlsm_template_path_edit.setText(path)

    def _browse_output_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Choose output directory",
            self.output_directory_edit.text().strip() or str(self.output_directory),
        )
        if path:
            self.output_directory_edit.setText(path)

    def _reload_templates(self) -> None:
        templates = self.template_store.list_templates()
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self._template_ids_by_index = []
        for template in templates:
            self.template_combo.addItem(template.name, userData=template.template_id)
            self._template_ids_by_index.append(template.template_id)
        self.template_combo.blockSignals(False)

        if templates:
            self.template_combo.setCurrentIndex(0)
            self._load_template(templates[0], template_id=templates[0].template_id)
            return

        self._load_template(self._build_starter_template(), template_id=None)

    def _handle_template_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._template_ids_by_index):
            return
        template_id = self._template_ids_by_index[index]
        template = self.template_store.get_template(template_id)
        if template is None:
            return
        self._load_template(template, template_id=template_id)

    def _load_template(self, template: WireRecipeTemplate, *, template_id: str | None) -> None:
        self._loading_template = True
        self._current_template_id = template_id
        self._current_header_defaults = dict(template.header_defaults)
        self.template_name_edit.setText(template.name)
        self.machine_type_edit.setText(template.machine_type)
        self.wb1_template_path_edit.setText(template.wb1_template_path or "")
        self.xlsm_template_path_edit.setText(template.xlsm_template_path or "")
        self.coord_scale_spin.setValue(template.coord_scale)
        self.default_z_spin.setValue(template.default_z)
        self._set_combo_by_data(self.primary_axis_combo, template.ordering.primary_axis)
        self._set_combo_by_data(self.primary_direction_combo, template.ordering.primary_direction)
        self._set_combo_by_data(self.secondary_direction_combo, template.ordering.secondary_direction)
        self._set_combo_by_data(self.start_role_combo, template.ordering.start_role)
        self.group_no_spin.setValue(template.ordering.group_no)
        self.record_defaults_edit.setPlainText(self._to_json(template.record_defaults))
        self.role_record_defaults_edit.setPlainText(self._to_json(template.role_record_defaults))
        self.header_defaults_edit.setPlainText(self._to_json(template.header_defaults))
        self.wb1_field_map_edit.setPlainText(self._to_json(template.wb1_field_map))
        self.wb1_record_defaults_edit.setPlainText(self._to_json(template.wb1_record_defaults))
        self.wb1_role_codes_edit.setPlainText(self._to_json(template.wb1_role_codes))
        self._loading_template = False
        self._refresh_preview()

    def _set_combo_by_data(self, combo: QComboBox, target: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == target:
                combo.setCurrentIndex(index)
                return

    def _new_template(self) -> None:
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentIndex(-1)
        self.template_combo.blockSignals(False)
        self._load_template(self._build_starter_template(), template_id=None)

    def _save_template(self) -> None:
        template = self._collect_template(show_errors=True)
        if template is None:
            return

        if self._current_template_id is None:
            self._save_template_as()
            return

        saved = self._with_template_id(template, self._current_template_id)
        self.template_store.save_template(saved)
        self._reload_templates_and_select(saved.template_id)
        self.status_label.setText(f"Saved template {saved.name}.")

    def _save_template_as(self) -> None:
        template = self._collect_template(show_errors=True)
        if template is None:
            return

        default_name = template.name or "New Template"
        name, accepted = QInputDialog.getText(self, "Save template as", "Template name", text=default_name)
        if not accepted or not name.strip():
            return

        template_id = self._make_template_id(name)
        while self.template_store.get_template(template_id) is not None:
            template_id = self._make_template_id(name, suffix=uuid.uuid4().hex[:6])

        saved = self._with_template_id(template, template_id, name=name.strip())
        self.template_store.save_template(saved)
        self._reload_templates_and_select(saved.template_id)
        self.status_label.setText(f"Saved new template {saved.name}.")

    def _reload_templates_and_select(self, template_id: str) -> None:
        self._reload_templates()
        for index, item_template_id in enumerate(self._template_ids_by_index):
            if item_template_id == template_id:
                self.template_combo.setCurrentIndex(index)
                return

    def _with_template_id(
        self,
        template: WireRecipeTemplate,
        template_id: str,
        *,
        name: str | None = None,
    ) -> WireRecipeTemplate:
        return WireRecipeTemplate(
            template_id=template_id,
            name=name or template.name,
            machine_type=template.machine_type,
            wb1_template_path=template.wb1_template_path,
            xlsm_template_path=template.xlsm_template_path,
            coord_scale=template.coord_scale,
            default_z=template.default_z,
            ordering=template.ordering,
            header_defaults=template.header_defaults,
            record_defaults=template.record_defaults,
            role_record_defaults=template.role_record_defaults,
            wb1_field_map=template.wb1_field_map,
            wb1_record_defaults=template.wb1_record_defaults,
            wb1_role_codes=template.wb1_role_codes,
        )

    def _collect_template(self, *, show_errors: bool) -> WireRecipeTemplate | None:
        try:
            record_defaults = self._parse_json_object(self.record_defaults_edit.toPlainText(), "Record Defaults")
            role_record_defaults = self._parse_json_object(
                self.role_record_defaults_edit.toPlainText(),
                "Role Record Defaults",
            )
            header_defaults = self._parse_json_object(self.header_defaults_edit.toPlainText(), "Header Defaults")
            wb1_field_map = self._parse_json_object(self.wb1_field_map_edit.toPlainText(), "WB1 Field Map")
            wb1_record_defaults = self._parse_json_object(
                self.wb1_record_defaults_edit.toPlainText(),
                "WB1 Record Defaults",
            )
            wb1_role_codes = self._parse_json_object(self.wb1_role_codes_edit.toPlainText(), "WB1 Role Codes")
        except ValueError as exc:
            if show_errors:
                QMessageBox.warning(self, "Template JSON", str(exc))
            return None

        name = self.template_name_edit.text().strip() or "New Template"
        try:
            field_map = {str(key): int(value) for key, value in wb1_field_map.items()}
            record_index_defaults = {int(key): value for key, value in wb1_record_defaults.items()}
        except (TypeError, ValueError) as exc:
            if show_errors:
                QMessageBox.warning(self, "Template JSON", f"WB1 JSON contains a non-numeric field index: {exc}")
            return None
        try:
            role_named_defaults = self._normalize_role_record_defaults(role_record_defaults)
        except ValueError as exc:
            if show_errors:
                QMessageBox.warning(self, "Template JSON", str(exc))
            return None

        return WireRecipeTemplate(
            template_id=self._current_template_id or self._make_template_id(name),
            name=name,
            machine_type=self.machine_type_edit.text().strip() or "RX2000",
            wb1_template_path=self._optional_path(self.wb1_template_path_edit.text()),
            xlsm_template_path=self._optional_path(self.xlsm_template_path_edit.text()),
            coord_scale=float(self.coord_scale_spin.value()),
            default_z=float(self.default_z_spin.value()),
            ordering=WireOrderingConfig(
                primary_axis=str(self.primary_axis_combo.currentData()),
                primary_direction=str(self.primary_direction_combo.currentData()),
                secondary_direction=str(self.secondary_direction_combo.currentData()),
                start_role=str(self.start_role_combo.currentData()),
                group_no=int(self.group_no_spin.value()),
            ),
            header_defaults=header_defaults,
            record_defaults=record_defaults,
            role_record_defaults=role_named_defaults,
            wb1_field_map=field_map,
            wb1_record_defaults=record_index_defaults,
            wb1_role_codes={str(key): value for key, value in wb1_role_codes.items()},
        )

    def _parse_json_object(self, text: str, field_name: str) -> dict[str, Any]:
        stripped = text.strip()
        if not stripped:
            return {}
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} JSON is invalid: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{field_name} must be a JSON object.")
        return payload

    def _optional_path(self, text: str) -> str | None:
        stripped = text.strip()
        return stripped or None

    def _normalize_role_record_defaults(self, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        for role, values in payload.items():
            if not isinstance(values, dict):
                raise ValueError("Role Record Defaults must map each role name to a JSON object.")
            normalized[str(role)] = {str(key): value for key, value in values.items()}
        return normalized

    def _refresh_preview(self) -> None:
        if self._loading_template:
            return

        template = self._collect_template(show_errors=False)
        if template is None:
            self.preview_table.setRowCount(0)
            self.preview_summary_label.setText("Preview unavailable until the JSON fields are valid.")
            return

        ordered_records = self._production_exporter.build_ordered_records(self.document.wire_geometries, template)
        preview_records = ordered_records[: min(len(ordered_records), 120)]
        self.preview_table.setRowCount(len(preview_records))

        for row_index, record in enumerate(preview_records):
            first = record.geometry.first_point
            second = record.geometry.second_point
            values = [
                str(record.wire_seq),
                record.wire_id,
                str(record.group_no),
                f"{first.x:.3f}, {first.y:.3f}, {first.z:.3f}",
                f"{second.x:.3f}, {second.y:.3f}, {second.z:.3f}",
                f"{record.geometry.length:.3f}",
                f"{record.geometry.angle_deg:.2f}",
            ]
            for column, value in enumerate(values):
                self.preview_table.setItem(row_index, column, QTableWidgetItem(value))

        if ordered_records:
            self.preview_summary_label.setText(
                f"{len(ordered_records)} wires detected. Showing the first {len(preview_records)} ordered rows."
            )
        else:
            self.preview_summary_label.setText("No wire geometries are available in the current document.")

    def _accept_export(self, *, export_wb1: bool, export_xlsm: bool) -> None:
        if not self.document.wire_geometries:
            QMessageBox.information(self, "Wire export", "No wire geometries are available in the current document.")
            return

        template = self._collect_template(show_errors=True)
        if template is None:
            return

        output_directory_text = self.output_directory_edit.text().strip()
        if not output_directory_text:
            QMessageBox.warning(self, "Wire export", "Choose an output directory.")
            return

        base_name = self.base_name_edit.text().strip()
        issues = self._production_exporter.validate_export_request(
            self.document.wire_geometries,
            template,
            base_name=base_name,
            export_wb1=export_wb1,
            export_xlsm=export_xlsm,
        )
        if issues:
            QMessageBox.warning(self, "Wire export", "\n".join(issues))
            return

        self._export_request = WireExportRequest(
            template=template,
            output_directory=Path(output_directory_text),
            base_name=base_name,
            export_wb1=export_wb1,
            export_xlsm=export_xlsm,
        )
        self.accept()

    def _build_starter_template(self) -> WireRecipeTemplate:
        starter = build_rx2000_default_template()
        return WireRecipeTemplate(
            template_id="starter-template",
            name="New Template",
            machine_type=starter.machine_type,
            wb1_template_path=starter.wb1_template_path,
            xlsm_template_path=starter.xlsm_template_path,
            coord_scale=starter.coord_scale,
            default_z=starter.default_z,
            ordering=starter.ordering,
            header_defaults=dict(starter.header_defaults),
            record_defaults=dict(starter.record_defaults),
            role_record_defaults={
                role: dict(values) for role, values in starter.role_record_defaults.items()
            },
            wb1_field_map=dict(starter.wb1_field_map),
            wb1_record_defaults=dict(starter.wb1_record_defaults),
            wb1_role_codes=dict(starter.wb1_role_codes),
        )

    def _make_template_id(self, name: str, *, suffix: str | None = None) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "template"
        if suffix:
            return f"{base}-{suffix}"
        return base

    def _to_json(self, payload: dict[object, object]) -> str:
        return json.dumps(payload, indent=2, sort_keys=True)


__all__ = ["WireExportDialog", "WireExportRequest"]
