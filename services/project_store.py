"""Small state container for the desktop application."""

from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.export.coordinates import BondPoint
from core.geometry.converter import BondingElement
from core.pipeline_types import DRCReport
from core.raw_dxf_types import LayerInfo, RawEntity, SceneRect


@dataclass
class ProjectDocument:
    """Represents one imported DXF file and its derived artifacts."""

    path: Path
    size_bytes: int
    raw_entities: list[RawEntity]
    scene_rect: SceneRect
    raw_counts: Counter[str]
    layer_info: list[LayerInfo] = field(default_factory=list)
    parser_elements: list[BondingElement] = field(default_factory=list)
    converted_counts: Counter[str] = field(default_factory=Counter)
    coordinates: list[BondPoint] = field(default_factory=list)
    drc_report: DRCReport = field(
        default_factory=lambda: {
            "passed": True,
            "total_violations": 0,
            "errors": 0,
            "warnings": 0,
            "violations": [],
        }
    )
    assembly: Any | None = None
    output_path: Path | None = None
    status: str = "ready"
    used_fallback: bool = False
    note: str = "Ready."

    @property
    def key(self) -> str:
        return str(self.path)


class ProjectStore:
    """Keeps track of imported files and the active selection."""

    def __init__(self, project_name: str = "Default Project"):
        self.project_name = project_name
        self._documents: "OrderedDict[str, ProjectDocument]" = OrderedDict()
        self.selected_key: str | None = None

    @property
    def documents(self) -> list[ProjectDocument]:
        return list(self._documents.values())

    def add_document(self, document: ProjectDocument) -> None:
        self._documents[document.key] = document
        self.selected_key = document.key

    def remove_document(self, key: str) -> None:
        self._documents.pop(key, None)
        if self.selected_key == key:
            self.selected_key = next(iter(self._documents), None)

    def clear(self) -> None:
        self._documents.clear()
        self.selected_key = None

    def select(self, key: str | None) -> None:
        if key is None or key in self._documents:
            self.selected_key = key

    def selected(self) -> ProjectDocument | None:
        if self.selected_key is None:
            return None
        return self._documents.get(self.selected_key)
