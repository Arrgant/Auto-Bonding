"""3D assembly preview widgets."""

from __future__ import annotations

import math
import struct
from typing import Any

from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QVector3D
from PySide6.QtWidgets import QFrame, QLabel, QStackedLayout, QVBoxLayout, QWidget

from services import ProjectDocument

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
        self._empty_scene()

    def load_assembly(self, assembly: Any | None) -> None:
        if assembly is None or not getattr(assembly, "objects", {}):
            self.placeholder.set_content("3D Preview", "Import DXF")
            self._empty_scene()
            return

        try:
            mesh_bytes, vertex_count, diagonal = self._build_mesh_payload(assembly)
        except Exception:
            mesh_bytes, vertex_count, diagonal = QByteArray(), 0, 1.0

        if vertex_count <= 0:
            self.placeholder.set_content("3D Preview", "Model unavailable")
            self._empty_scene()
            return

        self._current_root = self._build_scene(mesh_bytes, vertex_count, diagonal)
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._container)

    def _empty_scene(self) -> None:
        self._current_root = Qt3DCore.QEntity()
        self._window.setRootEntity(self._current_root)
        self._stack.setCurrentWidget(self._placeholder_page)

    def _build_scene(self, mesh_bytes: QByteArray, vertex_count: int, diagonal: float) -> Any:
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

    def _build_mesh_payload(self, assembly: Any) -> tuple[QByteArray, int, float]:
        compound = assembly.toCompound() if hasattr(assembly, "toCompound") else None
        if compound is None:
            return QByteArray(), 0, 1.0

        bbox = compound.BoundingBox()
        diagonal = max(float(bbox.xlen), float(bbox.ylen), float(bbox.zlen), 1.0)
        tolerance = max(diagonal / 20.0, 0.75)
        vertices, triangles = compound.tessellate(tolerance)
        if not triangles:
            return QByteArray(), 0, diagonal

        max_triangles = 90000
        stride = max(1, math.ceil(len(triangles) / max_triangles))
        sampled_triangles = triangles[::stride]
        center = (
            float(bbox.xmin + bbox.xmax) / 2.0,
            float(bbox.ymin + bbox.ymax) / 2.0,
            float(bbox.zmin + bbox.zmax) / 2.0,
        )

        payload = bytearray()
        vertex_count = 0
        for indexes in sampled_triangles:
            p1 = self._normalize_vertex(vertices[indexes[0]], center)
            p2 = self._normalize_vertex(vertices[indexes[1]], center)
            p3 = self._normalize_vertex(vertices[indexes[2]], center)
            nx, ny, nz = self._triangle_normal(p1, p2, p3)
            payload.extend(struct.pack("6f", *p1, nx, ny, nz))
            payload.extend(struct.pack("6f", *p2, nx, ny, nz))
            payload.extend(struct.pack("6f", *p3, nx, ny, nz))
            vertex_count += 3

        return QByteArray(bytes(payload)), vertex_count, diagonal

    def _create_geometry(self, parent: Any, mesh_bytes: QByteArray, vertex_count: int) -> Any:
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

    @staticmethod
    def _normalize_vertex(vertex: Any, center: tuple[float, float, float]) -> tuple[float, float, float]:
        raw = vertex.toTuple() if hasattr(vertex, "toTuple") else tuple(vertex)
        return (
            float(raw[0]) - center[0],
            float(raw[1]) - center[1],
            float(raw[2]) - center[2],
        )

    @staticmethod
    def _triangle_normal(
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        p3: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        ux, uy, uz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
        vx, vy, vz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length <= 1e-9:
            return 0.0, 0.0, 1.0
        return nx / length, ny / length, nz / length


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

    def load_document(self, document: ProjectDocument | None) -> None:
        self.surface.load_assembly(None if document is None else document.assembly)
