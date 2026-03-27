"""Dialog for choosing active DXF layers and manual layer mappings."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
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
        self.setWindowTitle("Layer Setup")
        self.resize(760, 520)

        self._enabled_layers = set(enabled_layers) if enabled_layers else {
            str(layer["name"]) for layer in layer_info if layer.get("enabled", True)
        }
        self._layer_mapping_overrides = dict(layer_mapping_overrides or {})
        self._rows: list[tuple[str, QCheckBox, QComboBox]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        summary = QLabel("Select which DXF layers participate in import and optionally override their layer type.")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Use", "Layer", "Entities", "Detected", "Mapping"])
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
            self.table.insertRow(row_index)

            checkbox = QCheckBox()
            checkbox.setChecked(layer_name in self._enabled_layers)
            self.table.setCellWidget(row_index, 0, checkbox)

            layer_item = QTableWidgetItem(layer_name)
            count_item = QTableWidgetItem(str(layer.get("entity_count", 0)))
            detected_item = QTableWidgetItem(
                format_layer_role(layer.get("suggested_role") or layer.get("mapped_type"))
            )

            mapping_combo = QComboBox()
            for label, value in LAYER_MAPPING_CHOICES:
                mapping_combo.addItem(label, userData=value)

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
            self._rows.append((layer_name, checkbox, mapping_combo))

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def result_payload(self) -> dict[str, Any]:
        enabled_layers: set[str] = set()
        layer_mapping_overrides: dict[str, str] = {}

        for layer_name, checkbox, mapping_combo in self._rows:
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


__all__ = ["LayerConfigDialog", "LAYER_MAPPING_CHOICES"]
