"""DXF preview widget tests."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QGraphicsView

from services import ProjectDocument
from ui.widgets.dxf_preview import DXFPreviewView, SOURCE_INDICES_ROLE


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dxf_preview_focus_entity_uses_source_indices_for_merged_lines():
    _app()
    view = DXFPreviewView()
    selected_indices: list[int | None] = []
    view.selection_changed_handler = selected_indices.append

    document = ProjectDocument(
        path=Path("preview.dxf"),
        size_bytes=0,
        raw_entities=[
            {"type": "LINE", "start": (0.0, 0.0), "end": (5.0, 0.0), "layer": "06_wire"},
            {"type": "LINE", "start": (5.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        ],
        scene_rect=(0.0, -1.0, 10.0, 2.0),
        raw_counts=Counter({"LINE": 2}),
        layer_info=[
            {
                "name": "06_wire",
                "color": 3,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": "wire",
                "suggested_role": "wire",
                "entity_count": 2,
                "entity_types": {"LINE": 2},
            }
        ],
        visible_layers={"06_wire"},
        enabled_layers={"06_wire"},
        selected_entity_index=1,
    )

    view.load_document(document)

    assert selected_indices[-1] == 1
    selected_items = view.scene().selectedItems()
    assert len(selected_items) == 1
    assert 1 in selected_items[0].data(SOURCE_INDICES_ROLE)

    view.deleteLater()


def test_dxf_preview_uses_distinct_layer_colors():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_layers.dxf"),
        size_bytes=0,
        raw_entities=[
            {"type": "LINE", "start": (0.0, 0.0), "end": (5.0, 0.0), "layer": "01_base"},
            {"type": "LINE", "start": (0.0, 2.0), "end": (5.0, 2.0), "layer": "02_top"},
        ],
        scene_rect=(0.0, -1.0, 10.0, 4.0),
        raw_counts=Counter({"LINE": 2}),
        layer_info=[
            {
                "name": "01_base",
                "color": 1,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 1,
                "entity_types": {"LINE": 1},
            },
            {
                "name": "02_top",
                "color": 2,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 1,
                "entity_types": {"LINE": 1},
            },
        ],
        visible_layers={"01_base", "02_top"},
        enabled_layers={"01_base", "02_top"},
    )

    view.load_document(document)

    items = [item for item in view.scene().items() if item.data(SOURCE_INDICES_ROLE) is not None]
    assert len(items) == 2
    colors = {item.pen().color().name().upper() for item in items}
    assert len(colors) == 2

    view.deleteLater()


def test_dxf_preview_shows_navigation_hint_when_content_is_loaded():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_hint.dxf"),
        size_bytes=0,
        raw_entities=[
            {"type": "LINE", "start": (0.0, 0.0), "end": (5.0, 0.0), "layer": "01_base"},
        ],
        scene_rect=(0.0, -1.0, 10.0, 4.0),
        raw_counts=Counter({"LINE": 1}),
        layer_info=[
            {
                "name": "01_base",
                "color": 1,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 1,
                "entity_types": {"LINE": 1},
            }
        ],
        visible_layers={"01_base"},
        enabled_layers={"01_base"},
    )

    view.load_document(document)

    assert view.focus_banner.text() == "Wheel to zoom | Drag empty space to pan"
    assert view.transformationAnchor() == QGraphicsView.ViewportAnchor.AnchorUnderMouse
    assert view.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert view.scene().sceneRect().width() > 1000.0
    assert view.scene().sceneRect().height() > 1000.0

    view.deleteLater()
