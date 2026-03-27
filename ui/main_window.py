"""PySide6 desktop application window for Auto-Bonding."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
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

from core import BondingDiagramConverter, CoordinateExporter, PreparedDocument, RawImportPreview
from core.layer_stack import build_stacked_preview_assembly
from services import ProjectDocument

from .import_worker import ImportWorker
from .layer_config_dialog import LayerConfigDialog
from .widgets import DXFPreviewView, ModelPreviewPanel


class MainWindow(QMainWindow):
    """Main desktop window with a 2D viewer and a 3D viewer."""

    def __init__(self):
        super().__init__()
        self.document: ProjectDocument | None = None
        self.output_directory = Path.cwd() / "output"
        self.output_directory.mkdir(exist_ok=True)
        self.exporter = CoordinateExporter()
        self._import_thread: QThread | None = None
        self._import_worker: ImportWorker | None = None
        self._pending_import_config: dict[str, Any] | None = None

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
        self.preview.selection_changed_handler = self._handle_preview_selection
        self.preview.closed_shape_click_handler = self._configure_shape_thickness

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
        self.layers_button = self._build_icon_button(
            self._make_toolbar_icon("layers"),
            "Layer Setup",
            self._open_layer_setup,
        )
        self.export_button = self._build_menu_button(
            self._make_toolbar_icon("export"),
            "Export",
        )

        layout.addWidget(self.import_button)
        layout.addWidget(self.layers_button)
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
        elif kind == "layers":
            painter.drawRoundedRect(5, 5, 14, 4, 1.5, 1.5)
            painter.drawRoundedRect(5, 10, 14, 4, 1.5, 1.5)
            painter.drawRoundedRect(5, 15, 14, 4, 1.5, 1.5)
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

    def _config(self, *, layer_settings: dict[str, Any] | None = None) -> dict[str, Any]:
        config = {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
            "export_format": "STEP",
        }
        if layer_settings is not None:
            config["enabled_layers"] = sorted(layer_settings.get("enabled_layers", []))
            config["layer_mapping_overrides"] = dict(layer_settings.get("layer_mapping_overrides", {}))
        return config

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

    def _load_document(self, file_path: Path, *, layer_settings: dict[str, Any] | None = None) -> None:
        if self._import_thread is not None:
            QMessageBox.information(self, "Import in progress", "Please wait for the current DXF import to finish.")
            return

        self._pending_import_config = self._config(layer_settings=layer_settings)
        self.status_label.setText(f"Parsing {file_path.name}...")
        self.progress.setRange(0, 0)
        self.import_button.setEnabled(False)
        self.layers_button.setEnabled(False)
        self.export_button.setEnabled(False)

        self._import_thread = QThread(self)
        self._import_worker = ImportWorker(file_path, self._pending_import_config)
        self._import_worker.moveToThread(self._import_thread)
        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.preview_ready.connect(self._handle_import_preview)
        self._import_worker.progress_ready.connect(self._handle_import_progress)
        self._import_worker.finished.connect(self._handle_import_success)
        self._import_worker.failed.connect(self._handle_import_failure)
        self._import_worker.finished.connect(self._finish_import_thread)
        self._import_worker.failed.connect(self._finish_import_thread)
        self._import_thread.start()

    def _current_layer_settings(self) -> dict[str, Any]:
        if self.document is None:
            return {"enabled_layers": set(), "layer_mapping_overrides": {}}
        return {
            "enabled_layers": set(self.document.enabled_layers),
            "layer_mapping_overrides": dict(self.document.layer_mapping_overrides),
        }

    def _open_layer_setup(self) -> None:
        if self.document is None:
            QMessageBox.information(self, "Layer Setup", "Import a DXF file first.")
            return

        dialog = LayerConfigDialog(
            self.document.layer_info,
            enabled_layers=self.document.enabled_layers,
            layer_mapping_overrides=self.document.layer_mapping_overrides,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        payload = dialog.result_payload()
        if not payload["enabled_layers"]:
            QMessageBox.warning(self, "Layer Setup", "Select at least one enabled layer.")
            return

        current_settings = self._current_layer_settings()
        if (
            payload["enabled_layers"] == current_settings["enabled_layers"]
            and payload["layer_mapping_overrides"] == current_settings["layer_mapping_overrides"]
        ):
            return

        self._load_document(self.document.path, layer_settings=payload)

    def _should_preserve_user_state(
        self,
        previous_document: ProjectDocument | None,
        file_path: Path,
        config: dict[str, Any],
    ) -> bool:
        if previous_document is None or previous_document.path != file_path:
            return False
        enabled_layers = set(config.get("enabled_layers", []))
        layer_mapping_overrides = dict(config.get("layer_mapping_overrides", {}))
        return (
            previous_document.enabled_layers == enabled_layers
            and previous_document.layer_mapping_overrides == layer_mapping_overrides
        )

    def _handle_import_preview(self, file_path_str: str, preview: RawImportPreview) -> None:
        file_path = Path(file_path_str)
        previous_document = self.document if self.document and self.document.path == file_path else None
        import_config = self._pending_import_config or self._config()
        preserve_user_state = self._should_preserve_user_state(previous_document, file_path, import_config)
        enabled_layers = set(import_config.get("enabled_layers", []))
        if not enabled_layers:
            enabled_layers = {
                str(layer["name"]) for layer in preview["layer_info"] if layer.get("enabled", True)
            }
        layer_mapping_overrides = dict(import_config.get("layer_mapping_overrides", {}))

        self.document = ProjectDocument(
            path=file_path,
            size_bytes=file_path.stat().st_size,
            raw_entities=preview["raw_entities"],
            scene_rect=preview["scene_rect"],
            raw_counts=preview["raw_counts"],
            layer_info=preview["layer_info"],
            enabled_layers=enabled_layers,
            layer_mapping_overrides=layer_mapping_overrides,
            parser_elements=preview["parser_elements"],
            converted_counts=Counter(previous_document.converted_counts) if preserve_user_state and previous_document else Counter(),
            coordinates=previous_document.coordinates if preserve_user_state and previous_document else [],
            entity_thicknesses=dict(previous_document.entity_thicknesses) if preserve_user_state and previous_document else {},
            selected_entity_index=previous_document.selected_entity_index if preserve_user_state and previous_document else None,
            drc_report=(
                previous_document.drc_report
                if preserve_user_state and previous_document
                else {
                    "passed": True,
                    "total_violations": 0,
                    "errors": 0,
                    "warnings": 0,
                    "violations": [],
                }
            ),
            assembly=None,
            stack_preview_assembly=previous_document.stack_preview_assembly if preserve_user_state and previous_document else None,
            status="preview-ready",
            note="2D preview ready. Building 3D model in background.",
        )

        populated_layers = [
            layer for layer in self.document.layer_info if layer.get("enabled", True) and layer.get("entity_count", 0) > 0
        ]
        self.status_label.setText(
            f"{file_path.name} | {len(populated_layers)} active layers ready | generating 3D model..."
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(35)
        self.preview.load_document(self.document)
        self.model_preview.load_document(self.document)

    def _handle_import_progress(self, file_path_str: str, progress_payload: dict[str, Any]) -> None:
        file_path = Path(file_path_str)
        if self.document is None or self.document.path != file_path:
            return

        self.document.converted_counts = Counter(progress_payload.get("converted_counts", {}))
        self.document.status = "building-3d"

        completed_layers = int(progress_payload.get("completed_layers", 0))
        total_layers = max(int(progress_payload.get("total_layers", 0)), 1)
        layer_name = str(progress_payload.get("layer_name", ""))
        progress_value = 35 + int((completed_layers / total_layers) * 50)
        self.progress.setRange(0, 100)
        self.progress.setValue(min(progress_value, 90))
        self.status_label.setText(
            f"{file_path.name} | 3D layer {completed_layers}/{total_layers}: {layer_name}"
        )
        self.model_preview.surface.placeholder.set_content(
            "3D Preview",
            f"Building layer {completed_layers}/{total_layers}",
        )

    def _handle_import_success(self, file_path_str: str, prepared: PreparedDocument) -> None:
        file_path = Path(file_path_str)
        previous_document = self.document if self.document and self.document.path == file_path else None
        import_config = self._pending_import_config or self._config()
        preserve_user_state = self._should_preserve_user_state(previous_document, file_path, import_config)
        enabled_layers = set(import_config.get("enabled_layers", []))
        if not enabled_layers:
            enabled_layers = {
                str(layer["name"]) for layer in prepared["layer_info"] if layer.get("enabled", True)
            }
        layer_mapping_overrides = dict(import_config.get("layer_mapping_overrides", {}))

        self.document = ProjectDocument(
            path=file_path,
            size_bytes=file_path.stat().st_size,
            raw_entities=prepared["raw_entities"],
            scene_rect=prepared["scene_rect"],
            raw_counts=prepared["raw_counts"],
            layer_info=prepared["layer_info"],
            enabled_layers=enabled_layers,
            layer_mapping_overrides=layer_mapping_overrides,
            parser_elements=prepared["parser_elements"],
            converted_counts=prepared["converted_counts"],
            coordinates=prepared["coordinates"],
            entity_thicknesses=dict(previous_document.entity_thicknesses) if preserve_user_state and previous_document else {},
            selected_entity_index=previous_document.selected_entity_index if preserve_user_state and previous_document else None,
            drc_report=prepared["drc_report"],
            assembly=prepared["assembly"],
            stack_preview_assembly=previous_document.stack_preview_assembly if preserve_user_state and previous_document else None,
            status="ready",
            used_fallback=prepared["used_fallback"],
            note=prepared["note"],
        )

        populated_layers = [
            layer for layer in self.document.layer_info if layer.get("enabled", True) and layer.get("entity_count", 0) > 0
        ]
        mapped_layers = [layer for layer in populated_layers if layer.get("mapped_type")]
        self.status_label.setText(
            f"{file_path.name} | {len(populated_layers)} active layers | {len(mapped_layers)} mapped | "
            "click shaded shapes to assign thickness"
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.import_button.setEnabled(True)
        self._update_ui()

    def _handle_import_failure(self, file_path_str: str, error_message: str) -> None:
        file_path = Path(file_path_str)
        if self.document is not None and self.document.path == file_path and self.document.raw_entities:
            QMessageBox.warning(self, "3D generation failed", error_message)
            self.status_label.setText(f"{file_path.name} | 2D ready | 3D generation failed")
        else:
            QMessageBox.critical(self, "Import failed", error_message)
            self.status_label.setText(f"Import failed: {file_path.name}")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.import_button.setEnabled(True)
        self.layers_button.setEnabled(bool(self.document))
        self.export_button.setEnabled(bool(self.document and self.document.assembly))

    def _finish_import_thread(self, *_args: object) -> None:
        if self._import_thread is not None:
            self._import_thread.quit()
            self._import_thread.wait()
            self._import_thread.deleteLater()
            self._import_thread = None

        if self._import_worker is not None:
            self._import_worker.deleteLater()
            self._import_worker = None
        self._pending_import_config = None

    def _update_ui(self) -> None:
        self.preview.load_document(self.document)
        self.model_preview.load_document(self.document)
        self.layers_button.setEnabled(self.document is not None and self._import_thread is None)
        self.export_button.setEnabled(bool(self.document and self.document.assembly))

    def _handle_preview_selection(self, entity_index: int | None) -> None:
        if self.document is None:
            return

        self.document.selected_entity_index = entity_index
        if entity_index is None or entity_index >= len(self.document.raw_entities):
            return

        entity = self.document.raw_entities[entity_index]
        layer_name = entity.get("layer", "0")
        entity_type = entity["type"]
        thickness = self.document.entity_thicknesses.get(entity_index)
        if thickness is not None:
            self.status_label.setText(
                f"Selected {entity_type} on layer {layer_name} | thickness {thickness:.3f} mm"
            )
        else:
            self.status_label.setText(f"Selected {entity_type} on layer {layer_name}")

    def _configure_shape_thickness(self, entity_index: int) -> None:
        if self.document is None or entity_index >= len(self.document.raw_entities):
            return

        entity = self.document.raw_entities[entity_index]
        entity_type = entity["type"]
        is_supported_closed = entity_type == "CIRCLE" or (
            entity_type == "LWPOLYLINE" and bool(entity.get("closed"))
        )
        if not is_supported_closed:
            return

        current = float(self.document.entity_thicknesses.get(entity_index, 0.2))
        thickness, accepted = QInputDialog.getDouble(
            self,
            "Set thickness",
            f"Thickness for {entity.get('layer', '0')} ({entity_type})",
            current,
            0.0,
            50.0,
            3,
        )
        if not accepted:
            return

        if thickness <= 0:
            self.document.entity_thicknesses.pop(entity_index, None)
        else:
            self.document.entity_thicknesses[entity_index] = thickness

        self.document.stack_preview_assembly = build_stacked_preview_assembly(
            self.document.raw_entities,
            self.document.layer_info,
            self.document.entity_thicknesses,
        )
        self.model_preview.load_document(self.document)

        layer_name = entity.get("layer", "0")
        if thickness <= 0:
            self.status_label.setText(f"Cleared thickness for layer {layer_name}")
        else:
            self.status_label.setText(f"Thickness set: {layer_name} -> {thickness:.3f} mm")

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
