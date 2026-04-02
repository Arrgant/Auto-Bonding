"""2D DXF preview widget."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGraphicsItem, QGraphicsScene, QGraphicsView

from core.layer_colors import build_layer_color_map, tint_color
from core.layer_stack import build_layer_order_map
from core.preview_entities import build_preview_entities
from core.raw_dxf_types import RawEntity
from services import ProjectDocument

from .viewer_placeholder import ViewerPlaceholder

ENTITY_INDEX_ROLE = 0
ENTITY_CLOSED_ROLE = 1
LAYER_NAME_ROLE = 2
SOURCE_COUNT_ROLE = 3
SOURCE_INDICES_ROLE = 4


class DXFPreviewView(QGraphicsView):
    """2D DXF preview area with layer ordering and entity selection."""

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._scene_rect = QRectF(-400.0, -300.0, 800.0, 600.0)
        self._has_content = False
        self._item_styles: dict[QGraphicsItem, dict[str, Any]] = {}
        self._selection_override: int | None = None
        self._layer_colors: dict[str, str] = {}

        self.file_drop_handler: Callable[[Path], None] | None = None
        self.import_requested_handler: Callable[[], None] | None = None
        self.selection_changed_handler: Callable[[int | None], None] | None = None
        self.closed_shape_click_handler: Callable[[int], None] | None = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#161616"))
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        self.placeholder = ViewerPlaceholder(
            "2D Preview",
            "Import a DXF or drop it here.",
            "dxf",
            self.viewport(),
            action_text="Import DXF",
        )
        self.placeholder.setAcceptDrops(True)
        self.placeholder.hide()
        self.viewport().installEventFilter(self)
        self.placeholder.installEventFilter(self)
        self.placeholder.action_requested.connect(self._handle_import_requested)
        self._scene.selectionChanged.connect(self._handle_selection_changed)

    def load_document(self, document: ProjectDocument | None) -> None:
        self._scene.clear()
        self._item_styles.clear()
        self._has_content = False

        if document is None or not document.raw_entities:
            self.placeholder.set_content("2D Preview", "Import a DXF or drop it here.")
            self.placeholder.set_action("Import DXF")
            self._scene.setSceneRect(self._scene_rect)
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.placeholder.show()
            self._position_placeholder()
            return

        visible_layers = set(document.visible_layers)
        rendered_count = 0
        layer_order = build_layer_order_map(document.layer_info, document.raw_entities)
        self._layer_colors = dict(document.layer_colors) or build_layer_color_map(
            document.layer_info,
            document.raw_entities,
        )
        for preview_entity in build_preview_entities(document.raw_entities, document.layer_info):
            layer_name = str(preview_entity.entity.get("layer", "0"))
            if layer_name not in visible_layers:
                continue
            item = self._draw_entity(
                preview_entity.entity,
                preview_entity.entity_index,
                source_count=len(preview_entity.source_indices),
                source_indices=preview_entity.source_indices,
            )
            if item is not None:
                item.setZValue(float(layer_order.get(layer_name, 0)))
                rendered_count += 1

        self._scene_rect = QRectF(*document.scene_rect)
        self._scene.setSceneRect(self._scene_rect)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._has_content = rendered_count > 0
        if rendered_count <= 0:
            self.placeholder.set_content("2D Preview", "All layers are hidden. Re-enable one from Layers.")
            self.placeholder.set_action(None)
            self.placeholder.show()
            self._position_placeholder()
            return

        self._apply_layer_focus(document.selected_layer_name)
        if document.selected_entity_index is not None:
            self.focus_entity(document.selected_entity_index, center=False)
        self.placeholder.hide()

    def resizeEvent(self, event) -> None:  # pragma: no cover
        super().resizeEvent(event)
        if self._has_content:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._position_placeholder()

    def mousePressEvent(self, event) -> None:  # pragma: no cover
        super().mousePressEvent(event)

        if event.button() != Qt.MouseButton.LeftButton:
            return

        item = self.itemAt(event.position().toPoint())
        if item is None:
            return

        if bool(item.data(ENTITY_CLOSED_ROLE)) and self.closed_shape_click_handler is not None:
            entity_index = item.data(ENTITY_INDEX_ROLE)
            if isinstance(entity_index, int):
                self.closed_shape_click_handler(entity_index)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # pragma: no cover
        painter.fillRect(rect, QColor("#161616"))

        minor_pen = QPen(QColor("#252525"))
        major_pen = QPen(QColor("#2F2F2F"))
        minor_pen.setWidthF(0.0)
        major_pen.setWidthF(0.0)

        left = int(math.floor(rect.left() / 20.0) * 20)
        right = int(math.ceil(rect.right() / 20.0) * 20)
        top = int(math.floor(rect.top() / 20.0) * 20)
        bottom = int(math.ceil(rect.bottom() / 20.0) * 20)

        for x_value in range(left, right + 1, 20):
            painter.setPen(major_pen if x_value % 100 == 0 else minor_pen)
            painter.drawLine(QLineF(float(x_value), rect.top(), float(x_value), rect.bottom()))

        for y_value in range(top, bottom + 1, 20):
            painter.setPen(major_pen if y_value % 100 == 0 else minor_pen)
            painter.drawLine(QLineF(rect.left(), float(y_value), rect.right(), float(y_value)))

    def _position_placeholder(self) -> None:
        x_pos = (self.viewport().width() - self.placeholder.width()) // 2
        y_pos = (self.viewport().height() - self.placeholder.height()) // 2
        self.placeholder.move(max(0, x_pos), max(0, y_pos))

    def set_import_action_enabled(self, enabled: bool) -> None:
        if not self.placeholder.action_button.isVisible():
            return
        self.placeholder.set_action(self.placeholder.action_button.text(), enabled=enabled)

    def dragEnterEvent(self, event) -> None:  # pragma: no cover
        if self._extract_dxf_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # pragma: no cover
        if self._extract_dxf_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # pragma: no cover
        paths = self._extract_dxf_paths(event.mimeData())
        if not paths:
            event.ignore()
            return

        event.acceptProposedAction()
        if self.file_drop_handler is not None:
            self.file_drop_handler(paths[0])

    def eventFilter(self, watched, event) -> bool:  # pragma: no cover
        if watched in {self.viewport(), self.placeholder}:
            if event.type() in {QEvent.Type.DragEnter, QEvent.Type.DragMove}:
                if self._extract_dxf_paths(event.mimeData()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                paths = self._extract_dxf_paths(event.mimeData())
                if paths:
                    event.acceptProposedAction()
                    if self.file_drop_handler is not None:
                        self.file_drop_handler(paths[0])
                    return True
        return super().eventFilter(watched, event)

    def _handle_import_requested(self) -> None:
        if self.import_requested_handler is not None:
            self.import_requested_handler()

    def _extract_dxf_paths(self, mime_data) -> list[Path]:
        if not mime_data or not mime_data.hasUrls():
            return []

        paths: list[Path] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            file_path = Path(url.toLocalFile())
            if file_path.suffix.lower() == ".dxf":
                paths.append(file_path)
        return paths

    def _make_style(
        self,
        stroke_color: str,
        *,
        width: float,
        fill_color: str | None = None,
    ) -> dict[str, Any]:
        pen = QPen(QColor(stroke_color))
        pen.setWidthF(width)
        pen.setCosmetic(True)

        selected_pen = QPen(QColor("#FFD166"))
        selected_pen.setWidthF(width + 1.25)
        selected_pen.setCosmetic(True)

        brush = QBrush(Qt.BrushStyle.NoBrush)
        selected_brush = QBrush(Qt.BrushStyle.NoBrush)
        if fill_color is not None:
            fill = QColor(fill_color)
            fill.setAlpha(72)
            brush = QBrush(fill)

            selected_fill = QColor("#FFB703")
            selected_fill.setAlpha(110)
            selected_brush = QBrush(selected_fill)

        return {
            "pen": pen,
            "selected_pen": selected_pen,
            "brush": brush,
            "selected_brush": selected_brush,
        }

    def _register_item(
        self,
        item: QGraphicsItem,
        entity_index: int,
        layer_name: str,
        style: dict[str, Any],
        *,
        is_closed: bool,
        source_count: int,
        source_indices: tuple[int, ...],
    ) -> QGraphicsItem:
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        item.setData(ENTITY_INDEX_ROLE, entity_index)
        item.setData(ENTITY_CLOSED_ROLE, is_closed)
        item.setData(LAYER_NAME_ROLE, layer_name)
        item.setData(SOURCE_COUNT_ROLE, source_count)
        item.setData(SOURCE_INDICES_ROLE, source_indices)
        item.setPen(style["pen"])
        if hasattr(item, "setBrush"):
            item.setBrush(style["brush"])
        self._item_styles[item] = style
        return item

    def _handle_selection_changed(self) -> None:
        selected_index: int | None = None
        selected_items = set(self._scene.selectedItems())

        for item, style in self._item_styles.items():
            is_selected = item in selected_items
            item.setPen(style["selected_pen"] if is_selected else style["pen"])
            if hasattr(item, "setBrush"):
                item.setBrush(style["selected_brush"] if is_selected else style["brush"])
            if is_selected and selected_index is None:
                source_indices = item.data(SOURCE_INDICES_ROLE)
                if (
                    isinstance(self._selection_override, int)
                    and isinstance(source_indices, tuple)
                    and self._selection_override in source_indices
                ):
                    selected_index = self._selection_override
                else:
                    entity_index = item.data(ENTITY_INDEX_ROLE)
                    if isinstance(entity_index, int):
                        selected_index = entity_index

        self._selection_override = None

        if self.selection_changed_handler is not None:
            self.selection_changed_handler(selected_index)

    def _apply_layer_focus(self, layer_name: str | None) -> None:
        if not layer_name:
            for item in self._item_styles:
                item.setOpacity(1.0)
            return

        for item in self._item_styles:
            item_layer = item.data(LAYER_NAME_ROLE)
            item.setOpacity(1.0 if item_layer == layer_name else 0.22)

    def focus_entity(self, entity_index: int | None, *, center: bool = True) -> None:
        self._selection_override = entity_index
        self._scene.clearSelection()

        if entity_index is None:
            return

        for item in self._item_styles:
            source_indices = item.data(SOURCE_INDICES_ROLE)
            if isinstance(source_indices, tuple) and entity_index in source_indices:
                item.setSelected(True)
                item.setFocus()
                if center:
                    self.centerOn(item)
                return

    def _draw_entity(
        self,
        entity: RawEntity,
        entity_index: int,
        *,
        source_count: int = 1,
        source_indices: tuple[int, ...] = (),
    ) -> QGraphicsItem | None:
        layer_name = str(entity.get("layer", "0"))
        layer_color = self._layer_colors.get(layer_name, "#E8E8E8")

        entity_type = entity["type"]
        if entity_type == "LINE":
            style = self._make_style(layer_color, width=1.0 if source_count <= 1 else 2.6)
            x1, y1 = entity["start"]
            x2, y2 = entity["end"]
            item = self._scene.addLine(x1, -y1, x2, -y2, style["pen"])
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=False,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "CIRCLE":
            style = self._make_style(layer_color, width=1.7, fill_color=tint_color(layer_color, ratio=0.18))
            center_x, center_y = entity["center"]
            radius = entity["radius"]
            item = self._scene.addEllipse(
                center_x - radius,
                -(center_y + radius),
                radius * 2.0,
                radius * 2.0,
                style["pen"],
                style["brush"],
            )
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=True,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "ARC":
            points = entity.get("points") or []
            if len(points) < 2:
                return None
            style = self._make_style(layer_color, width=1.3)
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            item = self._scene.addPath(path, style["pen"])
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=False,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "LWPOLYLINE":
            points = entity.get("points") or []
            if len(points) < 2:
                return None
            is_closed = bool(entity.get("closed"))
            style = self._make_style(
                layer_color,
                width=2.1 if is_closed else 1.8,
                fill_color=tint_color(layer_color, ratio=0.16) if is_closed else None,
            )
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            if is_closed:
                path.closeSubpath()
            item = self._scene.addPath(path, style["pen"], style["brush"])
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=is_closed,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "POINT":
            style = self._make_style(layer_color, width=1.1, fill_color=tint_color(layer_color, ratio=0.2))
            x_value, y_value = entity["location"]
            item = self._scene.addEllipse(
                x_value - 1.8,
                -(y_value + 1.8),
                3.6,
                3.6,
                style["pen"],
                style["brush"],
            )
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=False,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        return None
