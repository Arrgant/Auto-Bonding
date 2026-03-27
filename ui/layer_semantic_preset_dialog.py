"""Dialog for managing persisted semantic layer presets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.layer_semantics import format_layer_role


class LayerSemanticPresetDialog(QDialog):
    """Inspect and edit saved semantic layer presets."""

    def __init__(self, presets: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Semantic Presets")
        self.resize(520, 420)
        self._presets = dict(sorted(presets.items()))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        summary = QLabel(
            "These saved presets apply to future DXF imports on this machine. "
            "Removing them does not modify the currently opened DXF file."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["Layer Key", "Semantic Role"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self._remove_selected)
        controls.addWidget(self.remove_button)

        self.clear_button = QPushButton("Reset All")
        self.clear_button.clicked.connect(self._clear_all)
        controls.addWidget(self.clear_button)
        controls.addStretch(1)

        layout.addLayout(controls)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._reload_table()

    def result_presets(self) -> dict[str, str]:
        """Return the edited preset payload."""

        return dict(self._presets)

    def _reload_table(self) -> None:
        self.table.setRowCount(0)
        for row, (layer_key, role_name) in enumerate(sorted(self._presets.items())):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(layer_key))
            self.table.setItem(row, 1, QTableWidgetItem(format_layer_role(role_name)))

        has_rows = bool(self._presets)
        self.remove_button.setEnabled(has_rows)
        self.clear_button.setEnabled(has_rows)
        if has_rows and self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _remove_selected(self) -> None:
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        layer_item = self.table.item(current_row, 0)
        if layer_item is None:
            return
        self._presets.pop(layer_item.text(), None)
        self._reload_table()

    def _clear_all(self) -> None:
        if not self._presets:
            return
        answer = QMessageBox.question(
            self,
            "Reset semantic presets",
            "Remove all saved semantic layer presets for future imports?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._presets.clear()
        self._reload_table()


__all__ = ["LayerSemanticPresetDialog"]
