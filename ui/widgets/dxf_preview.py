"""2D DXF preview widget."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGraphicsItem, QGraphicsScene, QGraphicsView, QLabel

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
        self._layer_linetypes: dict[str, str] = {}
        self._current_document: ProjectDocument | None = None
        self._focused_layer_name: str | None = None
        self._selected_entity_index: int | None = None

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

        self.focus_banner = QLabel(self.viewport())
        self.focus_banner.setObjectName("ViewerInfoBadge")
        self.focus_banner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.focus_banner.hide()

    def load_document(self, document: ProjectDocument | None) -> None:
        self._current_document = document
        self._scene.clear()
        self._item_styles.clear()
        self._has_content = False

        if document is None or not document.raw_entities:
            self._focused_layer_name = None
            self._selected_entity_index = None
            self.placeholder.set_content("2D Preview", "Import a DXF or drop it here.")
            self.placeholder.set_action("Import DXF")
            self._scene.setSceneRect(self._scene_rect)
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.placeholder.show()
            self.focus_banner.hide()
            self._position_placeholder()
            return

        visible_layers = set(document.visible_layers)
        rendered_count = 0
        layer_order = build_layer_order_map(document.layer_info, document.raw_entities)
        self._layer_colors = dict(document.layer_colors) or build_layer_color_map(
            document.layer_info,
            document.raw_entities,
        )
        self._layer_linetypes = {
            str(layer.get("name", "0")): str(layer.get("linetype", "CONTINUOUS"))
            for layer in document.layer_info
        }
        for preview_entity in build_preview_entities(document.raw_entities, document.layer_info):
            layer_name = str(preview_entity.entity.get("layer", "0"))
            if layer_name not in visible_layers:
                continue
            item = self._draw_entity(
                preview_entity.entity,
                preview_entity.entity_index,
                source_count=len(preview_entity.source_indices),
                source_indices=preview_entity.source_indices,
                z_value=float(layer_order.get(layer_name, 0)),
            )
            if item is not None:
                rendered_count += 1

        self._scene_rect = QRectF(*document.scene_rect)
        self._scene.setSceneRect(self._scene_rect)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._has_content = rendered_count > 0
        if rendered_count <= 0:
            self._focused_layer_name = None
            self._selected_entity_index = None
            self.placeholder.set_content("2D Preview", "All layers are hidden. Re-enable one from Layers.")
            self.placeholder.set_action(None)
            self.placeholder.show()
            self.focus_banner.hide()
            self._position_placeholder()
            return

        self._apply_layer_focus(document.selected_layer_name)
        self._selected_entity_index = document.selected_entity_index
        if document.selected_entity_index is not None:
            self.focus_entity(document.selected_entity_index, center=False)
        self.placeholder.hide()
        self._update_focus_banner()

    def resizeEvent(self, event) -> None:  # pragma: no cover
        super().resizeEvent(event)
        if self._has_content:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._position_placeholder()
        self._position_focus_banner()

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

    def _position_focus_banner(self) -> None:
        self.focus_banner.move(14, 12)

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
        linetype_name: str = "CONTINUOUS",
        fill_alpha: int = 72,
        text_fill: bool = False,
    ) -> dict[str, Any]:
        pen = QPen(QColor(stroke_color))
        pen.setWidthF(width)
        pen.setCosmetic(True)
        pen.setStyle(self._resolve_pen_style(linetype_name))

        selected_pen = QPen(QColor("#FFD166"))
        selected_pen.setWidthF(width + 2.0)
        selected_pen.setCosmetic(True)
        selected_pen.setStyle(self._resolve_pen_style(linetype_name))

        brush = QBrush(Qt.BrushStyle.NoBrush)
        selected_brush = QBrush(Qt.BrushStyle.NoBrush)
        if fill_color is not None:
            fill = QColor(fill_color)
            fill.setAlpha(fill_alpha)
            brush = QBrush(fill)

            selected_fill = QColor("#FFB703")
            selected_fill.setAlpha(150)
            selected_brush = QBrush(selected_fill)
        elif text_fill:
            brush = QBrush(QColor(stroke_color))
            selected_brush = QBrush(QColor("#FFD166"))

        return {
            "pen": pen,
            "selected_pen": selected_pen,
            "brush": brush,
            "selected_brush": selected_brush,
        }

    def _resolve_pen_style(self, linetype_name: str) -> Qt.PenStyle:
        normalized_name = str(linetype_name or "CONTINUOUS").upper()
        if "PHANTOM" in normalized_name:
            return Qt.PenStyle.DashDotDotLine
        if "CENTER" in normalized_name:
            return Qt.PenStyle.DashDotLine
        if "DASH" in normalized_name or "HIDDEN" in normalized_name:
            return Qt.PenStyle.DashLine
        if "DOT" in normalized_name:
            return Qt.PenStyle.DotLine
        return Qt.PenStyle.SolidLine

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
        self._selected_entity_index = selected_index
        self._update_focus_banner()

        if self.selection_changed_handler is not None:
            self.selection_changed_handler(selected_index)

    def _apply_layer_focus(self, layer_name: str | None) -> None:
        self._focused_layer_name = layer_name
        if not layer_name:
            for item in self._item_styles:
                item.setOpacity(1.0)
            return

        for item in self._item_styles:
            item_layer = item.data(LAYER_NAME_ROLE)
            item.setOpacity(1.0 if item_layer == layer_name else 0.14)

    def focus_entity(self, entity_index: int | None, *, center: bool = True) -> None:
        self._selection_override = entity_index
        self._selected_entity_index = entity_index
        self._scene.clearSelection()

        if entity_index is None:
            self._update_focus_banner()
            return

        for item in self._item_styles:
            source_indices = item.data(SOURCE_INDICES_ROLE)
            if isinstance(source_indices, tuple) and entity_index in source_indices:
                item.setSelected(True)
                item.setFocus()
                if center:
                    self.centerOn(item)
                return

        self._update_focus_banner()

    def _update_focus_banner(self) -> None:
        if self._current_document is None or not self._has_content:
            self.focus_banner.hide()
            return

        banner_text: str | None = None
        if (
            isinstance(self._selected_entity_index, int)
            and 0 <= self._selected_entity_index < len(self._current_document.raw_entities)
        ):
            entity = self._current_document.raw_entities[self._selected_entity_index]
            layer_name = str(entity.get("layer", "0"))
            banner_text = f"Selected {entity['type']} on {layer_name}"
            thickness = self._current_document.entity_thicknesses.get(self._selected_entity_index)
            if thickness is not None:
                banner_text += f" | {thickness:.3f} mm"
        elif isinstance(self._focused_layer_name, str) and self._focused_layer_name:
            banner_text = f"Focused layer {self._focused_layer_name}"
            thickness = self._current_document.layer_thicknesses.get(self._focused_layer_name)
            if thickness is not None:
                banner_text += f" | {thickness:.3f} mm"

        if not banner_text:
            self.focus_banner.hide()
            return

        self.focus_banner.setText(banner_text)
        self.focus_banner.adjustSize()
        self._position_focus_banner()
        self.focus_banner.show()

    def _draw_entity(
        self,
        entity: RawEntity,
        entity_index: int,
        *,
        source_count: int = 1,
        source_indices: tuple[int, ...] = (),
        z_value: float | None = None,
    ) -> QGraphicsItem | None:
        layer_name = str(entity.get("layer", "0"))
        layer_color = self._layer_colors.get(layer_name, "#E8E8E8")
        layer_linetype = self._layer_linetypes.get(layer_name, "CONTINUOUS")

        if (
            self._current_document is not None
            and self._current_document.visible_layers
            and layer_name not in self._current_document.visible_layers
        ):
            return None

        entity_type = entity["type"]
        if entity_type == "LINE":
            style = self._make_style(
                layer_color,
                width=1.0 if source_count <= 1 else 2.6,
                linetype_name=layer_linetype,
            )
            x1, y1 = entity["start"]
            x2, y2 = entity["end"]
            item = self._scene.addLine(x1, -y1, x2, -y2, style["pen"])
            if z_value is not None:
                item.setZValue(z_value)
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
            style = self._make_style(
                layer_color,
                width=1.7,
                fill_color=tint_color(layer_color, ratio=0.18),
                linetype_name=layer_linetype,
            )
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
            if z_value is not None:
                item.setZValue(z_value)
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
            style = self._make_style(layer_color, width=1.3, linetype_name=layer_linetype)
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            item = self._scene.addPath(path, style["pen"])
            if z_value is not None:
                item.setZValue(z_value)
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=False,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "ELLIPSE":
            points = entity.get("points") or []
            if len(points) < 2:
                return None
            is_closed = bool(entity.get("closed"))
            style = self._make_style(
                layer_color,
                width=1.4,
                fill_color=tint_color(layer_color, ratio=0.18) if is_closed else None,
                linetype_name=layer_linetype,
            )
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            if is_closed:
                path.closeSubpath()
            item = self._scene.addPath(path, style["pen"], style["brush"])
            if z_value is not None:
                item.setZValue(z_value)
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=is_closed,
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
                linetype_name=layer_linetype,
            )
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            if is_closed:
                path.closeSubpath()
            item = self._scene.addPath(path, style["pen"], style["brush"])
            if z_value is not None:
                item.setZValue(z_value)
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
            style = self._make_style(
                layer_color,
                width=1.1,
                fill_color=tint_color(layer_color, ratio=0.2),
                linetype_name=layer_linetype,
            )
            x_value, y_value = entity["location"]
            item = self._scene.addEllipse(
                x_value - 1.8,
                -(y_value + 1.8),
                3.6,
                3.6,
                style["pen"],
                style["brush"],
            )
            if z_value is not None:
                item.setZValue(z_value)
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=False,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            text_value = str(entity.get("text") or "")
            if not text_value.strip():
                return None

            style = self._make_style(
                layer_color,
                width=0.6,
                linetype_name="CONTINUOUS",
                text_fill=True,
            )
            text_font = QFont("Segoe UI")
            text_font.setPointSizeF(12.0)
            item = self._scene.addSimpleText(text_value, text_font)
            text_height = max(float(entity.get("height", 1.0) or 1.0), 0.1)
            item_height = max(float(item.boundingRect().height()), 1e-6)
            item.setScale(text_height / item_height)

            insert_x, insert_y = entity["insert"]
            item.setPos(insert_x, -insert_y - text_height)
            item.setRotation(-float(entity.get("rotation", 0.0) or 0.0))
            if z_value is not None:
                item.setZValue(z_value)

            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=False,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "SOLID":
            points = entity.get("points") or []
            if len(points) < 3:
                return None

            style = self._make_style(
                layer_color,
                width=0.0,
                fill_color=tint_color(layer_color, ratio=0.26),
                linetype_name="CONTINUOUS",
                fill_alpha=104,
            )
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            path.closeSubpath()

            item = self._scene.addPath(path, style["pen"], style["brush"])
            if z_value is not None:
                item.setZValue(z_value)
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=True,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "HATCH":
            hatch_paths = entity.get("paths") or []
            if not hatch_paths:
                return None

            style = self._make_style(
                layer_color,
                width=0.0 if bool(entity.get("solid_fill", True)) else 0.8,
                fill_color=tint_color(layer_color, ratio=0.22),
                linetype_name="CONTINUOUS",
                fill_alpha=96,
            )
            painter_path = QPainterPath()
            for path_points in hatch_paths:
                if len(path_points) < 2:
                    continue
                painter_path.moveTo(path_points[0][0], -path_points[0][1])
                for x_value, y_value in path_points[1:]:
                    painter_path.lineTo(x_value, -y_value)
                painter_path.closeSubpath()

            if painter_path.isEmpty():
                return None

            item = self._scene.addPath(painter_path, style["pen"], style["brush"])
            if z_value is not None:
                item.setZValue(z_value)
            return self._register_item(
                item,
                entity_index,
                layer_name,
                style,
                is_closed=True,
                source_count=source_count,
                source_indices=source_indices or (entity_index,),
            )

        if entity_type == "INSERT":
            children = entity.get("entities") or []
            first_item: QGraphicsItem | None = None
            for child_entity in children:
                child_item = self._draw_entity(
                    child_entity,
                    entity_index,
                    source_count=source_count,
                    source_indices=source_indices or (entity_index,),
                    z_value=z_value,
                )
                if first_item is None and child_item is not None:
                    first_item = child_item
            return first_item

        return None
