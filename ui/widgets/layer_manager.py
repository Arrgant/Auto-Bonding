"""Layer sidebar for 2D preview visibility and thickness controls."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout

from core.layer_semantics import format_layer_role
from core.layer_stack import layer_sort_key
from services import ProjectDocument


class LayerManagerPanel(QFrame):
    """Sidebar that manages preview-layer visibility and per-layer thickness."""

    layer_visibility_changed = Signal(str, bool)
    layer_selected = Signal(object)
    layer_thickness_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumWidth(270)
        self.setMaximumWidth(320)
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)

        title = QLabel("Layers")
        title.setObjectName("SectionTitle")
        title_row.addWidget(title)

        self.active_badge = QLabel("Idle")
        self.active_badge.setObjectName("SectionBadge")
        title_row.addWidget(self.active_badge)

        self.visible_badge = QLabel("0 shown")
        self.visible_badge.setObjectName("SectionBadge")
        title_row.addWidget(self.visible_badge)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self.summary = QLabel("Import a DXF to inspect layers.")
        self.summary.setObjectName("MutedLabel")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["On", "Layer", "Role", "Thk"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().resizeSection(0, 48)
        self.tree.header().resizeSection(1, 132)
        self.tree.header().resizeSection(2, 108)
        self.tree.header().resizeSection(3, 58)
        self.tree.itemChanged.connect(self._handle_item_changed)
        self.tree.itemSelectionChanged.connect(self._handle_selection_changed)
        self.tree.itemDoubleClicked.connect(self._handle_item_double_clicked)
        layout.addWidget(self.tree, stretch=1)

    def load_document(self, document: ProjectDocument | None) -> None:
        self._syncing = True
        self.tree.clear()

        if document is None:
            self.tree.setEnabled(False)
            self.active_badge.setText("Idle")
            self.visible_badge.setText("0 shown")
            self.summary.setText("Import a DXF to inspect layers.")
            self._syncing = False
            return

        visible_layers = set(document.visible_layers)
        populated_layers = [
            layer
            for layer in sorted(document.layer_info, key=lambda item: layer_sort_key(str(item["name"])))
            if layer.get("entity_count", 0) > 0
        ]
        active_layers = [
            layer
            for layer in populated_layers
            if layer.get("enabled", True) and layer.get("entity_count", 0) > 0
        ]

        self.tree.setEnabled(bool(active_layers))
        if not active_layers:
            self.active_badge.setText("0 imported")
            self.visible_badge.setText("0 shown")
            self.summary.setText("No populated DXF layers are currently imported.")
            self._syncing = False
            return

        active_names = {str(layer["name"]) for layer in active_layers}
        visible_count = len(active_names & visible_layers)
        skipped_count = max(len(populated_layers) - len(active_layers), 0)
        remapped_count = len(document.layer_mapping_overrides)
        self.active_badge.setText(f"{len(active_layers)} imported")
        self.visible_badge.setText(f"{visible_count} shown")
        summary = (
            "Viewer-only toggles. Use Import Layers above to exclude or remap DXF layers. "
            "Double-click a row to set thickness."
        )
        if skipped_count or remapped_count:
            summary = (
                f"{len(active_layers)} imported, {skipped_count} skipped, {remapped_count} remapped. "
                "Checkboxes here only hide or show imported layers."
            )
        self.summary.setText(summary)
        selected_item: QTreeWidgetItem | None = None

        for layer in active_layers:
            layer_name = str(layer["name"])
            item = QTreeWidgetItem(self.tree)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setData(0, Qt.ItemDataRole.UserRole, layer_name)
            item.setCheckState(
                0,
                Qt.CheckState.Checked if layer_name in visible_layers else Qt.CheckState.Unchecked,
            )
            item.setText(1, layer_name)
            item.setText(2, format_layer_role(layer.get("suggested_role") or layer.get("mapped_type")))
            thickness = document.layer_thicknesses.get(layer_name)
            item.setText(3, "-" if thickness is None else f"{thickness:.3f}")
            if document.selected_layer_name == layer_name:
                selected_item = item

        if selected_item is not None:
            self.tree.setCurrentItem(selected_item)
        self._syncing = False

    def _handle_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._syncing:
            return
        layer_name = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(layer_name, str):
            self.layer_visibility_changed.emit(layer_name, item.checkState(0) == Qt.CheckState.Checked)

    def _handle_selection_changed(self) -> None:
        if self._syncing:
            return
        item = self.tree.currentItem()
        if item is None:
            self.layer_selected.emit(None)
            return
        layer_name = item.data(0, Qt.ItemDataRole.UserRole)
        self.layer_selected.emit(layer_name if isinstance(layer_name, str) else None)

    def _handle_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._syncing:
            return
        layer_name = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(layer_name, str):
            self.layer_thickness_requested.emit(layer_name)


__all__ = ["LayerManagerPanel"]
