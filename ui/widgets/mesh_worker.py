"""Background mesh worker for progressive 3D preview rendering."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from .mesh_payload import build_mesh_payload


class PreviewMeshWorker(QObject):
    """Generate one preview mesh payload in a worker thread."""

    mesh_ready = Signal(int, str, object, int, float)
    failed = Signal(int, str, str)

    def __init__(self, assembly: Any, quality: str, token: int):
        super().__init__()
        self._assembly = assembly
        self._quality = quality
        self._token = token

    @Slot()
    def run(self) -> None:
        try:
            mesh_bytes, vertex_count, diagonal = build_mesh_payload(self._assembly, self._quality)
        except Exception as exc:
            self.failed.emit(self._token, self._quality, str(exc))
            return

        self.mesh_ready.emit(self._token, self._quality, mesh_bytes, vertex_count, diagonal)


__all__ = ["PreviewMeshWorker"]
