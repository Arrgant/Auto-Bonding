"""Dialog for choosing active DXF layers and manual layer mappings."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.layer_semantics import format_layer_role
from core.layer_stack import layer_sort_key
from core.parsing.dxf import DEFAULT_LAYER_MAPPING
from core.raw_dxf_types import LayerInfo

LAYER_MAPPING_CHOICES = [
    ("Auto", None),
    ("Die Pad", "die_pad"),
    ("Wire", "wire"),
    ("Lead Frame", "lead_frame"),
    ("Bond Point", "bond_point"),
]


class LayerConfigDialog(QDialog):
    """Collect enabled-layer state and explicit layer-type overrides."""

    def __init__(
        self,
        layer_info: list[LayerInfo],
        *,
        enabled_layers: set[str] | None = None,
        layer_mapping_overrides: dict[str, str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Import Layers")
        self.resize(820, 560)

        self._enabled_layers = set(enabled_layers) if enabled_layers is not None else {
            str(layer["name"]) for layer in layer_info if layer.get("enabled", True)
        }
        self._layer_mapping_overrides = dict(layer_mapping_overrides or {})
        self._rows: list[tuple[str, int, QCheckBox, QComboBox]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        summary = QLabel(
            "Choose which DXF layers are imported into this session. "
            "This is different from the left Layers panel, which only hides or shows layers after import."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)

        self.scope_badge = QLabel("0 enabled")
        self.scope_badge.setObjectName("SectionBadge")
        status_row.addWidget(self.scope_badge)

        self.mapping_badge = QLabel("0 remapped")
        self.mapping_badge.setObjectName("SectionBadge")
        status_row.addWidget(self.mapping_badge)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(8)

        enable_all_button = QPushButton("Enable All", self)
        enable_all_button.setObjectName("SecondaryButton")
        enable_all_button.clicked.connect(lambda: self._set_all_layers_enabled(True))
        actions_row.addWidget(enable_all_button)

        populated_button = QPushButton("Only Populated", self)
        populated_button.setObjectName("SecondaryButton")
        populated_button.clicked.connect(self._enable_populated_layers)
        actions_row.addWidget(populated_button)

        reset_mapping_button = QPushButton("Reset Mapping", self)
        reset_mapping_button.setObjectName("SecondaryButton")
        reset_mapping_button.clicked.connect(self._reset_mappings)
        actions_row.addWidget(reset_mapping_button)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        self.detail_label = QLabel()
        self.detail_label.setObjectName("MutedLabel")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Use", "Layer", "Entities", "Detected", "Import As"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, stretch=1)

        for row_index, layer in enumerate(sorted(layer_info, key=lambda item: layer_sort_key(str(item["name"])))):
            layer_name = str(layer["name"])
            entity_count = int(layer.get("entity_count", 0))
            self.table.insertRow(row_index)

            checkbox = QCheckBox()
            checkbox.setChecked(layer_name in self._enabled_layers)
            checkbox.stateChanged.connect(self._update_summary)
            self.table.setCellWidget(row_index, 0, checkbox)

            layer_item = QTableWidgetItem(layer_name)
            count_item = QTableWidgetItem(str(entity_count))
            detected_item = QTableWidgetItem(
                format_layer_role(layer.get("suggested_role") or layer.get("mapped_type"))
            )

            mapping_combo = QComboBox()
            for label, value in LAYER_MAPPING_CHOICES:
                mapping_combo.addItem(label, userData=value)
            mapping_combo.currentIndexChanged.connect(self._update_summary)

            override_value = self._layer_mapping_overrides.get(layer_name)
            mapping_index = 0
            for index in range(mapping_combo.count()):
                if mapping_combo.itemData(index) == override_value:
                    mapping_index = index
                    break
            mapping_combo.setCurrentIndex(mapping_index)

            self.table.setItem(row_index, 1, layer_item)
            self.table.setItem(row_index, 2, count_item)
            self.table.setItem(row_index, 3, detected_item)
            self.table.setCellWidget(row_index, 4, mapping_combo)
            self._rows.append((layer_name, entity_count, checkbox, mapping_combo))

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self._update_summary()

    def result_payload(self) -> dict[str, Any]:
        enabled_layers: set[str] = set()
        layer_mapping_overrides: dict[str, str] = {}

        for layer_name, _entity_count, checkbox, mapping_combo in self._rows:
            if checkbox.isChecked():
                enabled_layers.add(layer_name)

            selected_value = mapping_combo.currentData()
            if selected_value is not None:
                layer_mapping_overrides[layer_name] = str(selected_value)

        effective_mapping = dict(DEFAULT_LAYER_MAPPING)
        effective_mapping.update({name.upper(): value for name, value in layer_mapping_overrides.items()})

        return {
            "enabled_layers": enabled_layers,
            "layer_mapping_overrides": layer_mapping_overrides,
            "effective_layer_mapping": effective_mapping,
        }

    def _set_all_layers_enabled(self, enabled: bool) -> None:
        self._apply_bulk_row_updates(
            lambda _layer_name, _entity_count, checkbox, _mapping_combo: checkbox.setChecked(enabled)
        )

    def _enable_populated_layers(self) -> None:
        self._apply_bulk_row_updates(
            lambda _layer_name, entity_count, checkbox, _mapping_combo: checkbox.setChecked(entity_count > 0)
        )

    def _reset_mappings(self) -> None:
        self._apply_bulk_row_updates(
            lambda _layer_name, _entity_count, _checkbox, mapping_combo: mapping_combo.setCurrentIndex(0)
        )

    def _apply_bulk_row_updates(self, updater) -> None:
        blockers: list[QSignalBlocker] = []
        for layer_name, entity_count, checkbox, mapping_combo in self._rows:
            blockers.append(QSignalBlocker(checkbox))
            blockers.append(QSignalBlocker(mapping_combo))
            updater(layer_name, entity_count, checkbox, mapping_combo)
        self._update_summary()

    def _update_summary(self, *_args: object) -> None:
        total_layers = len(self._rows)
        enabled_layers = 0
        skipped_layers = 0
        remapped_layers = 0
        populated_layers = 0
        enabled_populated_layers = 0

        for _layer_name, entity_count, checkbox, mapping_combo in self._rows:
            is_enabled = checkbox.isChecked()
            if is_enabled:
                enabled_layers += 1
            else:
                skipped_layers += 1

            if entity_count > 0:
                populated_layers += 1
                if is_enabled:
                    enabled_populated_layers += 1

            if mapping_combo.currentData() is not None:
                remapped_layers += 1

        self.scope_badge.setText(f"{enabled_layers} enabled")
        self.mapping_badge.setText(f"{remapped_layers} remapped")

        detail_parts = [
            f"Importing {enabled_layers} of {total_layers} layers",
            f"{skipped_layers} skipped",
        ]
        if populated_layers:
            detail_parts.append(f"{enabled_populated_layers}/{populated_layers} populated")
        if remapped_layers:
            detail_parts.append(f"{remapped_layers} explicit role overrides")

        detail = ", ".join(detail_parts) + ". "
        if enabled_layers:
            detail += "Apply refreshes the 2D import preview before thickness and 3D build."
        else:
            detail += "Enable at least one layer to continue."
        self.detail_label.setText(detail)


__all__ = ["LayerConfigDialog", "LAYER_MAPPING_CHOICES"]
