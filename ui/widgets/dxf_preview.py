"""2D DXF preview widget."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from core.raw_dxf_types import RawEntity
from services import ProjectDocument

from .viewer_placeholder import ViewerPlaceholder


class DXFPreviewView(QGraphicsView):
    """2D DXF preview area."""

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._scene_rect = QRectF(-400.0, -300.0, 800.0, 600.0)
        self._has_content = False
        self.file_drop_handler: Callable[[Path], None] | None = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#161616"))
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        self.placeholder = ViewerPlaceholder("2D Preview", "Import DXF", "dxf", self.viewport())
        self.placeholder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.placeholder.setAcceptDrops(True)
        self.placeholder.hide()
        self.viewport().installEventFilter(self)
        self.placeholder.installEventFilter(self)

    def load_document(self, document: ProjectDocument | None) -> None:
        self._scene.clear()
        self._has_content = False

        if document is None or not document.raw_entities:
            self._scene.setSceneRect(self._scene_rect)
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.placeholder.show()
            self._position_placeholder()
            return

        for entity in document.raw_entities:
            self._draw_entity(entity)

        self._scene_rect = QRectF(*document.scene_rect)
        self._scene.setSceneRect(self._scene_rect)
        self._has_content = True
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.placeholder.hide()

    def resizeEvent(self, event) -> None:  # pragma: no cover
        super().resizeEvent(event)
        if self._has_content:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._position_placeholder()

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

    def _draw_entity(self, entity: RawEntity) -> None:
        colors = {
            "LINE": "#E53935",
            "CIRCLE": "#FF7043",
            "ARC": "#EF5350",
            "LWPOLYLINE": "#FF8A65",
            "POINT": "#FFF176",
        }

        pen = QPen(QColor(colors.get(entity["type"], "#E8E8E8")))
        pen.setWidthF(0.0)
        pen.setCosmetic(True)

        entity_type = entity["type"]
        if entity_type == "LINE":
            x1, y1 = entity["start"]
            x2, y2 = entity["end"]
            self._scene.addLine(x1, -y1, x2, -y2, pen)
        elif entity_type == "CIRCLE":
            center_x, center_y = entity["center"]
            radius = entity["radius"]
            self._scene.addEllipse(center_x - radius, -(center_y + radius), radius * 2.0, radius * 2.0, pen)
        elif entity_type == "ARC":
            points = entity.get("points") or []
            if len(points) < 2:
                return
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            self._scene.addPath(path, pen)
        elif entity_type == "LWPOLYLINE":
            points = entity.get("points") or []
            if len(points) < 2:
                return
            path = QPainterPath(QPointF(points[0][0], -points[0][1]))
            for x_value, y_value in points[1:]:
                path.lineTo(x_value, -y_value)
            if entity.get("closed"):
                path.closeSubpath()
            self._scene.addPath(path, pen)
        elif entity_type == "POINT":
            x_value, y_value = entity["location"]
            self._scene.addEllipse(x_value - 1.5, -(y_value + 1.5), 3.0, 3.0, pen)
