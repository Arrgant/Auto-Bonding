"""Reusable placeholder widget for empty viewer states."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class ViewerPlaceholder(QWidget):
    """Centered placeholder used by empty viewer states."""

    action_requested = Signal()

    def __init__(
        self,
        title: str,
        caption: str,
        icon_kind: str,
        parent: QWidget | None = None,
        *,
        action_text: str | None = None,
    ):
        super().__init__(parent)
        self.setFixedSize(240, 210)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("PlaceholderBox")
        box.setFixedSize(82, 82)

        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.addStretch(1)

        icon_label = QLabel()
        icon_label.setPixmap(self._make_icon(icon_kind))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        box_layout.addStretch(1)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("ViewerTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("MutedLabel")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setWordWrap(True)

        self.action_button = QPushButton(self)
        self.action_button.setObjectName("PlaceholderActionButton")
        self.action_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_button.clicked.connect(lambda: self.action_requested.emit())

        layout.addWidget(box, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.caption_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.set_action(action_text)

    def set_content(self, title: str, caption: str) -> None:
        self.title_label.setText(title)
        self.caption_label.setText(caption)

    def set_action(self, text: str | None, *, enabled: bool = True) -> None:
        has_action = bool(text)
        self.action_button.setVisible(has_action)
        self.action_button.setEnabled(enabled and has_action)
        self.action_button.setText("" if text is None else text)

    def _make_icon(self, icon_kind: str) -> QPixmap:
        pixmap = QPixmap(34, 34)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(QColor("#5A5A5A"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if icon_kind == "dxf":
            painter.drawRoundedRect(5, 5, 24, 24, 3, 3)
            painter.drawLine(13, 5, 13, 29)
            painter.drawLine(21, 5, 21, 29)
            painter.drawLine(5, 13, 29, 13)
            painter.drawLine(5, 21, 29, 21)
        else:
            front = [
                QPointF(9, 11),
                QPointF(17, 7),
                QPointF(25, 11),
                QPointF(17, 15),
            ]
            lower = [QPointF(point.x(), point.y() + 10) for point in front]
            for start, end in zip(front, front[1:] + front[:1]):
                painter.drawLine(start, end)
            for start, end in zip(lower, lower[1:] + lower[:1]):
                painter.drawLine(start, end)
            for start, end in zip(front, lower):
                painter.drawLine(start, end)

        painter.end()
        return pixmap
