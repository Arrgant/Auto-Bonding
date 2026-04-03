"""PySide6 desktop application window for Auto-Bonding."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, QSize, Qt, QTimer
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

from core import (
    BondingDiagramConverter,
    CoordinateExporter,
    PreparedDocument,
    RawImportPreview,
    WireProductionExporter,
    infer_elements_from_raw_entities,
)
from core.layer_colors import build_layer_color_map
from core.layer_semantics import apply_layer_role_overrides
from core.layer_stack import build_stacked_preview_assembly, layer_sort_key, stack_preview_layer_names
from core.semantic import (
    MANUAL_REVIEW_KIND_OPTIONS,
    SemanticClassificationResult,
    apply_manual_semantic_overrides,
    classify_semantic_layers,
    manual_override_entity_key,
)
from services import LayerSemanticPresetStore, ProjectDocument, WireRecipeTemplateStore

from .import_worker import ImportWorker
from .layer_thickness_dialog import LayerThicknessDialog
from .layer_semantic_preset_dialog import LayerSemanticPresetDialog
from .stack_preview_worker import StackPreviewWorker
from .wire_export_dialog import WireExportDialog
from .widgets import DXFPreviewView, LayerManagerPanel, ModelPreviewPanel

TOPBAR_BUTTON_WIDTH = 168


class MainWindow(QMainWindow):
    """Main desktop window with a 2D viewer and a 3D viewer."""

    def __init__(self):
        super().__init__()
        self.document: ProjectDocument | None = None
        self.output_directory = Path.cwd() / "output"
        self.output_directory.mkdir(exist_ok=True)
        self.exporter = CoordinateExporter()
        self.wire_production_exporter = WireProductionExporter()
        self.layer_semantic_store = LayerSemanticPresetStore()
        self.wire_template_store = WireRecipeTemplateStore()
        self._import_thread: QThread | None = None
        self._import_worker: ImportWorker | None = None
        self._stack_preview_thread: QThread | None = None
        self._stack_preview_worker: StackPreviewWorker | None = None
        self._pending_import_config: dict[str, Any] | None = None
        self._auto_build_after_preview = False
        self._skip_next_walkthrough = False
        self._layer_walkthrough_queue: list[str] = []
        self._layer_walkthrough_index = -1
        self._layer_walkthrough_active = False

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

        left_body = QWidget()
        left_body_layout = QHBoxLayout(left_body)
        left_body_layout.setContentsMargins(0, 0, 0, 0)
        left_body_layout.setSpacing(0)

        self.layer_panel = LayerManagerPanel()
        left_body_layout.addWidget(self.layer_panel)

        self.preview = DXFPreviewView()
        left_body_layout.addWidget(self.preview, stretch=1)
        left_layout.addWidget(left_body, stretch=1)
        split.addWidget(left_panel)

        self.model_preview = ModelPreviewPanel()
        split.addWidget(self.model_preview)
        split.setSizes([820, 620])

        self.preview.file_drop_handler = lambda path: self._load_document(path, preview_only=True, auto_continue=True)
        self.preview.import_requested_handler = self._import_file
        self.preview.selection_changed_handler = self._handle_preview_selection
        self.preview.closed_shape_click_handler = self._configure_shape_thickness
        self.model_preview.set_import_requested_handler(self._import_file)
        self.layer_panel.layer_visibility_changed.connect(self._handle_layer_visibility_changed)
        self.layer_panel.layer_selected.connect(self._handle_layer_selected)
        self.layer_panel.layer_thickness_requested.connect(self._edit_layer_thickness)
        self.status_stage = QLabel("Idle")
        self.status_stage.setObjectName("StatusBadge")
        self.status_file_label = QLabel("No file")
        self.status_file_label.setObjectName("StatusMeta")
        self.status_label = QLabel("Import a DXF to begin.")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(180)
        self.progress.setMaximumHeight(8)

        statusbar = QStatusBar()
        statusbar.addWidget(self.status_stage)
        statusbar.addWidget(self.status_file_label)
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

    def _build_icon_button(self, icon: QIcon, label: str, handler) -> QToolButton:
        button = QToolButton()
        button.setObjectName("TopBarButton")
        button.setFixedWidth(TOPBAR_BUTTON_WIDTH)
        button.setIcon(icon)
        button.setText(label)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setIconSize(QSize(18, 18))
        button.setToolTip(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(False)
        button.clicked.connect(handler)
        return button

    def _build_menu_button(self, icon: QIcon, label: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("TopBarButton")
        button.setFixedWidth(TOPBAR_BUTTON_WIDTH)
        button.setIcon(icon)
        button.setText(label)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setIconSize(QSize(18, 18))
        button.setToolTip(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(button)
        export_coordinates_action = QAction("Export Coordinates", button)
        export_coordinates_action.triggered.connect(self._export_coordinates)
        menu.addAction(export_coordinates_action)

        export_wire_action = QAction("Export Wire Production Files...", button)
        export_wire_action.triggered.connect(self._export_wire_production_files)
        menu.addAction(export_wire_action)

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
            #TopBarButton {
                background: #242424;
                border: 1px solid #343434;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
            }
            #TopBarButton:hover { background: #2E2E2E; }
            #TopBarButton:disabled {
                background: #1F1F1F;
                border-color: #2B2B2B;
            }
            QToolButton#TopBarButton::menu-indicator {
                image: none;
                width: 0px;
            }
            #SecondaryButton {
                background: #202020;
                border: 1px solid #303030;
                border-radius: 8px;
                padding: 6px 10px;
                color: #D0D0D0;
            }
            #SecondaryButton:hover { background: #282828; }
            #SectionBadge {
                background: #2A2A2A;
                color: #D6D6D6;
                border: 1px solid #353535;
                border-radius: 999px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            #ViewerStatus {
                background: #2A2A2A;
                color: #D6D6D6;
                border: 1px solid #353535;
                border-radius: 999px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            #ViewerStatus[tone="good"] {
                background: #1E4D3A;
                color: #E2F7EA;
                border: 1px solid #2F7A5C;
            }
            #ViewerStatus[tone="warn"] {
                background: #533A1D;
                color: #FFE8C7;
                border: 1px solid #7A5730;
            }
            #ViewerStatus[tone="busy"] {
                background: #28374A;
                color: #DEEAF9;
                border: 1px solid #425B79;
            }
            #ViewerInfoBadge {
                background: rgba(25, 25, 25, 0.88);
                color: #F4F4F4;
                border: 1px solid #414141;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            #StatusBadge {
                background: #2A2A2A;
                color: #D6D6D6;
                border: 1px solid #353535;
                border-radius: 999px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            #StatusBadge[tone="good"] {
                background: #1E4D3A;
                color: #E2F7EA;
                border: 1px solid #2F7A5C;
            }
            #StatusBadge[tone="warn"] {
                background: #533A1D;
                color: #FFE8C7;
                border: 1px solid #7A5730;
            }
            #StatusBadge[tone="busy"] {
                background: #28374A;
                color: #DEEAF9;
                border: 1px solid #425B79;
            }
            #StatusBadge[tone="error"] {
                background: #5A2323;
                color: #FFE4E4;
                border: 1px solid #8B3A3A;
            }
            #StatusMeta {
                color: #8E8E8E;
                padding-left: 8px;
                padding-right: 8px;
            }
            #ViewerProgressBar {
                background: #1D1D1D;
                border: 1px solid #303030;
                border-radius: 999px;
            }
            #ViewerProgressBar::chunk {
                background: #D45B2E;
                border-radius: 999px;
            }
            #PlaceholderActionButton {
                background: #D45B2E;
                color: #FFFFFF;
                border: 1px solid #E07A53;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 700;
                min-width: 120px;
            }
            #PlaceholderActionButton:hover { background: #E06737; }
            #PlaceholderActionButton:disabled {
                background: #7C3B22;
                color: #E6C8BC;
                border-color: #8F4A2E;
            }
            QMenu {
                background: #242424;
                color: #E8E8E8;
                border: 1px solid #343434;
            }
            QMenu::item:selected {
                background: #E53935;
            }
            QStatusBar::item { border: none; }
            QTreeWidget {
                background: #202020;
                border: 1px solid #303030;
                border-radius: 8px;
                alternate-background-color: #252525;
            }
            QTreeWidget::item:selected {
                background: #7A1D1B;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background: #262626;
                color: #BEBEBE;
                border: none;
                border-bottom: 1px solid #313131;
                padding: 4px 6px;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #202020;
                color: #BEBEBE;
                padding: 6px 10px;
                border: 1px solid #303030;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #2A2A2A;
                color: #FFFFFF;
            }
            QStatusBar { background: #202020; border-top: 1px solid #2E2E2E; color: #A8A8A8; }
            """
        )

    def _config(self, *, layer_settings: dict[str, Any] | None = None, preview_only: bool = False) -> dict[str, Any]:
        config = {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
            "defer_wire_geometry": True,
            "defer_drc_report": True,
            "export_format": "STEP",
            "preview_only": preview_only,
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

        self._load_document(Path(file_path), preview_only=True, auto_continue=True)

    def _load_document(
        self,
        file_path: Path,
        *,
        layer_settings: dict[str, Any] | None = None,
        preview_only: bool = False,
        auto_continue: bool = False,
    ) -> None:
        if self._import_thread is not None:
            QMessageBox.information(self, "Import in progress", "Please wait for the current DXF import to finish.")
            return

        self._auto_build_after_preview = bool(preview_only and auto_continue)
        self._pending_import_config = self._config(layer_settings=layer_settings, preview_only=preview_only)
        self._set_status_message(
            "Reading DXF and extracting layers.",
            stage="Parsing",
            tone="busy",
            file_name=file_path.name,
        )
        self.progress.setRange(0, 0)
        self.import_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self._set_import_actions_enabled(False)

        self._import_thread = QThread(self)
        self._import_worker = ImportWorker(file_path, self._pending_import_config)
        self._import_worker.moveToThread(self._import_thread)
        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.preview_ready.connect(self._handle_import_preview)
        self._import_worker.preview_complete.connect(self._finish_import_thread)
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

    def _open_semantic_preset_manager(self) -> None:
        dialog = LayerSemanticPresetDialog(self.layer_semantic_store.list_presets(), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated_presets = dialog.result_presets()
        before = self.layer_semantic_store.list_presets()
        if updated_presets == before:
            return

        self.layer_semantic_store.replace_presets(updated_presets)
        self._set_status_message(
            "Semantic presets updated. Re-import the DXF to apply changes to the current session.",
            stage="Updated",
            tone="good",
        )

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

    def _default_visible_layers(self, layer_info: list[dict[str, Any]]) -> set[str]:
        return {
            str(layer["name"])
            for layer in layer_info
            if layer.get("enabled", True) and layer.get("entity_count", 0) > 0
        }

    def _resolve_semantic_state(
        self,
        raw_entities: list[dict[str, Any]],
        layer_info: list[dict[str, Any]],
        base_result: SemanticClassificationResult,
        previous_document: ProjectDocument | None,
        preserve_user_state: bool,
    ) -> tuple[list[dict[str, Any]], SemanticClassificationResult, dict[str, str], dict[str, str], str | None]:
        layer_semantic_overrides = self.layer_semantic_store.resolve_for_layers(layer_info)
        semantic_overrides: dict[str, str] = {}
        selected_semantic_key: str | None = None

        if preserve_user_state and previous_document is not None:
            layer_semantic_overrides.update(previous_document.layer_semantic_overrides)
            semantic_overrides = dict(previous_document.semantic_overrides)
            selected_semantic_key = previous_document.selected_semantic_key

        resolved_layer_info = apply_layer_role_overrides(layer_info, layer_semantic_overrides)
        semantic_result = (
            classify_semantic_layers(raw_entities, resolved_layer_info)
            if layer_semantic_overrides
            else base_result
        )
        semantic_result = apply_manual_semantic_overrides(semantic_result, semantic_overrides)
        return (
            resolved_layer_info,
            semantic_result,
            semantic_overrides,
            layer_semantic_overrides,
            selected_semantic_key,
        )

    def _find_semantic_selection(
        self,
        result: SemanticClassificationResult,
        *,
        layer_name: str | None,
        source_indices: tuple[int, ...],
        preferred_kind: str,
    ) -> tuple[str | None, object | None]:
        if not source_indices:
            return None, None

        for entity in result.entities:
            if (
                entity.layer_name == layer_name
                and entity.source_indices == source_indices
                and entity.kind == preferred_kind
            ):
                return f"entity:{entity.id}", entity

        for entity in result.entities:
            if entity.layer_name == layer_name and entity.source_indices == source_indices:
                return f"entity:{entity.id}", entity

        for candidate in result.review:
            if candidate.layer_name == layer_name and candidate.source_indices == source_indices:
                return f"review:{candidate.id}", candidate

        return None, None

    def _rebuild_stack_preview(self) -> None:
        if self.document is None:
            return

        if self._stack_preview_thread is not None:
            return

        self.document.stack_preview_layer_meshes = []
        self.model_preview.show_build_progress("Updating stacked preview...", value=None, maximum=None)
        self.model_preview.surface.placeholder.set_content("3D Preview", "Updating stacked preview")
        self.model_preview.surface.placeholder.set_action(None)
        self.model_preview.surface._stack.setCurrentWidget(self.model_preview.surface._placeholder_page)

        self._stack_preview_thread = QThread(self)
        self._stack_preview_worker = StackPreviewWorker(
            list(self.document.raw_entities),
            list(self.document.layer_info),
            dict(self.document.entity_thicknesses),
            dict(self.document.layer_thicknesses),
            set(self.document.visible_layers),
            dict(self.document.layer_colors),
        )
        self._stack_preview_worker.moveToThread(self._stack_preview_thread)
        self._stack_preview_thread.started.connect(self._stack_preview_worker.run)
        self._stack_preview_worker.finished.connect(self._handle_stack_preview_ready)
        self._stack_preview_worker.failed.connect(self._handle_stack_preview_failed)
        self._stack_preview_worker.finished.connect(self._finish_stack_preview_thread)
        self._stack_preview_worker.failed.connect(self._finish_stack_preview_thread)
        self._stack_preview_thread.start()

    def _handle_stack_preview_ready(self, assembly: object, layer_meshes: object) -> None:
        if self.document is None:
            return

        self.document.stack_preview_assembly = assembly
        self.document.stack_preview_layer_meshes = list(layer_meshes) if isinstance(layer_meshes, list) else []
        self.model_preview.hide_build_progress()
        self.model_preview.load_document(self.document)

        if self._layer_walkthrough_active:
            QTimer.singleShot(0, self._advance_layer_walkthrough)

    def _handle_stack_preview_failed(self, error_message: str) -> None:
        if self.document is None:
            return

        self._set_status_message(
            f"Stacked preview failed: {error_message}",
            stage="Warning",
            tone="warn",
        )
        self.model_preview.hide_build_progress()
        if self._layer_walkthrough_active:
            QTimer.singleShot(0, self._advance_layer_walkthrough)

    def _finish_stack_preview_thread(self, *_args: object) -> None:
        if self._stack_preview_thread is not None:
            self._stack_preview_thread.quit()
            self._stack_preview_thread.wait()
            self._stack_preview_thread.deleteLater()
            self._stack_preview_thread = None

        if self._stack_preview_worker is not None:
            self._stack_preview_worker.deleteLater()
            self._stack_preview_worker = None

    def _ordered_active_layer_names(self) -> list[str]:
        if self.document is None:
            return []

        preview_layers = stack_preview_layer_names(self.document.layer_info)
        return [
            str(layer["name"])
            for layer in sorted(self.document.layer_info, key=lambda item: layer_sort_key(str(item["name"])))
            if str(layer["name"]) in preview_layers
        ]

    def _layer_affects_stack_preview(self, layer_name: str | None) -> bool:
        if self.document is None or not isinstance(layer_name, str):
            return False
        return layer_name in stack_preview_layer_names(self.document.layer_info)

    def _start_layer_walkthrough(self) -> None:
        if self.document is None:
            return

        ordered_layers = self._ordered_active_layer_names()
        if not ordered_layers:
            self._finish_layer_walkthrough()
            return

        self._layer_walkthrough_queue = ordered_layers
        self._layer_walkthrough_index = -1
        self._layer_walkthrough_active = True
        QTimer.singleShot(0, self._advance_layer_walkthrough)

    def _finish_layer_walkthrough(self) -> None:
        should_start_final_build = (
            self.document is not None
            and self.document.assembly is None
            and self._import_thread is None
        )
        next_path = self.document.path if self.document is not None else None
        next_layer_settings = self._current_layer_settings() if self.document is not None else None

        self._layer_walkthrough_queue = []
        self._layer_walkthrough_index = -1
        self._layer_walkthrough_active = False

        if self.document is None:
            return

        visible_layers = self._default_visible_layers(self.document.layer_info)
        if not visible_layers:
            visible_layers = {
                str(layer["name"])
                for layer in self.document.layer_info
                if layer.get("enabled", True)
            }
        self.document.visible_layers = visible_layers
        self.document.selected_layer_name = None
        self.preview.load_document(self.document)
        self.layer_panel.load_document(self.document)
        if self.document.stack_preview_assembly is not None:
            self.model_preview.load_document(self.document)

        if should_start_final_build and next_path is not None and next_layer_settings is not None:
            self._skip_next_walkthrough = True
            self._load_document(next_path, layer_settings=next_layer_settings, preview_only=False)

    def _advance_layer_walkthrough(self) -> None:
        if not self._layer_walkthrough_active or self.document is None:
            return

        self._layer_walkthrough_index += 1
        if self._layer_walkthrough_index >= len(self._layer_walkthrough_queue):
            self._finish_layer_walkthrough()
            self._set_status_message(
                "Layer thickness setup complete. Generating the 3D model.",
                stage="Building",
                tone="busy",
            )
            return

        layer_name = self._layer_walkthrough_queue[self._layer_walkthrough_index]
        self.document.visible_layers = set(self._layer_walkthrough_queue[: self._layer_walkthrough_index + 1])
        self.document.selected_layer_name = layer_name
        self.preview.load_document(self.document)
        self.layer_panel.load_document(self.document)

        current = self._suggest_walkthrough_thickness(layer_name)
        payload = self._prompt_thickness(
            title="Set layer thickness",
            headline=f"Layer {self._layer_walkthrough_index + 1}/{len(self._layer_walkthrough_queue)}: {layer_name}",
            detail="Use a quick preset or type a value in millimeters. Clear removes any assigned thickness.",
            current_value=current,
            apply_to_remaining_label="Apply this thickness to the remaining layers in this walkthrough",
            reject_text="Finish Now",
        )
        if payload is None:
            self._finish_layer_walkthrough()
            self._set_status_message(
                "Layer setup canceled. Generating the 3D model with the current values.",
                stage="Building",
                tone="busy",
            )
            return

        thickness = float(payload["thickness"])
        apply_to_remaining = bool(payload["apply_to_remaining"])
        self._set_layer_thickness_value(layer_name, thickness)

        if apply_to_remaining:
            remaining_layers = self._layer_walkthrough_queue[self._layer_walkthrough_index + 1 :]
            for remaining_layer in remaining_layers:
                self._set_layer_thickness_value(remaining_layer, thickness)
            self.layer_panel.load_document(self.document)
            self._finish_layer_walkthrough()
            if thickness <= 0:
                detail = f"Cleared thickness across {1 + len(remaining_layers)} layers. Generating the 3D model."
            else:
                detail = f"Applied {thickness:.3f} mm to {1 + len(remaining_layers)} layers. Generating the 3D model."
            self._set_status_message(detail, stage="Building", tone="busy")
            return

        self._rebuild_stack_preview()
        self.layer_panel.load_document(self.document)
        if thickness <= 0:
            self._set_status_message(
                f"Cleared thickness for layer {layer_name}.",
                stage="Thickness",
                tone="good",
            )
        else:
            self._set_status_message(
                f"Layer {layer_name} thickness set to {thickness:.3f} mm.",
                stage="Thickness",
                tone="good",
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
        active_layers = self._default_visible_layers(preview["layer_info"])
        visible_layers = set(previous_document.visible_layers) if preserve_user_state and previous_document else set(active_layers)
        visible_layers &= active_layers
        if not visible_layers:
            visible_layers = set(active_layers)
        layer_mapping_overrides = dict(import_config.get("layer_mapping_overrides", {}))
        (
            resolved_layer_info,
            semantic_result,
            semantic_overrides,
            layer_semantic_overrides,
            selected_semantic_key,
        ) = self._resolve_semantic_state(
            preview["raw_entities"],
            preview["layer_info"],
            preview["semantic_result"],
            previous_document,
            preserve_user_state,
        )
        active_layers = self._default_visible_layers(resolved_layer_info)
        visible_layers &= active_layers
        if not visible_layers:
            visible_layers = set(active_layers)
        layer_colors = build_layer_color_map(resolved_layer_info, preview["raw_entities"])

        self.document = ProjectDocument(
            path=file_path,
            size_bytes=file_path.stat().st_size,
            raw_entities=preview["raw_entities"],
            scene_rect=preview["scene_rect"],
            raw_counts=preview["raw_counts"],
            layer_info=resolved_layer_info,
            semantic_result=semantic_result,
            semantic_overrides=semantic_overrides,
            layer_semantic_overrides=layer_semantic_overrides,
            enabled_layers=enabled_layers,
            visible_layers=visible_layers,
            layer_mapping_overrides=layer_mapping_overrides,
            layer_colors=layer_colors,
            parser_elements=preview["parser_elements"],
            converted_counts=Counter(previous_document.converted_counts) if preserve_user_state and previous_document else Counter(),
            coordinates=previous_document.coordinates if preserve_user_state and previous_document else [],
            layer_thicknesses=(
                {
                    layer_name: thickness
                    for layer_name, thickness in previous_document.layer_thicknesses.items()
                    if layer_name in active_layers
                }
                if preserve_user_state and previous_document
                else {}
            ),
            entity_thicknesses=dict(previous_document.entity_thicknesses) if preserve_user_state and previous_document else {},
            selected_layer_name=(
                previous_document.selected_layer_name
                if preserve_user_state
                and previous_document
                and previous_document.selected_layer_name in active_layers
                else None
            ),
            selected_entity_index=previous_document.selected_entity_index if preserve_user_state and previous_document else None,
            selected_semantic_key=selected_semantic_key,
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
            layer_meshes=[],
            mesh_bytes=None,
            mesh_vertex_count=0,
            mesh_diagonal=1.0,
            stack_preview_assembly=previous_document.stack_preview_assembly if preserve_user_state and previous_document else None,
            stack_preview_layer_meshes=(
                list(previous_document.stack_preview_layer_meshes)
                if preserve_user_state and previous_document
                else []
            ),
            status="preview-ready",
            note="2D preview ready. Building 3D model in background.",
        )

        populated_layers = [
            layer for layer in self.document.layer_info if layer.get("enabled", True) and layer.get("entity_count", 0) > 0
        ]
        if self._skip_next_walkthrough:
            self._set_status_message(
                f"{len(populated_layers)} imported layers ready. Generating the 3D model.",
                stage="Building",
                tone="busy",
                file_name=file_path.name,
            )
        else:
            self._set_status_message(
                f"{len(populated_layers)} imported layers ready. Configure thickness layer by layer.",
                stage="2D Ready",
                tone="warn",
                file_name=file_path.name,
            )
        self.progress.setRange(0, 100)
        self.progress.setValue(35)
        self.preview.load_document(self.document)
        self.layer_panel.load_document(self.document)
        self.model_preview.load_document(self.document)
        if self._skip_next_walkthrough:
            self._skip_next_walkthrough = False
        elif self._auto_build_after_preview:
            self._set_status_message(
                "2D preview is ready. Building 3D automatically. Adjust layer thickness later from the Layers panel if needed.",
                stage="Building",
                tone="busy",
                file_name=file_path.name,
            )
        else:
            self._start_layer_walkthrough()

    def _handle_import_progress(self, file_path_str: str, progress_payload: dict[str, Any]) -> None:
        file_path = Path(file_path_str)
        if self.document is None or self.document.path != file_path:
            return

        self.document.converted_counts = Counter(progress_payload.get("converted_counts", {}))
        self.document.status = "building-3d"

        completed_layers = int(progress_payload.get("completed_layers", 0))
        total_layers = max(int(progress_payload.get("total_layers", 0)), 1)
        layer_name = str(progress_payload.get("layer_name", ""))
        deferred = bool(progress_payload.get("deferred"))
        self.document.note = f"Generating the stacked model from layer {completed_layers}/{total_layers}: {layer_name}."
        progress_value = 35 + int((completed_layers / total_layers) * 50)
        self.progress.setRange(0, 100)
        self.progress.setValue(min(progress_value, 90))
        if deferred:
            progress_label = f"Fast import: keeping {layer_name} in 2D"
            self.document.note = f"Keeping {layer_name} in 2D during import to avoid a heavy wire rebuild."
            placeholder_text = "Skipping heavy wire mesh during import"
        else:
            progress_label = f"3D layer {completed_layers}/{total_layers}: {layer_name}"
            placeholder_text = f"Building layer {completed_layers}/{total_layers}"
        self._set_status_message(
            progress_label,
            stage="Building",
            tone="busy",
            file_name=file_path.name,
        )
        self.model_preview.show_build_progress(
            progress_label,
            value=min(progress_value, 90),
            maximum=100,
        )
        self.model_preview.surface.placeholder.set_content("3D Preview", placeholder_text)
        self.model_preview.surface.placeholder.set_action(None)

    def _assembly_contains_element_type(self, assembly: object | None, element_type: str) -> bool:
        if assembly is None:
            return False

        pending = list(getattr(assembly, "children", []))
        while pending:
            node = pending.pop()
            metadata = getattr(node, "metadata", {}) or {}
            if metadata.get("element_type") == element_type:
                return True
            pending.extend(getattr(node, "children", []))
        return False

    def _resolve_export_elements(self) -> list[Any]:
        if self.document is None:
            return []
        if self.document.parser_elements:
            return list(self.document.parser_elements)
        return infer_elements_from_raw_entities(self.document.raw_entities, self._config())

    def _full_step_export_assembly(self) -> object | None:
        if self.document is None or self.document.assembly is None:
            return None

        if not self.document.wire_geometries or self._assembly_contains_element_type(self.document.assembly, "wire"):
            return self.document.assembly

        self._set_status_message(
            "Preparing full wire geometry for STEP export.",
            stage="Export",
            tone="busy",
        )
        elements = self._resolve_export_elements()
        if not elements:
            return self.document.assembly

        full_config = dict(self._config())
        full_config["defer_wire_geometry"] = False
        assembly = BondingDiagramConverter(full_config).convert_elements(elements)
        self.document.assembly = assembly
        return assembly

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
        active_layers = self._default_visible_layers(prepared["layer_info"])
        visible_layers = set(previous_document.visible_layers) if preserve_user_state and previous_document else set(active_layers)
        visible_layers &= active_layers
        if not visible_layers:
            visible_layers = set(active_layers)
        layer_mapping_overrides = dict(import_config.get("layer_mapping_overrides", {}))
        (
            resolved_layer_info,
            semantic_result,
            semantic_overrides,
            layer_semantic_overrides,
            selected_semantic_key,
        ) = self._resolve_semantic_state(
            prepared["raw_entities"],
            prepared["layer_info"],
            prepared["semantic_result"],
            previous_document,
            preserve_user_state,
        )
        active_layers = self._default_visible_layers(resolved_layer_info)
        visible_layers &= active_layers
        if not visible_layers:
            visible_layers = set(active_layers)
        layer_colors = build_layer_color_map(resolved_layer_info, prepared["raw_entities"])

        self.document = ProjectDocument(
            path=file_path,
            size_bytes=file_path.stat().st_size,
            raw_entities=prepared["raw_entities"],
            scene_rect=prepared["scene_rect"],
            raw_counts=prepared["raw_counts"],
            layer_info=resolved_layer_info,
            semantic_result=semantic_result,
            semantic_overrides=semantic_overrides,
            layer_semantic_overrides=layer_semantic_overrides,
            enabled_layers=enabled_layers,
            visible_layers=visible_layers,
            layer_mapping_overrides=layer_mapping_overrides,
            layer_colors=layer_colors,
            parser_elements=prepared["parser_elements"],
            converted_counts=prepared["converted_counts"],
            coordinates=prepared["coordinates"],
            wire_geometries=prepared["wire_geometries"],
            layer_thicknesses=(
                {
                    layer_name: thickness
                    for layer_name, thickness in previous_document.layer_thicknesses.items()
                    if layer_name in active_layers
                }
                if preserve_user_state and previous_document
                else {}
            ),
            entity_thicknesses=dict(previous_document.entity_thicknesses) if preserve_user_state and previous_document else {},
            selected_layer_name=(
                previous_document.selected_layer_name
                if preserve_user_state
                and previous_document
                and previous_document.selected_layer_name in active_layers
                else None
            ),
            selected_entity_index=previous_document.selected_entity_index if preserve_user_state and previous_document else None,
            selected_semantic_key=selected_semantic_key,
            drc_report=prepared["drc_report"],
            assembly=prepared["assembly"],
            layer_meshes=list(prepared.get("layer_meshes", [])),
            mesh_bytes=prepared.get("mesh_bytes"),
            mesh_vertex_count=int(prepared.get("mesh_vertex_count", 0)),
            mesh_diagonal=float(prepared.get("mesh_diagonal", 1.0)),
            stack_preview_assembly=previous_document.stack_preview_assembly if preserve_user_state and previous_document else None,
            stack_preview_layer_meshes=(
                list(previous_document.stack_preview_layer_meshes)
                if preserve_user_state and previous_document
                else []
            ),
            status="ready",
            used_fallback=prepared["used_fallback"],
            note=prepared["note"],
        )

        populated_layers = [
            layer for layer in self.document.layer_info if layer.get("enabled", True) and layer.get("entity_count", 0) > 0
        ]
        mapped_layers = [layer for layer in populated_layers if layer.get("mapped_type")]
        self._set_status_message(
            f"{len(populated_layers)} active layers, {len(mapped_layers)} mapped. Click shaded shapes to assign thickness.",
            stage="Ready",
            tone="good",
            file_name=file_path.name,
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.import_button.setEnabled(True)
        self.model_preview.hide_build_progress()
        self._update_ui()

    def _handle_import_failure(self, file_path_str: str, error_message: str) -> None:
        file_path = Path(file_path_str)
        if self.document is not None and self.document.path == file_path and self.document.raw_entities:
            QMessageBox.warning(self, "3D generation failed", error_message)
            self._set_status_message(
                "2D preview is ready, but 3D generation failed.",
                stage="Warning",
                tone="warn",
                file_name=file_path.name,
            )
        else:
            QMessageBox.critical(self, "Import failed", error_message)
            self._set_status_message(
                "Import failed.",
                stage="Error",
                tone="error",
                file_name=file_path.name,
            )
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.import_button.setEnabled(True)
        self.export_button.setEnabled(self._has_exportable_outputs())
        self.model_preview.hide_build_progress()

    def _finish_import_thread(self, *_args: object) -> None:
        pending_config = dict(self._pending_import_config or {})
        auto_build_after_preview = bool(self._auto_build_after_preview)
        next_path = self.document.path if self.document is not None else None
        next_layer_settings = self._current_layer_settings() if self.document is not None else None

        if self._import_thread is not None:
            self._import_thread.quit()
            self._import_thread.wait()
            self._import_thread.deleteLater()
            self._import_thread = None

        if self._import_worker is not None:
            self._import_worker.deleteLater()
            self._import_worker = None
        self._pending_import_config = None
        self._auto_build_after_preview = False
        self._set_import_actions_enabled(True)

        if (
            auto_build_after_preview
            and pending_config.get("preview_only")
            and next_path is not None
            and next_layer_settings is not None
            and self.document is not None
            and self.document.assembly is None
        ):
            self._skip_next_walkthrough = True
            QTimer.singleShot(
                0,
                lambda path=next_path, settings=next_layer_settings: self._load_document(
                    path,
                    layer_settings=settings,
                    preview_only=False,
                ),
            )

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI teardown path
        if self._import_worker is not None:
            try:
                self._import_worker.failed.disconnect(self._finish_import_thread)
                self._import_worker.finished.disconnect(self._finish_import_thread)
            except (RuntimeError, TypeError):
                pass
        self._finish_import_thread()
        self._finish_stack_preview_thread()
        self.model_preview.shutdown()
        super().closeEvent(event)

    def _update_ui(self) -> None:
        self.preview.load_document(self.document)
        self.layer_panel.load_document(self.document)
        self.model_preview.load_document(self.document)
        self._set_import_actions_enabled(self._import_thread is None)
        self.export_button.setEnabled(self._has_exportable_outputs())

    def _has_exportable_outputs(self) -> bool:
        return bool(
            self.document
            and (
                self.document.assembly is not None
                or self.document.wire_geometries
            )
        )

    def _set_status_message(
        self,
        detail: str,
        *,
        stage: str,
        tone: str = "neutral",
        file_name: str | None = None,
    ) -> None:
        self.status_stage.setText(stage)
        self.status_stage.setProperty("tone", tone)
        self.status_stage.style().unpolish(self.status_stage)
        self.status_stage.style().polish(self.status_stage)
        if file_name is None:
            file_name = self.document.path.name if self.document is not None else "No file"
        self.status_file_label.setText(file_name)
        self.status_label.setText(detail)

    def _set_import_actions_enabled(self, enabled: bool) -> None:
        self.preview.set_import_action_enabled(enabled)
        self.model_preview.set_import_action_enabled(enabled)

    def _prompt_thickness(
        self,
        *,
        title: str,
        headline: str,
        detail: str | None,
        current_value: float,
        apply_to_remaining_label: str | None = None,
        reject_text: str = "Cancel",
    ) -> dict[str, float | bool] | None:
        dialog = LayerThicknessDialog(
            title=title,
            headline=headline,
            detail=detail,
            current_value=current_value,
            apply_to_remaining_label=apply_to_remaining_label,
            reject_text=reject_text,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog.result_payload()

    def _suggest_walkthrough_thickness(self, layer_name: str) -> float:
        if self.document is None:
            return 0.2
        existing_value = self.document.layer_thicknesses.get(layer_name)
        if existing_value is not None:
            return float(existing_value)
        if self._layer_walkthrough_index > 0:
            previous_layers = self._layer_walkthrough_queue[: self._layer_walkthrough_index]
            for previous_layer in reversed(previous_layers):
                previous_value = self.document.layer_thicknesses.get(previous_layer)
                if previous_value is not None:
                    return float(previous_value)
        return 0.2

    def _set_layer_thickness_value(self, layer_name: str, thickness: float) -> None:
        if self.document is None:
            return
        if thickness <= 0:
            self.document.layer_thicknesses.pop(layer_name, None)
        else:
            self.document.layer_thicknesses[layer_name] = thickness

    def _set_entity_thickness_value(self, entity_index: int, thickness: float) -> None:
        if self.document is None:
            return
        if thickness <= 0:
            self.document.entity_thicknesses.pop(entity_index, None)
        else:
            self.document.entity_thicknesses[entity_index] = thickness

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
            self._set_status_message(
                f"Selected {entity_type} on layer {layer_name} with thickness {thickness:.3f} mm.",
                stage="Selected",
                tone="busy",
            )
        else:
            self._set_status_message(
                f"Selected {entity_type} on layer {layer_name}.",
                stage="Selected",
                tone="busy",
            )

    def _handle_semantic_item_selected(self, payload: object) -> None:
        if self.document is None:
            return

        if not isinstance(payload, dict):
            self.document.selected_semantic_key = None
            return

        semantic_item = payload.get("item")
        semantic_key = payload.get("key")
        if semantic_item is None or not isinstance(semantic_key, str):
            self.document.selected_semantic_key = None
            return

        layer_name = getattr(semantic_item, "layer_name", None)
        source_indices = tuple(getattr(semantic_item, "source_indices", ()) or ())
        selected_index = source_indices[0] if source_indices else None
        visibility_changed = False

        if isinstance(layer_name, str) and layer_name:
            if layer_name not in self.document.visible_layers:
                self.document.visible_layers.add(layer_name)
                visibility_changed = True
            self.document.selected_layer_name = layer_name

        self.document.selected_semantic_key = semantic_key
        self.document.selected_entity_index = selected_index

        if self._layer_affects_stack_preview(layer_name if isinstance(layer_name, str) else None) and (
            self.document.stack_preview_assembly is not None
            or self.document.layer_thicknesses
            or self.document.entity_thicknesses
        ):
            self._rebuild_stack_preview()

        self.preview.load_document(self.document)
        self.preview.focus_entity(selected_index)
        self.layer_panel.load_document(self.document)

        kind_label = getattr(semantic_item, "kind", "object")
        kind_label = str(kind_label).removesuffix("_candidate").replace("_", " ")
        if isinstance(layer_name, str) and layer_name:
            self._set_status_message(
                f"Selected {kind_label} on layer {layer_name}.",
                stage="Selected",
                tone="busy",
            )
        else:
            self._set_status_message(
                f"Selected {kind_label}.",
                stage="Selected",
                tone="busy",
            )

    def _handle_review_override_requested(self, payload: object) -> None:
        if self.document is None or self.document.semantic_result is None:
            return
        if not isinstance(payload, dict):
            return

        semantic_item = payload.get("item")
        if semantic_item is None:
            return

        candidate_id = getattr(semantic_item, "id", None)
        kind_label = str(getattr(semantic_item, "kind", "review")).removesuffix("_candidate").replace("_", " ")
        if not isinstance(candidate_id, str):
            return

        options = [kind.replace("_", " ").title() for kind in MANUAL_REVIEW_KIND_OPTIONS]
        current_index = 0
        selected_label, accepted = QInputDialog.getItem(
            self,
            "Classify review item",
            f"Assign semantic class for {kind_label}:",
            options,
            current_index,
            False,
        )
        if not accepted or not selected_label:
            return

        target_kind = selected_label.lower().replace(" ", "_")
        layer_name = getattr(semantic_item, "layer_name", None)
        source_indices = tuple(getattr(semantic_item, "source_indices", ()) or ())
        self.document.semantic_overrides[candidate_id] = target_kind
        sync_answer = QMessageBox.question(
            self,
            "Sync layer semantic role",
            (
                f"Use {selected_label} as the default semantic role for layer "
                f"'{layer_name}' in this DXF session?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if sync_answer == QMessageBox.StandardButton.Yes and isinstance(layer_name, str) and layer_name:
            self.document.layer_semantic_overrides[layer_name] = target_kind
            self.layer_semantic_store.remember_layer_role(layer_name, target_kind)

        self.document.layer_info = apply_layer_role_overrides(
            self.document.layer_info,
            self.document.layer_semantic_overrides,
        )
        base_semantic_result = classify_semantic_layers(self.document.raw_entities, self.document.layer_info)
        self.document.semantic_result = apply_manual_semantic_overrides(
            base_semantic_result,
            self.document.semantic_overrides,
        )
        selected_key, selected_item = self._find_semantic_selection(
            self.document.semantic_result,
            layer_name=layer_name if isinstance(layer_name, str) else None,
            source_indices=source_indices,
            preferred_kind=target_kind,
        )
        if selected_key is None:
            selected_key = manual_override_entity_key(candidate_id, target_kind)
            selected_item = next(
                (
                    entity
                    for entity in self.document.semantic_result.entities
                    if entity.id == selected_key.removeprefix("entity:")
                ),
                None,
            )

        self.document.selected_semantic_key = selected_key
        self.layer_panel.load_document(self.document)
        if selected_key and selected_item is not None:
            self._handle_semantic_item_selected({"key": selected_key, "item": selected_item})
        self._set_status_message(
            f"Review item classified as {target_kind.replace('_', ' ')}.",
            stage="Updated",
            tone="good",
        )

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
        payload = self._prompt_thickness(
            title="Set thickness",
            headline=f"Thickness for {entity.get('layer', '0')} ({entity_type})",
            detail="Use a quick preset or type a value in millimeters.",
            current_value=current,
        )
        if payload is None:
            return

        thickness = float(payload["thickness"])
        self._set_entity_thickness_value(entity_index, thickness)

        self._rebuild_stack_preview()

        layer_name = entity.get("layer", "0")
        if thickness <= 0:
            self._set_status_message(
                f"Cleared entity thickness on layer {layer_name}.",
                stage="Thickness",
                tone="good",
            )
        else:
            self._set_status_message(
                f"Entity thickness on layer {layer_name} set to {thickness:.3f} mm.",
                stage="Thickness",
                tone="good",
            )

    def _handle_layer_visibility_changed(self, layer_name: str, visible: bool) -> None:
        if self.document is None:
            return

        if visible:
            self.document.visible_layers.add(layer_name)
        else:
            self.document.visible_layers.discard(layer_name)
            if self.document.selected_layer_name == layer_name:
                self.document.selected_layer_name = None

        self.preview.load_document(self.document)
        self.layer_panel.load_document(self.document)
        if self._layer_affects_stack_preview(layer_name) and (
            self.document.stack_preview_assembly is not None
            or self.document.layer_thicknesses
            or self.document.entity_thicknesses
        ):
            self._rebuild_stack_preview()

    def _handle_layer_selected(self, layer_name: object) -> None:
        if self.document is None:
            return

        normalized = str(layer_name) if isinstance(layer_name, str) else None
        self.document.selected_layer_name = normalized
        self.preview.load_document(self.document)
        if normalized is None:
            self._set_status_message(
                "Layer focus cleared.",
                stage="Layers",
            )
            return

        thickness = self.document.layer_thicknesses.get(normalized)
        if thickness is None:
            self._set_status_message(
                f"Layer selected: {normalized}.",
                stage="Layers",
            )
        else:
            self._set_status_message(
                f"Layer selected: {normalized} with thickness {thickness:.3f} mm.",
                stage="Layers",
            )

    def _edit_layer_thickness(self, layer_name: str) -> None:
        if self.document is None:
            return
        if not self._layer_affects_stack_preview(layer_name):
            self._set_status_message(
                f"Layer {layer_name} is excluded from the stacked 3D preview.",
                stage="Layers",
            )
            return

        current = float(self.document.layer_thicknesses.get(layer_name, 0.2))
        payload = self._prompt_thickness(
            title="Set layer thickness",
            headline=f"Thickness for layer {layer_name}",
            detail="Use a quick preset or type a value in millimeters.",
            current_value=current,
        )
        if payload is None:
            return

        thickness = float(payload["thickness"])
        self._set_layer_thickness_value(layer_name, thickness)

        self._rebuild_stack_preview()
        self.layer_panel.load_document(self.document)
        if thickness <= 0:
            self._set_status_message(
                f"Cleared thickness for layer {layer_name}.",
                stage="Thickness",
                tone="good",
            )
        else:
            self._set_status_message(
                f"Layer thickness set: {layer_name} -> {thickness:.3f} mm.",
                stage="Thickness",
                tone="good",
            )

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

        self._set_status_message(
            "Coordinates exported successfully.",
            stage="Exported",
            tone="good",
        )

    def _export_wire_production_files(self) -> None:
        if self.document is None:
            QMessageBox.information(self, "Wire production export", "Import a DXF file first.")
            return
        if not self.document.wire_geometries:
            QMessageBox.information(
                self,
                "Wire production export",
                "No 06_wire geometry was detected in the current document.",
            )
            return

        dialog = WireExportDialog(
            self.document,
            self.wire_template_store,
            self.output_directory,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        request = dialog.export_request()
        if request is None:
            return

        try:
            result = self.wire_production_exporter.export_bundle(
                self.document.wire_geometries,
                request.template,
                request.output_directory,
                base_name=request.base_name,
                export_wb1=request.export_wb1,
                export_xlsm=request.export_xlsm,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Wire production export", str(exc))
            return

        self.output_directory = request.output_directory
        exported_paths = [str(path) for path in (result.wb1_path, result.xlsm_path) if path is not None]
        self._set_status_message(
            f"Wire production files exported: {request.base_name}.",
            stage="Exported",
            tone="good",
        )
        QMessageBox.information(
            self,
            "Wire production export",
            "Export completed:\n" + "\n".join(exported_paths),
        )

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

        assembly = self._full_step_export_assembly()
        if assembly is None:
            QMessageBox.critical(self, "Export STEP", "No 3D model is available for export.")
            return

        converter = BondingDiagramConverter(self._config())
        if not converter.export_step(assembly, output_path):
            QMessageBox.critical(self, "Export STEP", "Failed to export the STEP model.")
            return

        self._set_status_message(
            "STEP model exported successfully.",
            stage="Exported",
            tone="good",
        )
