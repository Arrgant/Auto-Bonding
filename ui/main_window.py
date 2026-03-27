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
from core.layer_colors import build_layer_color_map
from core.layer_semantics import apply_layer_role_overrides
from core.layer_stack import build_stacked_preview_assembly
from core.semantic import (
    MANUAL_REVIEW_KIND_OPTIONS,
    SemanticClassificationResult,
    apply_manual_semantic_overrides,
    classify_semantic_layers,
    manual_override_entity_key,
)
from services import LayerSemanticPresetStore, ProjectDocument

from .import_worker import ImportWorker
from .layer_config_dialog import LayerConfigDialog
from .layer_semantic_preset_dialog import LayerSemanticPresetDialog
from .widgets import DXFPreviewView, LayerManagerPanel, ModelPreviewPanel, SemanticObjectsPanel


class MainWindow(QMainWindow):
    """Main desktop window with a 2D viewer and a 3D viewer."""

    def __init__(self):
        super().__init__()
        self.document: ProjectDocument | None = None
        self.output_directory = Path.cwd() / "output"
        self.output_directory.mkdir(exist_ok=True)
        self.exporter = CoordinateExporter()
        self.layer_semantic_store = LayerSemanticPresetStore()
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

        left_body = QWidget()
        left_body_layout = QHBoxLayout(left_body)
        left_body_layout.setContentsMargins(0, 0, 0, 0)
        left_body_layout.setSpacing(12)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(12)

        self.layer_panel = LayerManagerPanel()
        sidebar_layout.addWidget(self.layer_panel, stretch=1)

        self.semantic_panel = SemanticObjectsPanel()
        sidebar_layout.addWidget(self.semantic_panel, stretch=1)

        left_body_layout.addWidget(sidebar)

        self.preview = DXFPreviewView()
        left_body_layout.addWidget(self.preview, stretch=1)
        left_layout.addWidget(left_body, stretch=1)
        split.addWidget(left_panel)

        self.model_preview = ModelPreviewPanel()
        split.addWidget(self.model_preview)
        split.setSizes([820, 620])

        self.preview.file_drop_handler = self._load_document
        self.preview.selection_changed_handler = self._handle_preview_selection
        self.preview.closed_shape_click_handler = self._configure_shape_thickness
        self.layer_panel.layer_visibility_changed.connect(self._handle_layer_visibility_changed)
        self.layer_panel.layer_selected.connect(self._handle_layer_selected)
        self.layer_panel.layer_thickness_requested.connect(self._edit_layer_thickness)
        self.semantic_panel.semantic_item_selected.connect(self._handle_semantic_item_selected)
        self.semantic_panel.review_override_requested.connect(self._handle_review_override_requested)
        self.semantic_panel.preset_manage_requested.connect(self._open_semantic_preset_manager)

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

    def _open_semantic_preset_manager(self) -> None:
        dialog = LayerSemanticPresetDialog(self.layer_semantic_store.list_presets(), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated_presets = dialog.result_presets()
        before = self.layer_semantic_store.list_presets()
        if updated_presets == before:
            return

        self.layer_semantic_store.replace_presets(updated_presets)
        self.status_label.setText(
            "Semantic presets updated. Re-import the DXF to apply changes to the current session."
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

        self.document.stack_preview_assembly = build_stacked_preview_assembly(
            self.document.raw_entities,
            self.document.layer_info,
            self.document.entity_thicknesses,
            layer_thicknesses=self.document.layer_thicknesses,
            visible_layers=self.document.visible_layers,
        )
        self.model_preview.load_document(self.document)

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
        self.layer_panel.load_document(self.document)
        self.semantic_panel.load_document(self.document)
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

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI teardown path
        if self._import_worker is not None:
            try:
                self._import_worker.failed.disconnect(self._finish_import_thread)
                self._import_worker.finished.disconnect(self._finish_import_thread)
            except (RuntimeError, TypeError):
                pass
        self._finish_import_thread()
        self.model_preview.shutdown()
        super().closeEvent(event)

    def _update_ui(self) -> None:
        self.preview.load_document(self.document)
        self.layer_panel.load_document(self.document)
        self.semantic_panel.load_document(self.document)
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

        if visibility_changed and (
            self.document.stack_preview_assembly is not None
            or self.document.layer_thicknesses
            or self.document.entity_thicknesses
        ):
            self._rebuild_stack_preview()

        self.preview.load_document(self.document)
        self.preview.focus_entity(selected_index)
        self.layer_panel.load_document(self.document)
        self.semantic_panel.load_document(self.document)

        kind_label = getattr(semantic_item, "kind", "object")
        kind_label = str(kind_label).removesuffix("_candidate").replace("_", " ")
        if isinstance(layer_name, str) and layer_name:
            self.status_label.setText(
                f"Selected {kind_label} on layer {layer_name}"
            )
        else:
            self.status_label.setText(f"Selected {kind_label}")

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
        self.semantic_panel.load_document(self.document)
        if selected_key and selected_item is not None:
            self._handle_semantic_item_selected({"key": selected_key, "item": selected_item})
        self.status_label.setText(
            f"Review item classified as {target_kind.replace('_', ' ')}"
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

        self._rebuild_stack_preview()

        layer_name = entity.get("layer", "0")
        if thickness <= 0:
            self.status_label.setText(f"Cleared thickness for layer {layer_name}")
        else:
            self.status_label.setText(f"Thickness set: {layer_name} -> {thickness:.3f} mm")

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
        if self.document.stack_preview_assembly is not None or self.document.layer_thicknesses or self.document.entity_thicknesses:
            self._rebuild_stack_preview()

    def _handle_layer_selected(self, layer_name: object) -> None:
        if self.document is None:
            return

        normalized = str(layer_name) if isinstance(layer_name, str) else None
        self.document.selected_layer_name = normalized
        self.preview.load_document(self.document)
        if normalized is None:
            self.status_label.setText(f"{self.document.path.name} | layer focus cleared")
            return

        thickness = self.document.layer_thicknesses.get(normalized)
        if thickness is None:
            self.status_label.setText(f"Layer selected: {normalized}")
        else:
            self.status_label.setText(f"Layer selected: {normalized} | thickness {thickness:.3f} mm")

    def _edit_layer_thickness(self, layer_name: str) -> None:
        if self.document is None:
            return

        current = float(self.document.layer_thicknesses.get(layer_name, 0.2))
        thickness, accepted = QInputDialog.getDouble(
            self,
            "Set layer thickness",
            f"Thickness for layer {layer_name}",
            current,
            0.0,
            50.0,
            3,
        )
        if not accepted:
            return

        if thickness <= 0:
            self.document.layer_thicknesses.pop(layer_name, None)
        else:
            self.document.layer_thicknesses[layer_name] = thickness

        self._rebuild_stack_preview()
        self.layer_panel.load_document(self.document)
        if thickness <= 0:
            self.status_label.setText(f"Cleared thickness for layer {layer_name}")
        else:
            self.status_label.setText(f"Layer thickness set: {layer_name} -> {thickness:.3f} mm")

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
