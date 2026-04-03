"""Semantic object and review sidebar widgets."""

from __future__ import annotations

from collections import defaultdict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
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

        self.content_stack = QStackedWidget(self)

        self.overview_page = QWidget(self)
        overview_layout = QVBoxLayout(self.overview_page)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(10)

        self.overview_hint = QLabel("Recognized objects and review items will appear here after import.")
        self.overview_hint.setObjectName("MutedLabel")
        self.overview_hint.setWordWrap(True)
        overview_layout.addWidget(self.overview_hint)

        self.review_callout = QFrame(self.overview_page)
        self.review_callout.setFrameShape(QFrame.Shape.NoFrame)
        review_callout_layout = QHBoxLayout(self.review_callout)
        review_callout_layout.setContentsMargins(0, 0, 0, 0)
        review_callout_layout.setSpacing(8)

        self.review_hint_badge = QLabel("Review Queue")
        self.review_hint_badge.setObjectName("SectionBadge")
        review_callout_layout.addWidget(self.review_hint_badge, alignment=Qt.AlignmentFlag.AlignTop)

        self.review_hint_label = QLabel("Items that need a manual confirmation will appear here.")
        self.review_hint_label.setObjectName("MutedLabel")
        self.review_hint_label.setWordWrap(True)
        review_callout_layout.addWidget(self.review_hint_label, stretch=1)

        self.review_callout.hide()
        overview_layout.addWidget(self.review_callout)

        overview_actions = QHBoxLayout()
        overview_actions.setContentsMargins(0, 0, 0, 0)
        overview_actions.setSpacing(8)

        self.open_objects_button = QPushButton("Browse Objects", self.overview_page)
        self.open_objects_button.setObjectName("SecondaryButton")
        self.open_objects_button.clicked.connect(lambda: self._open_detail_view("objects"))
        overview_actions.addWidget(self.open_objects_button)

        self.open_review_button = QPushButton("Open Review", self.overview_page)
        self.open_review_button.setObjectName("SecondaryButton")
        self.open_review_button.clicked.connect(lambda: self._open_detail_view("review"))
        overview_actions.addWidget(self.open_review_button)
        overview_actions.addStretch(1)
        overview_layout.addLayout(overview_actions)

        self.detail_page = QWidget(self)
        detail_layout = QVBoxLayout(self.detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(10)

        detail_header_row = QHBoxLayout()
        detail_header_row.setContentsMargins(0, 0, 0, 0)
        detail_header_row.setSpacing(8)

        self.detail_title = QLabel("Recognized objects")
        self.detail_title.setObjectName("SectionTitle")
        detail_header_row.addWidget(self.detail_title)
        detail_header_row.addStretch(1)

        self.back_to_overview_button = QToolButton(self.detail_page)
        self.back_to_overview_button.setObjectName("SecondaryButton")
        self.back_to_overview_button.setText("Overview")
        self.back_to_overview_button.setToolTip("Return to the recognition summary")
        self.back_to_overview_button.clicked.connect(self._show_overview)
        detail_header_row.addWidget(self.back_to_overview_button)
        detail_layout.addLayout(detail_header_row)

        self.detail_hint = QLabel("Select one item to inspect it in the 2D preview.")
        self.detail_hint.setObjectName("MutedLabel")
        self.detail_hint.setWordWrap(True)
        detail_layout.addWidget(self.detail_hint)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(8)

        self.object_mode_button = self._build_mode_button(self.detail_page)
        self.object_mode_button.clicked.connect(lambda: self._set_active_view("objects"))
        mode_row.addWidget(self.object_mode_button)

        self.review_mode_button = self._build_mode_button(self.detail_page)
        self.review_mode_button.clicked.connect(lambda: self._set_active_view("review"))
        mode_row.addWidget(self.review_mode_button)
        mode_row.addStretch(1)
        detail_layout.addLayout(mode_row)

        self.mode_stack = QStackedWidget(self)
        self.object_tree = self._build_tree()
        self.review_tree = self._build_tree()
        self.review_tree.setHeaderLabels(["Review", "Layer"])
        self.mode_stack.addWidget(self.object_tree)
        self.mode_stack.addWidget(self.review_tree)
        detail_layout.addWidget(self.mode_stack, stretch=1)

        self.content_stack.addWidget(self.overview_page)
        self.content_stack.addWidget(self.detail_page)
        layout.addWidget(self.content_stack, stretch=1)

        self.object_tree.itemSelectionChanged.connect(self._handle_tree_selection_changed)
        self.review_tree.itemSelectionChanged.connect(self._handle_tree_selection_changed)
        self.review_tree.itemDoubleClicked.connect(self._handle_review_item_double_clicked)
        self._show_overview()

    def load_document(self, document: ProjectDocument | None) -> None:
        self._syncing = True
        self.object_tree.clear()
        self.review_tree.clear()

        if document is None or document.semantic_result is None:
            self.object_badge.setText("0 found")
            self.review_badge.setText("0 review")
            self.summary.setText("Import a DXF to inspect recognized objects.")
            self.overview_hint.setText("Recognized objects and review items will appear here after import.")
            self.review_callout.hide()
            self._update_mode_buttons(entity_count=0, review_count=0)
            self.open_objects_button.hide()
            self.open_review_button.hide()
            self._show_overview()
            self._syncing = False
            return

        result = document.semantic_result
        self.object_badge.setText(f"{len(result.entities)} found")
        self.review_badge.setText(f"{len(result.review)} review")
        if result.review:
            self.summary.setText(
                f"{len(result.entities)} objects recognized. {len(result.review)} items need review. "
                "Double-click a Review item to classify it."
            )
        elif result.entities:
            self.summary.setText(
                f"{len(result.entities)} objects recognized. Select one to highlight it in the 2D preview."
            )
            self.overview_hint.setText(
                "Recognition results are available. Open the object list when you want to inspect or cross-check a match."
            )
        else:
            self.summary.setText("Recognized objects will appear here after import.")
            self.overview_hint.setText("No recognized objects are available for this import yet.")
        self._update_review_callout(result.review)
        self._update_mode_buttons(entity_count=len(result.entities), review_count=len(result.review))
        self.open_objects_button.setVisible(bool(result.entities))
        self.open_review_button.setVisible(bool(result.review))
        self.open_objects_button.setText(f"Browse Objects ({len(result.entities)})")
        self.open_review_button.setText(f"Open Review ({len(result.review)})")

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
            self.review_tree.setCurrentItem(selected_review_item)
            self._open_detail_view("review")
        elif selected_object_item is not None:
            self.object_tree.setCurrentItem(selected_object_item)
            self._open_detail_view("objects")
        else:
            self._show_overview()

        self._syncing = False

    def _build_mode_button(self, parent: QWidget | None = None) -> QToolButton:
        button = QToolButton(parent or self)
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setObjectName("SemanticModeButton")
        button.setStyleSheet(
            """
            QToolButton#SemanticModeButton {
                background: #202020;
                color: #BEBEBE;
                border: 1px solid #303030;
                border-radius: 999px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QToolButton#SemanticModeButton:hover {
                background: #272727;
                color: #F0F0F0;
            }
            QToolButton#SemanticModeButton:checked {
                background: #2F2F2F;
                color: #FFFFFF;
                border-color: #494949;
            }
            QToolButton#SemanticModeButton:disabled {
                background: #1D1D1D;
                color: #757575;
                border-color: #272727;
            }
            """
        )
        return button

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

    def _update_review_callout(self, items: list[SemanticCandidate]) -> None:
        if not items:
            self.review_callout.hide()
            return

        next_item = min(items, key=lambda item: (item.layer_name, -item.confidence, item.id))
        next_label = self._display_name(next_item)
        if len(items) == 1:
            text = (
                f"1 item is waiting for confirmation. Start with {next_label} on {next_item.layer_name}. "
                "Double-click it in Review to classify it."
            )
        else:
            text = (
                f"{len(items)} items are waiting for confirmation. Start with {next_label} on {next_item.layer_name}. "
                "Double-click a Review row to classify it."
            )
        self.review_hint_label.setText(text)
        self.review_callout.show()

    def _update_mode_buttons(self, *, entity_count: int, review_count: int) -> None:
        self.object_mode_button.setText(f"Objects {entity_count}")
        self.object_mode_button.setToolTip(f"{entity_count} recognized objects")
        self.object_mode_button.setEnabled(entity_count > 0)

        self.review_mode_button.setText(f"Review {review_count}")
        self.review_mode_button.setToolTip(f"{review_count} items need confirmation")
        self.review_mode_button.setEnabled(review_count > 0)

    def _show_overview(self) -> None:
        self.content_stack.setCurrentWidget(self.overview_page)

    def _open_detail_view(self, mode: str) -> None:
        self.content_stack.setCurrentWidget(self.detail_page)
        self._set_active_view(mode)

    def _set_active_view(self, mode: str) -> None:
        show_review = mode == "review"
        if show_review and not self.review_mode_button.isEnabled():
            show_review = False
        if not show_review and not self.object_mode_button.isEnabled() and self.review_mode_button.isEnabled():
            show_review = True

        self.object_mode_button.setChecked(not show_review)
        self.review_mode_button.setChecked(show_review)
        self.mode_stack.setCurrentWidget(self.review_tree if show_review else self.object_tree)
        if show_review:
            self.detail_title.setText("Review queue")
            self.detail_hint.setText("Double-click a review row to classify it and confirm the recognition.")
        else:
            self.detail_title.setText("Recognized objects")
            self.detail_hint.setText("Select one item to inspect it in the 2D preview.")

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
