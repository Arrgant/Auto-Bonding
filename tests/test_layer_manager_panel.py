from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from services import ProjectDocument
from ui.widgets.layer_manager import LayerManagerPanel


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_layer_manager_marks_wire_layers_as_non_editable():
    _app()
    panel = LayerManagerPanel()
    document = ProjectDocument(
        path=Path("layers.dxf"),
        size_bytes=0,
        raw_entities=[],
        scene_rect=(0.0, 0.0, 10.0, 10.0),
        raw_counts=Counter(),
        layer_info=[
            {
                "name": "04_pad",
                "color": 1,
                "linetype": "CONTINUOUS",
                "is_off": False,
                "is_frozen": False,
                "is_locked": False,
                "is_visible": True,
                "plot": True,
                "mapped_type": "die_pad",
                "suggested_role": "pad",
                "enabled": True,
                "entity_count": 4,
                "entity_types": {"LWPOLYLINE": 4},
            },
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
                "enabled": True,
                "entity_count": 20,
                "entity_types": {"LWPOLYLINE": 20},
            },
        ],
        visible_layers={"04_pad", "06_wire"},
        layer_colors={"04_pad": "#FFD24D", "06_wire": "#F26AA0"},
    )

    panel.load_document(document)

    pad_item = panel.tree.topLevelItem(0)
    wire_item = panel.tree.topLevelItem(1)
    pad_row = panel.tree.itemWidget(pad_item, 0)
    wire_row = panel.tree.itemWidget(wire_item, 0)

    assert pad_row.thickness_label.text() == "Set"
    assert wire_row.thickness_label.text() == "N/A"
    assert "does not participate in stacked 3D preview" in wire_row.toolTip()

    panel.deleteLater()
