"""Background worker for rebuilding stacked 3D preview payloads."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from core.layer_stack import build_stacked_preview_assembly
from .widgets.mesh_payload import build_layer_mesh_payloads


class StackPreviewWorker(QObject):
    """Build stacked preview assemblies off the UI thread."""

    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(
        self,
        raw_entities: list[dict[str, Any]],
        layer_info: list[dict[str, Any]],
        entity_thicknesses: dict[int, float],
        layer_thicknesses: dict[str, float],
        visible_layers: set[str],
        layer_colors: dict[str, str],
    ) -> None:
        super().__init__()
        self.raw_entities = raw_entities
        self.layer_info = layer_info
        self.entity_thicknesses = entity_thicknesses
        self.layer_thicknesses = layer_thicknesses
        self.visible_layers = visible_layers
        self.layer_colors = layer_colors

    def run(self) -> None:
        try:
            assembly = build_stacked_preview_assembly(
                self.raw_entities,
                self.layer_info,
                self.entity_thicknesses,
                layer_thicknesses=self.layer_thicknesses,
                visible_layers=self.visible_layers,
            )
            layer_meshes = build_layer_mesh_payloads(assembly, self.layer_colors) if assembly is not None else []
        except Exception as exc:  # pragma: no cover - defensive Qt thread path
            self.failed.emit(str(exc))
            return

        self.finished.emit(assembly, layer_meshes)


__all__ = ["StackPreviewWorker"]
