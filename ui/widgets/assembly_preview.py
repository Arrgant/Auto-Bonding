"""3D assembly preview widgets."""

from __future__ import annotations

from typing import Any

from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QVector3D
from PySide6.QtWidgets import QFrame, QLabel, QStackedLayout, QVBoxLayout, QWidget

from services import ProjectDocument

from .mesh_payload import build_layer_mesh_payloads, build_mesh_payload, layer_payload_rgb
from .viewer_placeholder import ViewerPlaceholder


class AssemblyPreviewWidget(QWidget):
    """Hardware-accelerated 3D preview built with Qt3D."""

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
        self._progressive_mesh_bytes = QByteArray()
        self._progressive_vertex_count = 0
        self._progressive_diagonal = 1.0
        self._empty_scene()

    def load_assembly(self, assembly: Any | None, *, progressive: bool = False) -> None:
        self._reset_progressive_mesh()

        if assembly is None or not getattr(assembly, "objects", {}):
            self.placeholder.set_content("3D Preview", "Import DXF")
            self._empty_scene()
            return

        self.placeholder.set_content("3D Preview", "Building layer mesh" if progressive else "Generating mesh")
        self._stack.setCurrentWidget(self._placeholder_page)
        mesh_bytes, vertex_count, diagonal = build_mesh_payload(assembly, "coarse")
        self.load_mesh_payload(mesh_bytes, vertex_count, diagonal)

    def load_mesh_payload(self, mesh_bytes: QByteArray, vertex_count: int, diagonal: float) -> None:
        """Load one ready-to-render mesh payload into the Qt3D scene."""

        if vertex_count <= 0:
            self.placeholder.set_content("3D Preview", "Model unavailable")
            self._empty_scene()
            return

        self._current_root = self._build_scene(mesh_bytes, vertex_count, diagonal)
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._container)

    def load_layer_meshes(self, layer_meshes: list[dict[str, Any]]) -> None:
        """Load one mesh per layer so the preview can color layers independently."""

        valid_layers = [payload for payload in layer_meshes if int(payload.get("vertex_count", 0)) > 0]
        if not valid_layers:
            self.placeholder.set_content("3D Preview", "Model unavailable")
            self._empty_scene()
            return

        diagonal = max(float(payload.get("diagonal", 1.0)) for payload in valid_layers)
        self._current_root = self._build_layered_scene(valid_layers, diagonal)
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._container)

    def append_progressive_mesh(self, mesh_bytes: QByteArray, vertex_count: int, diagonal: float) -> None:
        """Append one coarse mesh chunk during staged import."""

        if vertex_count <= 0:
            return

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
        self._reset_progressive_mesh()
        self._current_root = Qt3DCore.QEntity()
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._placeholder_page)

    def shutdown(self) -> None:
        """Tear down the Qt3D scene before the widget is destroyed."""

        self._reset_progressive_mesh()
        self._current_root = None
        self._window.setRootEntity(Qt3DCore.QEntity())
        self._stack.setCurrentWidget(self._placeholder_page)

    def _build_scene(self, mesh_bytes: Any, vertex_count: int, diagonal: float) -> Any:
        root = Qt3DCore.QEntity()
        self._prepare_scene_root(root, diagonal)

        model_entity = Qt3DCore.QEntity(root)
        geometry = self._create_geometry(model_entity, mesh_bytes, vertex_count)
        renderer = Qt3DRender.QGeometryRenderer(model_entity)
        renderer.setGeometry(geometry)
        renderer.setPrimitiveType(Qt3DRender.QGeometryRenderer.PrimitiveType.Triangles)
        renderer.setVertexCount(vertex_count)

        material = self._create_material(model_entity, QColor("#D45B2E"))

        model_entity.addComponent(renderer)
        model_entity.addComponent(material)
        return root

    def _build_layered_scene(self, layer_meshes: list[dict[str, Any]], diagonal: float) -> Any:
        root = Qt3DCore.QEntity()
        self._prepare_scene_root(root, diagonal)

        for payload in layer_meshes:
            vertex_count = int(payload["vertex_count"])
            if vertex_count <= 0:
                continue

            mesh_entity = Qt3DCore.QEntity(root)
            geometry = self._create_geometry(mesh_entity, payload["mesh_bytes"], vertex_count)
            renderer = Qt3DRender.QGeometryRenderer(mesh_entity)
            renderer.setGeometry(geometry)
            renderer.setPrimitiveType(Qt3DRender.QGeometryRenderer.PrimitiveType.Triangles)
            renderer.setVertexCount(vertex_count)

            red, green, blue = layer_payload_rgb(payload)
            material = self._create_material(mesh_entity, QColor(red, green, blue))

            mesh_entity.addComponent(renderer)
            mesh_entity.addComponent(material)

        return root

    def _prepare_scene_root(self, root: Qt3DCore.QEntity, diagonal: float) -> None:
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

    def _create_material(self, parent: Qt3DCore.QEntity, base_color: QColor) -> Qt3DExtras.QPhongMaterial:
        material = Qt3DExtras.QPhongMaterial(parent)
        material.setAmbient(base_color.darker(210))
        material.setDiffuse(base_color)
        material.setSpecular(base_color.lighter(180))
        material.setShininess(55.0)
        return material

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

        if document.stack_preview_assembly is not None:
            layer_meshes = build_layer_mesh_payloads(document.stack_preview_assembly, document.layer_colors)
            if layer_meshes:
                self.surface.load_layer_meshes(layer_meshes)
            else:
                self.surface.load_assembly(document.stack_preview_assembly, progressive=progressive)
            return

        if document.layer_meshes:
            self.surface.load_layer_meshes(document.layer_meshes)
            return

        if document.mesh_bytes is not None and document.mesh_vertex_count > 0:
            self.surface.load_mesh_payload(
                document.mesh_bytes,
                document.mesh_vertex_count,
                document.mesh_diagonal,
            )
        else:
            self.surface.load_assembly(document.assembly, progressive=progressive)

    def append_progressive_mesh(self, mesh_bytes: QByteArray, vertex_count: int, diagonal: float) -> None:
        self.surface.append_progressive_mesh(mesh_bytes, vertex_count, diagonal)

    def shutdown(self) -> None:
        self.surface.shutdown()
