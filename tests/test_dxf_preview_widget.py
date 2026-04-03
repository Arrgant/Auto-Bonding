"""DXF preview widget tests."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtWidgets import QGraphicsSimpleTextItem

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


def test_dxf_preview_renders_text_entities():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_text.dxf"),
        size_bytes=0,
        raw_entities=[
            {
                "type": "TEXT",
                "text": "PAD-A1",
                "insert": (10.0, 20.0),
                "height": 2.5,
                "rotation": 0.0,
                "box_width": 9.3,
                "layer": "05_note",
            },
            {
                "type": "MTEXT",
                "text": "TOP\nBOTTOM",
                "insert": (30.0, 40.0),
                "height": 3.0,
                "rotation": 15.0,
                "box_width": 14.0,
                "layer": "05_note",
            },
        ],
        scene_rect=(0.0, -60.0, 80.0, 80.0),
        raw_counts=Counter({"TEXT": 1, "MTEXT": 1}),
        layer_info=[
            {
                "name": "05_note",
                "color": 2,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 2,
                "entity_types": {"MTEXT": 1, "TEXT": 1},
            },
        ],
        visible_layers={"05_note"},
        enabled_layers={"05_note"},
    )

    view.load_document(document)

    text_items = [
        item
        for item in view.scene().items()
        if isinstance(item, QGraphicsSimpleTextItem) and item.data(SOURCE_INDICES_ROLE) is not None
    ]
    assert {item.text() for item in text_items} == {"PAD-A1", "TOP\nBOTTOM"}
    assert all(item.brush().style() != Qt.BrushStyle.NoBrush for item in text_items)

    view.deleteLater()


def test_dxf_preview_applies_layer_linetype_to_lines():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_linetype.dxf"),
        size_bytes=0,
        raw_entities=[
            {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "02_dash"},
        ],
        scene_rect=(0.0, -1.0, 10.0, 2.0),
        raw_counts=Counter({"LINE": 1}),
        layer_info=[
            {
                "name": "02_dash",
                "color": 3,
                "linetype": "DASHED",
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
        visible_layers={"02_dash"},
        enabled_layers={"02_dash"},
    )

    view.load_document(document)

    line_item = next(item for item in view.scene().items() if item.data(SOURCE_INDICES_ROLE) is not None)
    assert line_item.pen().style() == Qt.PenStyle.DashLine

    view.deleteLater()


def test_dxf_preview_renders_hatch_entities():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_hatch.dxf"),
        size_bytes=0,
        raw_entities=[
            {
                "type": "HATCH",
                "paths": [[(0.0, 0.0), (8.0, 0.0), (8.0, 4.0), (0.0, 4.0)]],
                "solid_fill": True,
                "layer": "04_pad",
            }
        ],
        scene_rect=(0.0, -8.0, 16.0, 12.0),
        raw_counts=Counter({"HATCH": 1}),
        layer_info=[
            {
                "name": "04_pad",
                "color": 2,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": "die_pad",
                "entity_count": 1,
                "entity_types": {"HATCH": 1},
            },
        ],
        visible_layers={"04_pad"},
        enabled_layers={"04_pad"},
    )

    view.load_document(document)

    hatch_items = [
        item
        for item in view.scene().items()
        if isinstance(item, QGraphicsPathItem) and item.data(SOURCE_INDICES_ROLE) is not None
    ]
    assert len(hatch_items) == 1
    assert hatch_items[0].brush().style() != Qt.BrushStyle.NoBrush

    view.deleteLater()


def test_dxf_preview_renders_insert_children():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_insert.dxf"),
        size_bytes=0,
        raw_entities=[
            {
                "type": "INSERT",
                "name": "MARKER",
                "insert": (10.0, 20.0),
                "rotation": 0.0,
                "xscale": 1.0,
                "yscale": 1.0,
                "entities": [
                    {
                        "type": "ELLIPSE",
                        "points": [(8.0, 20.0), (10.0, 21.5), (12.0, 20.0), (10.0, 18.5)],
                        "closed": True,
                        "layer": "07_mark",
                    },
                    {
                        "type": "TEXT",
                        "text": "PIN",
                        "insert": (13.0, 20.0),
                        "height": 1.2,
                        "rotation": 0.0,
                        "box_width": 2.2,
                        "layer": "07_mark",
                    },
                ],
                "layer": "07_mark",
            }
        ],
        scene_rect=(0.0, -30.0, 40.0, 40.0),
        raw_counts=Counter({"INSERT": 1}),
        layer_info=[
            {
                "name": "07_mark",
                "color": 4,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 1,
                "entity_types": {"INSERT": 1},
            },
        ],
        visible_layers={"07_mark"},
        enabled_layers={"07_mark"},
    )

    view.load_document(document)

    indexed_items = [
        item
        for item in view.scene().items()
        if item.data(SOURCE_INDICES_ROLE) is not None
    ]
    assert len(indexed_items) == 2
    assert all(item.data(SOURCE_INDICES_ROLE) == (0,) for item in indexed_items)
    assert any(isinstance(item, QGraphicsPathItem) for item in indexed_items)
    assert any(isinstance(item, QGraphicsSimpleTextItem) and item.text() == "PIN" for item in indexed_items)

    view.deleteLater()


def test_dxf_preview_renders_solid_and_insert_attributes():
    _app()
    view = DXFPreviewView()

    document = ProjectDocument(
        path=Path("preview_solid_attr.dxf"),
        size_bytes=0,
        raw_entities=[
            {
                "type": "SOLID",
                "points": [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)],
                "layer": "08_shape",
            },
            {
                "type": "INSERT",
                "name": "TAGBLOCK",
                "insert": (20.0, 30.0),
                "rotation": 0.0,
                "xscale": 1.0,
                "yscale": 1.0,
                "entities": [
                    {
                        "type": "ATTRIB",
                        "text": "B2",
                        "insert": (20.0, 30.0),
                        "height": 2.0,
                        "rotation": 0.0,
                        "box_width": 2.0,
                        "layer": "09_label",
                    },
                ],
                "layer": "09_label",
            },
        ],
        scene_rect=(0.0, -40.0, 60.0, 50.0),
        raw_counts=Counter({"SOLID": 1, "INSERT": 1}),
        layer_info=[
            {
                "name": "08_shape",
                "color": 5,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 1,
                "entity_types": {"SOLID": 1},
            },
            {
                "name": "09_label",
                "color": 6,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": None,
                "entity_count": 1,
                "entity_types": {"INSERT": 1},
            },
        ],
        visible_layers={"08_shape", "09_label"},
        enabled_layers={"08_shape", "09_label"},
    )

    view.load_document(document)

    indexed_items = [
        item
        for item in view.scene().items()
        if item.data(SOURCE_INDICES_ROLE) is not None
    ]
    assert any(
        isinstance(item, QGraphicsPathItem)
        and item.data(SOURCE_INDICES_ROLE) == (0,)
        and item.brush().style() != Qt.BrushStyle.NoBrush
        for item in indexed_items
    )
    assert any(
        isinstance(item, QGraphicsSimpleTextItem)
        and item.data(SOURCE_INDICES_ROLE) == (1,)
        and item.text() == "B2"
        for item in indexed_items
    )

    view.deleteLater()
