"""Semantic object and review sidebar widgets."""

from __future__ import annotations

from collections import defaultdict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from core.semantic import SemanticCandidate, SemanticEntity
from services import ProjectDocument

ITEM_KEY_ROLE = Qt.ItemDataRole.UserRole
ITEM_OBJECT_ROLE = Qt.ItemDataRole.UserRole + 1


class SemanticObjectsPanel(QFrame):
    """Sidebar that shows recognized semantic objects and review candidates."""

    semantic_item_selected = Signal(object)
    review_override_requested = Signal(object)
    preset_manage_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumWidth(270)
        self.setMaximumWidth(320)
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_row = QFrame(self)
        title_row.setFrameShape(QFrame.Shape.NoFrame)
        title_layout = QVBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        title = QLabel("Objects")
        title.setObjectName("SectionTitle")
        top_row.addWidget(title)

        self.object_badge = QLabel("0 found")
        self.object_badge.setObjectName("SectionBadge")
        top_row.addWidget(self.object_badge)

        self.review_badge = QLabel("0 review")
        self.review_badge.setObjectName("SectionBadge")
        top_row.addWidget(self.review_badge)
        top_row.addStretch(1)

        self.manage_presets_button = QToolButton(self)
        self.manage_presets_button.setObjectName("SecondaryButton")
        self.manage_presets_button.setText("Presets")
        self.manage_presets_button.setToolTip("Manage semantic presets")
        self.manage_presets_button.clicked.connect(self.preset_manage_requested.emit)
        top_row.addWidget(self.manage_presets_button, alignment=Qt.AlignmentFlag.AlignRight)
        title_layout.addLayout(top_row)

        layout.addWidget(title_row)

        self.summary = QLabel("Import a DXF to inspect recognized objects.")
        self.summary.setObjectName("MutedLabel")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.tabs = QTabWidget(self)
        self.object_tree = self._build_tree()
        self.review_tree = self._build_tree()
        self.tabs.addTab(self.object_tree, "Objects")
        self.tabs.addTab(self.review_tree, "Confirm")
        layout.addWidget(self.tabs, stretch=1)

        self.object_tree.itemSelectionChanged.connect(self._handle_tree_selection_changed)
        self.review_tree.itemSelectionChanged.connect(self._handle_tree_selection_changed)
        self.review_tree.itemDoubleClicked.connect(self._handle_review_item_double_clicked)

    def load_document(self, document: ProjectDocument | None) -> None:
        self._syncing = True
        self.object_tree.clear()
        self.review_tree.clear()

        if document is None or document.semantic_result is None:
            self.tabs.setEnabled(False)
            self.object_badge.setText("0 found")
            self.review_badge.setText("0 review")
            self.summary.setText("Import a DXF to inspect recognized objects.")
            self.tabs.setTabText(0, "Objects")
            self.tabs.setTabText(1, "Confirm")
            self._syncing = False
            return

        result = document.semantic_result
        self.tabs.setEnabled(True)
        self.object_badge.setText(f"{len(result.entities)} found")
        self.review_badge.setText(f"{len(result.review)} review")
        if result.review:
            self.summary.setText(
                f"{len(result.entities)} objects recognized. {len(result.review)} items need review. "
                "Double-click a Confirm item to classify it."
            )
        elif result.entities:
            self.summary.setText(
                f"{len(result.entities)} objects recognized. Select one to highlight it in the 2D preview."
            )
        else:
            self.summary.setText("Recognized objects will appear here after import.")
        self.tabs.setTabText(0, f"Objects ({len(result.entities)})")
        self.tabs.setTabText(1, f"Confirm ({len(result.review)})")

        selected_object_item = self._populate_tree(
            self.object_tree,
            result.entities,
            key_prefix="entity",
            selected_key=document.selected_semantic_key,
        )
        selected_review_item = self._populate_tree(
            self.review_tree,
            result.review,
            key_prefix="review",
            selected_key=document.selected_semantic_key,
        )

        if selected_review_item is not None:
            self.tabs.setCurrentWidget(self.review_tree)
            self.review_tree.setCurrentItem(selected_review_item)
        elif selected_object_item is not None:
            self.tabs.setCurrentWidget(self.object_tree)
            self.object_tree.setCurrentItem(selected_object_item)
        elif result.entities:
            self.tabs.setCurrentWidget(self.object_tree)
        else:
            self.tabs.setCurrentWidget(self.review_tree)

        self._syncing = False

    def _build_tree(self) -> QTreeWidget:
        tree = QTreeWidget(self)
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Object", "Layer"])
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setUniformRowHeights(True)
        tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        tree.header().setStretchLastSection(False)
        tree.header().resizeSection(0, 176)
        tree.header().resizeSection(1, 108)
        return tree

    def _populate_tree(
        self,
        tree: QTreeWidget,
        items: list[SemanticEntity] | list[SemanticCandidate],
        *,
        key_prefix: str,
        selected_key: str | None,
    ) -> QTreeWidgetItem | None:
        groups: dict[str, list[SemanticEntity | SemanticCandidate]] = defaultdict(list)
        for item in items:
            groups[self._display_kind(item.kind)].append(item)

        selected_item: QTreeWidgetItem | None = None
        for kind_label in sorted(groups):
            group_items = sorted(
                groups[kind_label],
                key=lambda item: (item.layer_name, -item.confidence, item.id),
            )
            group = QTreeWidgetItem(tree)
            group.setText(0, f"{kind_label} ({len(group_items)})")
            group.setFirstColumnSpanned(True)
            group.setExpanded(True)
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)

            for semantic_item in group_items:
                child = QTreeWidgetItem(group)
                key = f"{key_prefix}:{semantic_item.id}"
                child.setText(0, self._display_name(semantic_item))
                child.setText(1, semantic_item.layer_name)
                child.setData(0, ITEM_KEY_ROLE, key)
                child.setData(0, ITEM_OBJECT_ROLE, semantic_item)
                if key == selected_key:
                    selected_item = child

        return selected_item

    def _handle_tree_selection_changed(self) -> None:
        if self._syncing:
            return

        current_tree = self.sender()
        if current_tree not in {self.object_tree, self.review_tree}:
            return

        other_tree = self.review_tree if current_tree is self.object_tree else self.object_tree
        self._syncing = True
        other_tree.clearSelection()
        self._syncing = False

        item = current_tree.currentItem()
        if item is None or item.childCount() > 0:
            self.semantic_item_selected.emit(None)
            return

        key = item.data(0, ITEM_KEY_ROLE)
        semantic_item = item.data(0, ITEM_OBJECT_ROLE)
        if isinstance(key, str) and semantic_item is not None:
            self.semantic_item_selected.emit({"key": key, "item": semantic_item})
            return

        self.semantic_item_selected.emit(None)

    def _handle_review_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._syncing or item.childCount() > 0:
            return

        key = item.data(0, ITEM_KEY_ROLE)
        semantic_item = item.data(0, ITEM_OBJECT_ROLE)
        if isinstance(key, str) and semantic_item is not None:
            self.review_override_requested.emit({"key": key, "item": semantic_item})

    def _display_kind(self, kind: str) -> str:
        return kind.removesuffix("_candidate").replace("_", " ").title()

    def _display_name(self, semantic_item: SemanticEntity | SemanticCandidate) -> str:
        label = self._display_kind(semantic_item.kind)
        details: list[str] = []

        side = semantic_item.properties.get("side")
        if isinstance(side, str) and side:
            details.append(side.title())

        pad_kind = semantic_item.properties.get("pad_kind")
        if isinstance(pad_kind, str) and pad_kind:
            details.append(pad_kind.title())

        shape = semantic_item.properties.get("shape")
        if isinstance(shape, str) and shape and shape.title() not in details:
            details.append(shape.lower())

        hole_kind = semantic_item.properties.get("hole_kind")
        if isinstance(hole_kind, str) and hole_kind:
            details.append(hole_kind.replace("_", " ").lower())

        if details:
            return f"{label} ({', '.join(details)})"
        return label

__all__ = ["SemanticObjectsPanel"]
