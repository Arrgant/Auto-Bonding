"""Background import worker for staged DXF loading."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import cadquery as cq
from PySide6.QtCore import QObject, Signal, Slot

from core import BondingDiagramConverter, PreparedDocument, RawImportPreview, load_import_preview
from core.pipeline import finalize_prepared_document, group_elements_by_layer, resolve_preview_elements
from ui.widgets.mesh_payload import build_mesh_payload


class ImportWorker(QObject):
    """Run staged DXF import and conversion work away from the UI thread."""

    preview_ready = Signal(str, object)
    progress_ready = Signal(str, object)
    finished = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, file_path: Path, config: dict[str, Any]):
        super().__init__()
        self._file_path = Path(file_path)
        self._config = dict(config)

    @Slot()
    def run(self) -> None:
        try:
            enabled_layers = set(self._config.get("enabled_layers", [])) or None
            layer_mapping = dict(self._config.get("layer_mapping_overrides", {})) or None
            preview: RawImportPreview = load_import_preview(
                self._file_path,
                enabled_layers=enabled_layers,
                layer_mapping=layer_mapping,
            )
            self.preview_ready.emit(str(self._file_path), preview)
            elements, used_fallback = resolve_preview_elements(preview, self._config)
            converter = BondingDiagramConverter(self._config)
            layer_groups = group_elements_by_layer(elements)
            assembly = cq.Assembly()
            converted_counts: Counter[str] = Counter()
            scene_rect = preview["scene_rect"]
            center_override = (
                float(scene_rect[0] + (scene_rect[2] / 2.0)),
                float(-(scene_rect[1] + (scene_rect[3] / 2.0))),
                0.0,
            )
            diagonal_override = max(
                float(scene_rect[2]),
                float(scene_rect[3]),
                1.0,
            )

            for completed_layers, (layer_name, layer_elements) in enumerate(layer_groups, start=1):
                layer_assembly = converter.convert_elements(layer_elements)
                self._merge_assembly(assembly, layer_assembly)
                converted_counts.update(element.element_type for element in layer_elements)
                mesh_bytes, vertex_count, diagonal = build_mesh_payload(
                    layer_assembly,
                    "coarse",
                    center_override=center_override,
                    diagonal_override=diagonal_override,
                    progressive_filter=True,
                )
                self.progress_ready.emit(
                    str(self._file_path),
                    {
                        "layer_name": layer_name,
                        "completed_layers": completed_layers,
                        "total_layers": len(layer_groups),
                        "converted_counts": Counter(converted_counts),
                        "mesh_bytes": mesh_bytes,
                        "vertex_count": vertex_count,
                        "diagonal": diagonal,
                    },
                )

            prepared: PreparedDocument = finalize_prepared_document(
                preview,
                self._config,
                elements=elements,
                assembly=assembly,
                used_fallback=used_fallback,
            )
        except Exception as exc:
            self.failed.emit(str(self._file_path), str(exc))
            return

        self.finished.emit(str(self._file_path), prepared)

    def _merge_assembly(self, target: cq.Assembly, source: cq.Assembly) -> None:
        """Append one layer assembly into the cumulative final assembly."""

        for child in getattr(source, "children", []):
            self._merge_node(target, child)

    def _merge_node(self, target: cq.Assembly, node: cq.Assembly) -> None:
        base_name = getattr(node, "name", None) or "part"
        unique_name = base_name
        while unique_name in target.objects:
            unique_name = f"{base_name}_{len(target.objects)}"

        if getattr(node, "obj", None) is not None:
            target.add(
                node.obj,
                name=unique_name,
                color=getattr(node, "color", None),
                loc=getattr(node, "loc", None),
                metadata=dict(getattr(node, "metadata", {}) or {}),
            )
            return

        nested = cq.Assembly(
            loc=getattr(node, "loc", None),
            name=unique_name,
            color=getattr(node, "color", None),
            metadata=dict(getattr(node, "metadata", {}) or {}),
        )
        for child in getattr(node, "children", []):
            self._merge_node(nested, child)
        target.add(
            nested,
            name=unique_name,
            color=getattr(node, "color", None),
            loc=getattr(node, "loc", None),
            metadata=dict(getattr(node, "metadata", {}) or {}),
        )


__all__ = ["ImportWorker"]
