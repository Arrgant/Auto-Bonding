"""Layer sidebar for 2D preview visibility and thickness controls."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout

from core.layer_semantics import format_layer_role
from core.layer_stack import layer_sort_key, layer_supports_stacked_preview
from services import ProjectDocument


class _LayerRowWidget(QFrame):
    """Compact card row for one visible/imported DXF layer."""

    selected = Signal()
    visibility_toggled = Signal(bool)
    thickness_requested = Signal()

    def __init__(
        self,
        *,
        layer_name: str,
        role_label: str,
        layer_color: str,
        thickness_label: str,
        is_visible: bool,
        thickness_editable: bool,
    ):
        super().__init__()
        self.setObjectName("LayerRowCard")
        self.setProperty("selected", False)
        self._thickness_editable = thickness_editable
        if thickness_editable:
            self.setToolTip(f"{layer_name}\nRole: {role_label}\nDouble-click to set thickness.")
        else:
            self.setToolTip(f"{layer_name}\nRole: {role_label}\nThis layer does not participate in stacked 3D preview.")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.color_chip = QLabel()
        self.color_chip.setObjectName("LayerColorChip")
        self.color_chip.setFixedSize(10, 26)
        self.color_chip.setStyleSheet(
            f"QLabel#LayerColorChip {{ background: {layer_color}; border-radius: 5px; }}"
        )
        layout.addWidget(self.color_chip)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(2)

        self.layer_label = QLabel(layer_name)
        self.layer_label.setObjectName("LayerRowTitle")
        self.layer_label.setToolTip(layer_name)
        text_column.addWidget(self.layer_label)

        self.role_label = QLabel(role_label)
        self.role_label.setObjectName("LayerRowMeta")
        text_column.addWidget(self.role_label)

        layout.addLayout(text_column, stretch=1)

        self.thickness_label = QLabel(thickness_label)
        self.thickness_label.setObjectName("LayerThicknessPill")
        layout.addWidget(self.thickness_label)

        self.visibility_button = QToolButton()
        self.visibility_button.setObjectName("LayerVisibilityToggle")
        self.visibility_button.setCheckable(True)
        self.visibility_button.setChecked(is_visible)
        self.visibility_button.setFixedSize(QSize(42, 26))
        self.visibility_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.visibility_button.toggled.connect(self._handle_visibility_toggled)
        self._refresh_visibility_text(is_visible)
        layout.addWidget(self.visibility_button)

    def set_selected(self, is_selected: bool) -> None:
        self.setProperty("selected", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # pragma: no cover
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # pragma: no cover
        if event.button() == Qt.MouseButton.LeftButton and self._thickness_editable:
            self.selected.emit()
            self.thickness_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _handle_visibility_toggled(self, checked: bool) -> None:
        self._refresh_visibility_text(checked)
        self.selected.emit()
        self.visibility_toggled.emit(checked)

    def _refresh_visibility_text(self, checked: bool) -> None:
        self.visibility_button.setText("ON" if checked else "OFF")


class LayerManagerPanel(QFrame):
    """Sidebar that manages preview-layer visibility and per-layer thickness."""

    _EXPANDED_MIN_WIDTH = 244
    _EXPANDED_MAX_WIDTH = 284
    _COLLAPSED_WIDTH = 40

    layer_visibility_changed = Signal(str, bool)
    layer_selected = Signal(object)
    layer_thickness_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("LayerDockPane")
        self._syncing = False
        self._is_collapsed = False
        self._row_widgets: dict[QTreeWidgetItem, _LayerRowWidget] = {}

        self.setStyleSheet(
            """
            QFrame#LayerDockPane {
                background: transparent;
                border-right: 1px solid #303030;
                border-radius: 0px;
            }
            QTreeWidget {
                background: transparent;
                border: none;
            }
            QTreeWidget::item {
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QFrame#LayerRowCard {
                background: #242424;
                border: 1px solid #303030;
                border-radius: 10px;
            }
            QFrame#LayerRowCard[selected="true"] {
                background: #2C2422;
                border: 1px solid #D45B2E;
            }
            QLabel#LayerRowTitle {
                color: #F0F0F0;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#LayerRowMeta {
                color: #8E8E8E;
                font-size: 11px;
            }
            QLabel#LayerThicknessPill {
                background: #1F1F1F;
                color: #D8D8D8;
                border: 1px solid #323232;
                border-radius: 8px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QToolButton#LayerVisibilityToggle {
                background: #1F1F1F;
                color: #7F7F7F;
                border: 1px solid #303030;
                border-radius: 8px;
                font-size: 10px;
                font-weight: 800;
            }
            QToolButton#LayerVisibilityToggle:checked {
                background: #204033;
                color: #DFF6E8;
                border: 1px solid #2E7C56;
            }
            QToolButton#LayerVisibilityToggle:hover {
                background: #292929;
            }
            QToolButton#LayerVisibilityToggle:checked:hover {
                background: #25533F;
            }
            QToolButton#LayerDockToggle {
                background: #202020;
                border: 1px solid #303030;
                border-radius: 8px;
                padding: 0px;
            }
            QToolButton#LayerDockToggle:hover {
                background: #292929;
            }
            """
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 2, 12, 0)
        self._layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)

        self.title_label = QLabel("Layers")
        self.title_label.setObjectName("SectionTitle")
        title_row.addWidget(self.title_label)

        self.visible_badge = QLabel("0 / 0 visible")
        self.visible_badge.setObjectName("SectionBadge")
        title_row.addWidget(self.visible_badge)
        title_row.addStretch(1)

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("LayerDockToggle")
        self.toggle_button.setFixedSize(QSize(26, 26))
        self.toggle_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.toggle_button.setToolTip("Collapse layer panel")
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.clicked.connect(self._toggle_collapsed)
        title_row.addWidget(self.toggle_button)
        self._layout.addLayout(title_row)

        self.summary = QLabel("Layers appear here after a DXF import.")
        self.summary.setObjectName("MutedLabel")
        self.summary.setWordWrap(True)
        self._layout.addWidget(self.summary)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(False)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tree.setVerticalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        self.tree.itemSelectionChanged.connect(self._handle_selection_changed)
        self.tree.itemDoubleClicked.connect(self._handle_item_double_clicked)
        self._layout.addWidget(self.tree, stretch=1)
        self._set_collapsed(False)

    def load_document(self, document: ProjectDocument | None) -> None:
        self._syncing = True
        self.tree.clear()
        self._row_widgets.clear()

        if document is None:
            self.tree.setEnabled(False)
            self.visible_badge.setText("0 / 0 visible")
            self.summary.setText("Layers appear here after a DXF import.")
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
            self.visible_badge.setText("0 / 0 visible")
            self.summary.setText("No populated DXF layers are currently imported.")
            self._syncing = False
            return

        active_names = {str(layer["name"]) for layer in active_layers}
        visible_count = len(active_names & visible_layers)
        skipped_count = max(len(populated_layers) - len(active_layers), 0)
        remapped_count = len(document.layer_mapping_overrides)
        self.visible_badge.setText(f"{visible_count} / {len(active_layers)} visible")
        summary = "A lightweight layer switcher. Double-click a row only when you need thickness edits."
        if skipped_count or remapped_count:
            summary = (
                f"{skipped_count} skipped at import, {remapped_count} remapped. "
                "This sidebar only controls what the viewer shows."
            )
        self.summary.setText(summary)
        selected_item: QTreeWidgetItem | None = None

        for layer in active_layers:
            layer_name = str(layer["name"])
            item = QTreeWidgetItem(self.tree)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            item.setData(0, Qt.ItemDataRole.UserRole, layer_name)
            role_label = format_layer_role(layer.get("suggested_role") or layer.get("mapped_type"))
            thickness_editable = layer_supports_stacked_preview(layer)
            thickness = document.layer_thicknesses.get(layer_name)
            if thickness_editable:
                thickness_label = "Set" if thickness is None else f"{thickness:.3f}"
            else:
                thickness_label = "N/A"
            row_widget = _LayerRowWidget(
                layer_name=layer_name,
                role_label=role_label,
                layer_color=document.layer_colors.get(layer_name, "#D45B2E"),
                thickness_label=thickness_label,
                is_visible=layer_name in visible_layers,
                thickness_editable=thickness_editable,
            )
            row_widget.selected.connect(lambda row=item: self.tree.setCurrentItem(row))
            row_widget.visibility_toggled.connect(
                lambda checked, name=layer_name: self._handle_row_visibility_toggled(name, checked)
            )
            row_widget.thickness_requested.connect(
                lambda name=layer_name: self._handle_row_thickness_requested(name)
            )
            item.setSizeHint(0, QSize(220, 56))
            self.tree.setItemWidget(item, 0, row_widget)
            self._row_widgets[item] = row_widget
            if document.selected_layer_name == layer_name:
                selected_item = item

        if selected_item is not None:
            self.tree.setCurrentItem(selected_item)
        self._refresh_row_selection()
        self._syncing = False

    def _handle_row_visibility_toggled(self, layer_name: str, visible: bool) -> None:
        if self._syncing:
            return
        self.layer_visibility_changed.emit(layer_name, visible)

    def _handle_selection_changed(self) -> None:
        self._refresh_row_selection()
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

    def _handle_row_thickness_requested(self, layer_name: str) -> None:
        if self._syncing:
            return
        self.layer_thickness_requested.emit(layer_name)

    def _refresh_row_selection(self) -> None:
        current_item = self.tree.currentItem()
        for item, row_widget in self._row_widgets.items():
            row_widget.set_selected(item is current_item)

    def _toggle_collapsed(self) -> None:
        self._set_collapsed(not self._is_collapsed)

    def _set_collapsed(self, collapsed: bool) -> None:
        self._is_collapsed = collapsed
        self.title_label.setVisible(not collapsed)
        self.visible_badge.setVisible(not collapsed)
        self.summary.setVisible(not collapsed)
        self.tree.setVisible(not collapsed)

        if collapsed:
            self.setMinimumWidth(self._COLLAPSED_WIDTH)
            self.setMaximumWidth(self._COLLAPSED_WIDTH)
            self._layout.setContentsMargins(0, 2, 6, 0)
            self._layout.setSpacing(0)
            self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_button.setToolTip("Expand layer panel")
            return

        self.setMinimumWidth(self._EXPANDED_MIN_WIDTH)
        self.setMaximumWidth(self._EXPANDED_MAX_WIDTH)
        self._layout.setContentsMargins(0, 2, 12, 0)
        self._layout.setSpacing(12)
        self.toggle_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.toggle_button.setToolTip("Collapse layer panel")


__all__ = ["LayerManagerPanel"]
