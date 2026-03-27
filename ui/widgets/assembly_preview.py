"""3D assembly preview widgets."""

from __future__ import annotations

from functools import partial
from typing import Any

from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from PySide6.QtCore import QByteArray, QThread, QTimer, Qt
from PySide6.QtGui import QColor, QVector3D
from PySide6.QtWidgets import QFrame, QLabel, QStackedLayout, QVBoxLayout, QWidget

from services import ProjectDocument

from .mesh_worker import PreviewMeshWorker
from .viewer_placeholder import ViewerPlaceholder


class AssemblyPreviewWidget(QWidget):
    """Hardware-accelerated 3D preview built with Qt3D."""

    FINE_MESH_DELAY_MS = 450

    def __init__(self):
        super().__init__()
        self.setObjectName("ViewerSurface")
        self.setMinimumHeight(320)

        self._window = Qt3DExtras.Qt3DWindow()
        self._window.defaultFrameGraph().setClearColor(QColor("#171717"))
        self._container = QWidget.createWindowContainer(self._window, self)
        self._container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._placeholder_page = QWidget()
        placeholder_layout = QVBoxLayout(self._placeholder_page)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.addStretch(1)
        self.placeholder = ViewerPlaceholder("3D Preview", "Import DXF", "cube")
        placeholder_layout.addWidget(self.placeholder, alignment=Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addStretch(1)

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._placeholder_page)
        self._stack.addWidget(self._container)

        self._current_root: Any | None = None
        self._load_token = 0
        self._mesh_threads: list[QThread] = []
        self._mesh_workers: list[PreviewMeshWorker] = []
        self._loaded_fine_tokens: set[int] = set()
        self._pending_assembly: Any | None = None
        self._allow_fine_mesh = True
        self._progressive_mesh_bytes = QByteArray()
        self._progressive_vertex_count = 0
        self._progressive_diagonal = 1.0
        self._fine_timer = QTimer(self)
        self._fine_timer.setSingleShot(True)
        self._fine_timer.timeout.connect(self._start_scheduled_fine_mesh)
        self._empty_scene()

    def load_assembly(self, assembly: Any | None, *, progressive: bool = False) -> None:
        self._load_token += 1
        self._loaded_fine_tokens.discard(self._load_token)
        self._fine_timer.stop()
        self._allow_fine_mesh = not progressive
        self._reset_progressive_mesh()

        if assembly is None or not getattr(assembly, "objects", {}):
            self.placeholder.set_content("3D Preview", "Import DXF")
            self._empty_scene()
            return

        self._pending_assembly = assembly
        self.placeholder.set_content("3D Preview", "Building layer mesh" if progressive else "Generating mesh")
        self._stack.setCurrentWidget(self._placeholder_page)
        self._start_mesh_job(assembly, "coarse", self._load_token)

    def _start_mesh_job(self, assembly: Any, quality: str, token: int) -> None:
        thread = QThread(self)
        worker = PreviewMeshWorker(assembly, quality, token)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.mesh_ready.connect(self._handle_mesh_ready)
        worker.failed.connect(self._handle_mesh_failure)
        worker.mesh_ready.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(partial(self._cleanup_mesh_job, thread, worker))

        self._mesh_threads.append(thread)
        self._mesh_workers.append(worker)
        thread.start()

    def _cleanup_mesh_job(self, thread: QThread, worker: PreviewMeshWorker) -> None:
        if thread in self._mesh_threads:
            self._mesh_threads.remove(thread)
        if worker in self._mesh_workers:
            self._mesh_workers.remove(worker)

    def _handle_mesh_ready(
        self,
        token: int,
        quality: str,
        mesh_bytes: Any,
        vertex_count: int,
        diagonal: float,
    ) -> None:
        if token != self._load_token:
            return

        if vertex_count <= 0:
            if quality == "coarse":
                self.placeholder.set_content("3D Preview", "Model unavailable")
                self._empty_scene()
            return

        self._current_root = self._build_scene(mesh_bytes, vertex_count, diagonal)
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._container)

        if quality == "coarse" and self._allow_fine_mesh and token not in self._loaded_fine_tokens:
            self._loaded_fine_tokens.add(token)
            self._fine_timer.start(self.FINE_MESH_DELAY_MS)

    def _handle_mesh_failure(self, token: int, quality: str, _message: str) -> None:
        if token != self._load_token:
            return
        if quality == "coarse":
            self.placeholder.set_content("3D Preview", "Model unavailable")
            self._empty_scene()

    def _start_scheduled_fine_mesh(self) -> None:
        assembly = self._current_assembly()
        if assembly is None or self._load_token not in self._loaded_fine_tokens:
            return
        self._start_mesh_job(assembly, "fine", self._load_token)

    def _current_assembly(self) -> Any | None:
        return self._pending_assembly

    def append_progressive_mesh(self, mesh_bytes: QByteArray, vertex_count: int, diagonal: float) -> None:
        """Append one coarse mesh chunk during staged import."""

        if vertex_count <= 0:
            return

        self._fine_timer.stop()
        self._pending_assembly = None
        self._allow_fine_mesh = False
        self._progressive_mesh_bytes.append(mesh_bytes)
        self._progressive_vertex_count += vertex_count
        self._progressive_diagonal = max(self._progressive_diagonal, float(diagonal), 1.0)
        self._current_root = self._build_scene(
            self._progressive_mesh_bytes,
            self._progressive_vertex_count,
            self._progressive_diagonal,
        )
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._container)

    def _reset_progressive_mesh(self) -> None:
        self._progressive_mesh_bytes = QByteArray()
        self._progressive_vertex_count = 0
        self._progressive_diagonal = 1.0

    def _empty_scene(self) -> None:
        self._fine_timer.stop()
        self._pending_assembly = None
        self._allow_fine_mesh = True
        self._reset_progressive_mesh()
        self._current_root = Qt3DCore.QEntity()
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._placeholder_page)

    def _build_scene(self, mesh_bytes: Any, vertex_count: int, diagonal: float) -> Any:
        root = Qt3DCore.QEntity()

        self._configure_camera(diagonal)
        controller = Qt3DExtras.QOrbitCameraController(root)
        controller.setCamera(self._window.camera())
        controller.setLinearSpeed(max(diagonal * 0.35, 2.0))
        controller.setLookSpeed(180.0)

        light_entity = Qt3DCore.QEntity(root)
        light = Qt3DRender.QDirectionalLight(light_entity)
        light.setColor(QColor("#FFF2E3"))
        light.setIntensity(1.45)
        light.setWorldDirection(QVector3D(-0.6, -0.55, -1.0))
        light_entity.addComponent(light)

        fill_light_entity = Qt3DCore.QEntity(root)
        fill_light = Qt3DRender.QDirectionalLight(fill_light_entity)
        fill_light.setColor(QColor("#F36B39"))
        fill_light.setIntensity(0.55)
        fill_light.setWorldDirection(QVector3D(0.45, 0.2, -0.35))
        fill_light_entity.addComponent(fill_light)

        model_entity = Qt3DCore.QEntity(root)
        geometry = self._create_geometry(model_entity, mesh_bytes, vertex_count)
        renderer = Qt3DRender.QGeometryRenderer(model_entity)
        renderer.setGeometry(geometry)
        renderer.setPrimitiveType(Qt3DRender.QGeometryRenderer.PrimitiveType.Triangles)
        renderer.setVertexCount(vertex_count)

        material = Qt3DExtras.QPhongMaterial(model_entity)
        material.setAmbient(QColor("#4B170B"))
        material.setDiffuse(QColor("#D45B2E"))
        material.setSpecular(QColor("#FFD9C5"))
        material.setShininess(55.0)

        model_entity.addComponent(renderer)
        model_entity.addComponent(material)
        return root

    def _configure_camera(self, diagonal: float) -> None:
        camera = self._window.camera()
        camera.setProjectionType(Qt3DRender.QCameraLens.ProjectionType.PerspectiveProjection)
        camera.setFieldOfView(38.0)
        camera.setNearPlane(max(diagonal * 0.01, 0.01))
        camera.setFarPlane(max(diagonal * 20.0, 100.0))
        camera.setUpVector(QVector3D(0.0, 0.0, 1.0))
        camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))
        camera.setPosition(QVector3D(diagonal * 1.7, -diagonal * 1.75, diagonal * 1.15))
        aspect_ratio = max(self.width(), 1) / max(self.height(), 1)
        camera.setAspectRatio(aspect_ratio)

    def resizeEvent(self, event) -> None:  # pragma: no cover
        super().resizeEvent(event)
        self._window.camera().setAspectRatio(max(self.width(), 1) / max(self.height(), 1))

    def _create_geometry(self, parent: Any, mesh_bytes: Any, vertex_count: int) -> Any:
        geometry = Qt3DCore.QGeometry(parent)
        buffer = Qt3DCore.QBuffer(geometry)
        buffer.setData(mesh_bytes)

        position_attribute = Qt3DCore.QAttribute(geometry)
        position_attribute.setName(Qt3DCore.QAttribute.defaultPositionAttributeName())
        position_attribute.setAttributeType(Qt3DCore.QAttribute.AttributeType.VertexAttribute)
        position_attribute.setVertexBaseType(Qt3DCore.QAttribute.VertexBaseType.Float)
        position_attribute.setVertexSize(3)
        position_attribute.setByteOffset(0)
        position_attribute.setByteStride(24)
        position_attribute.setCount(vertex_count)
        position_attribute.setBuffer(buffer)

        normal_attribute = Qt3DCore.QAttribute(geometry)
        normal_attribute.setName(Qt3DCore.QAttribute.defaultNormalAttributeName())
        normal_attribute.setAttributeType(Qt3DCore.QAttribute.AttributeType.VertexAttribute)
        normal_attribute.setVertexBaseType(Qt3DCore.QAttribute.VertexBaseType.Float)
        normal_attribute.setVertexSize(3)
        normal_attribute.setByteOffset(12)
        normal_attribute.setByteStride(24)
        normal_attribute.setCount(vertex_count)
        normal_attribute.setBuffer(buffer)

        geometry.addAttribute(position_attribute)
        geometry.addAttribute(normal_attribute)
        return geometry


class ModelPreviewPanel(QFrame):
    """3D viewer shell with a lightweight interactive preview."""

    def __init__(self):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title = QLabel("3D Viewer")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.surface = AssemblyPreviewWidget()
        layout.addWidget(self.surface, stretch=1)

    def load_document(self, document: ProjectDocument | None, *, progressive: bool = False) -> None:
        if document is None:
            self.surface.load_assembly(None)
            return

        self.surface.load_assembly(document.stack_preview_assembly or document.assembly, progressive=progressive)

    def append_progressive_mesh(self, mesh_bytes: QByteArray, vertex_count: int, diagonal: float) -> None:
        self.surface.append_progressive_mesh(mesh_bytes, vertex_count, diagonal)
