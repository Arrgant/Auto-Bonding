"""PySide6 desktop application window for Auto-Bonding."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core import BondingDiagramConverter, CoordinateExporter, PreparedDocument, prepare_document
from services import ProjectDocument

from .widgets import DXFPreviewView, ModelPreviewPanel


class MainWindow(QMainWindow):
    """Main desktop window with a 2D viewer and a 3D viewer."""

    def __init__(self):
        super().__init__()
        self.document: ProjectDocument | None = None
        self.output_directory = Path.cwd() / "output"
        self.output_directory.mkdir(exist_ok=True)
        self.exporter = CoordinateExporter()

        self.setWindowTitle("Auto-Bonding")
        self.setMinimumSize(1460, 900)

        self._build_ui()
        self._apply_styles()
        self._update_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(1)
        root.addWidget(split, stretch=1)

        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)
        left_title = QLabel("2D Viewer")
        left_title.setObjectName("SectionTitle")
        left_layout.addWidget(left_title)

        self.preview = DXFPreviewView()
        left_layout.addWidget(self.preview, stretch=1)
        split.addWidget(left_panel)

        self.model_preview = ModelPreviewPanel()
        split.addWidget(self.model_preview)
        split.setSizes([820, 620])

        self.preview.file_drop_handler = self._load_document

        self.status_label = QLabel("Ready")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(180)
        self.progress.setMaximumHeight(8)

        statusbar = QStatusBar()
        statusbar.addWidget(self.status_label, 1)
        statusbar.addPermanentWidget(self.progress)
        self.setStatusBar(statusbar)

    def _build_topbar(self) -> QWidget:
        top = QFrame()
        top.setObjectName("TopBar")

        layout = QHBoxLayout(top)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "app_icon.png"
        if icon_path.exists():
            icon_pixmap = QPixmap(str(icon_path)).scaled(
                28,
                28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(28, 28)
        layout.addWidget(icon_label)

        title = QLabel("Auto-Bonding")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addStretch(1)

        self.import_button = self._build_icon_button(
            self._make_toolbar_icon("import"),
            "Import DXF",
            self._import_file,
        )
        self.export_button = self._build_menu_button(
            self._make_toolbar_icon("export"),
            "Export",
        )

        layout.addWidget(self.import_button)
        layout.addWidget(self.export_button)
        return top

    def _build_icon_button(self, icon: QIcon, tooltip: str, handler) -> QToolButton:
        button = QToolButton()
        button.setIcon(icon)
        button.setIconSize(QSize(20, 20))
        button.setToolTip(tooltip)
        button.setAutoRaise(False)
        button.clicked.connect(handler)
        return button

    def _build_menu_button(self, icon: QIcon, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(icon)
        button.setIconSize(QSize(20, 20))
        button.setToolTip(tooltip)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(button)
        export_coordinates_action = QAction("Export Coordinates", button)
        export_coordinates_action.triggered.connect(self._export_coordinates)
        menu.addAction(export_coordinates_action)

        export_step_action = QAction("Export STEP", button)
        export_step_action.triggered.connect(self._export_step)
        menu.addAction(export_step_action)

        button.setMenu(menu)
        return button

    def _make_toolbar_icon(self, kind: str) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        stroke = QPen(QColor("#E8E8E8"))
        stroke.setWidth(2)
        stroke.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroke.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(stroke)

        tray_color = QColor("#2E2E2E")
        tray_pen = QPen(QColor("#525252"))
        tray_pen.setWidth(1)
        painter.setBrush(tray_color)
        painter.setPen(tray_pen)
        painter.drawRoundedRect(4, 15, 16, 5, 2, 2)

        painter.setPen(stroke)
        if kind == "import":
            painter.drawLine(12, 4, 12, 13)
            painter.drawLine(8, 9, 12, 13)
            painter.drawLine(16, 9, 12, 13)
        else:
            painter.drawLine(12, 13, 12, 4)
            painter.drawLine(8, 8, 12, 4)
            painter.drawLine(16, 8, 12, 4)

        painter.end()
        return QIcon(pixmap)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #1A1A1A; color: #E8E8E8; font-size: 13px; }
            #TopBar { background: #202020; border-bottom: 1px solid #2E2E2E; }
            #Card, #ViewerSurface { background: #242424; border: 1px solid #313131; border-radius: 10px; }
            #ViewerSurface { background: #171717; }
            #Title { font-size: 22px; font-weight: 700; }
            #SectionTitle { font-size: 15px; font-weight: 700; }
            #ViewerTitle { font-size: 15px; font-weight: 700; }
            #MutedLabel { color: #8E8E8E; font-size: 12px; }
            #PlaceholderBox {
                background: transparent;
                border: 2px dashed #4A4A4A;
                border-radius: 10px;
            }
            QToolButton {
                background: #242424;
                border: 1px solid #343434;
                border-radius: 8px;
                padding: 8px;
            }
            QToolButton:hover { background: #2E2E2E; }
            QToolButton:disabled {
                background: #1F1F1F;
                border-color: #2B2B2B;
            }
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
            }
            QMenu {
                background: #242424;
                color: #E8E8E8;
                border: 1px solid #343434;
            }
            QMenu::item:selected {
                background: #E53935;
            }
            QStatusBar { background: #202020; border-top: 1px solid #2E2E2E; color: #A8A8A8; }
            """
        )

    def _config(self) -> dict[str, Any]:
        return {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
            "export_format": "STEP",
        }

    def _import_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import DXF file",
            "",
            "DXF Files (*.dxf);;All Files (*)",
        )
        if not file_path:
            return

        self._load_document(Path(file_path))

    def _load_document(self, file_path: Path) -> None:
        self.status_label.setText(f"Parsing {file_path.name}...")
        self.progress.setValue(25)

        try:
            prepared: PreparedDocument = prepare_document(file_path, self._config())
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Import failed", str(exc))
            self.status_label.setText("Import failed")
            self.progress.setValue(0)
            return

        self.document = ProjectDocument(
            path=file_path,
            size_bytes=file_path.stat().st_size,
            raw_entities=prepared["raw_entities"],
            scene_rect=prepared["scene_rect"],
            raw_counts=prepared["raw_counts"],
            layer_info=prepared["layer_info"],
            parser_elements=prepared["parser_elements"],
            converted_counts=prepared["converted_counts"],
            coordinates=prepared["coordinates"],
            drc_report=prepared["drc_report"],
            assembly=prepared["assembly"],
            used_fallback=prepared["used_fallback"],
            note=prepared["note"],
        )

        populated_layers = [layer for layer in self.document.layer_info if layer.get("entity_count", 0) > 0]
        mapped_layers = [layer for layer in populated_layers if layer.get("mapped_type")]
        self.status_label.setText(
            f"{file_path.name} | {len(populated_layers)} layers | {len(mapped_layers)} mapped"
        )
        self.progress.setValue(100)
        self._update_ui()

    def _update_ui(self) -> None:
        self.preview.load_document(self.document)
        self.model_preview.load_document(self.document)
        self.export_button.setEnabled(bool(self.document and self.document.assembly))

    def _export_coordinates(self) -> None:
        if self.document is None or self.document.assembly is None:
            QMessageBox.information(self, "Export coordinates", "Import a DXF file first.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save coordinates",
            str(self.output_directory / f"{self.document.path.stem}_coordinates.csv"),
            "CSV Files (*.csv)",
        )
        if not output_path:
            return

        if not self.exporter.export(self.document.assembly, output_path, "CSV"):
            QMessageBox.critical(self, "Export coordinates", "Failed to write the coordinate file.")
            return

        self.status_label.setText(f"Coordinates exported: {self.document.path.name}")

    def _export_step(self) -> None:
        if self.document is None or self.document.assembly is None:
            QMessageBox.information(self, "Export STEP", "Import a DXF file first.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save STEP",
            str(self.output_directory / f"{self.document.path.stem}.step"),
            "STEP Files (*.step *.stp)",
        )
        if not output_path:
            return

        converter = BondingDiagramConverter(self._config())
        if not converter.export_step(self.document.assembly, output_path):
            QMessageBox.critical(self, "Export STEP", "Failed to export the STEP model.")
            return

        self.status_label.setText(f"STEP exported: {self.document.path.name}")
