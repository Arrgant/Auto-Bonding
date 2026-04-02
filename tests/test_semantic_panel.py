"""Semantic sidebar widget tests."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.semantic import RelationNote, SemanticCandidate, SemanticClassificationResult, SemanticEntity
from services import ProjectDocument
from ui.widgets.semantic_panel import SemanticObjectsPanel


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_semantic_panel_groups_objects_and_review_items():
    _app()
    panel = SemanticObjectsPanel()
    document = ProjectDocument(
        path=Path("semantic.dxf"),
        size_bytes=0,
        raw_entities=[],
        scene_rect=(0.0, 0.0, 10.0, 10.0),
        raw_counts=Counter(),
        semantic_result=SemanticClassificationResult(
            candidates=[],
            entities=[
                SemanticEntity(
                    id="pad_1",
                    kind="pad",
                    layer_name="04_pad",
                    confidence=0.92,
                    source_indices=(3,),
                    properties={"pad_kind": "small"},
                ),
                SemanticEntity(
                    id="wire_1",
                    kind="wire",
                    layer_name="06_wire",
                    confidence=0.88,
                    source_indices=(7,),
                ),
            ],
            review=[
                SemanticCandidate(
                    id="substrate_candidate_1",
                    kind="substrate_candidate",
                    layer_name="01_substrate",
                    confidence=0.72,
                    source_indices=(1,),
                )
            ],
            relation_notes=[RelationNote("pad_candidate_1", "module-region", "pad_inside_module", 0.08)],
        ),
        selected_semantic_key="entity:pad_1",
    )

    panel.load_document(document)

    assert panel.tabs.tabText(0) == "Objects (2)"
    assert panel.tabs.tabText(1) == "Confirm (1)"
    assert panel.object_tree.topLevelItemCount() == 2
    assert panel.review_tree.topLevelItemCount() == 1
    assert panel.object_tree.currentItem().text(0).startswith("Pad")
    assert "2 objects recognized" in panel.summary.text()
    assert panel.object_tree.columnCount() == 2

    panel.deleteLater()


def test_semantic_panel_displays_hole_kind_details():
    _app()
    panel = SemanticObjectsPanel()
    document = ProjectDocument(
        path=Path("semantic_hole.dxf"),
        size_bytes=0,
        raw_entities=[],
        scene_rect=(0.0, 0.0, 10.0, 10.0),
        raw_counts=Counter(),
        semantic_result=SemanticClassificationResult(
            candidates=[],
            entities=[
                SemanticEntity(
                    id="hole_1",
                    kind="hole",
                    layer_name="01_substrate",
                    confidence=0.91,
                    source_indices=(1,),
                    properties={"hole_kind": "mounting"},
                )
            ],
            review=[],
            relation_notes=[],
        ),
        selected_semantic_key="entity:hole_1",
    )

    panel.load_document(document)

    assert panel.object_tree.currentItem().text(0) == "Hole (mounting)"

    panel.deleteLater()


def test_semantic_panel_emits_review_override_request_on_double_click():
    _app()
    panel = SemanticObjectsPanel()
    payloads: list[object] = []
    panel.review_override_requested.connect(payloads.append)

    document = ProjectDocument(
        path=Path("semantic.dxf"),
        size_bytes=0,
        raw_entities=[],
        scene_rect=(0.0, 0.0, 10.0, 10.0),
        raw_counts=Counter(),
        semantic_result=SemanticClassificationResult(
            candidates=[],
            entities=[],
            review=[
                SemanticCandidate(
                    id="wire_candidate_1",
                    kind="wire_candidate",
                    layer_name="06_wire",
                    confidence=0.72,
                    source_indices=(4,),
                )
            ],
            relation_notes=[],
        ),
    )

    panel.load_document(document)
    review_group = panel.review_tree.topLevelItem(0)
    review_item = review_group.child(0)
    panel._handle_review_item_double_clicked(review_item, 0)

    assert isinstance(payloads[0], dict)
    assert payloads[0]["key"] == "review:wire_candidate_1"

    panel.deleteLater()


def test_semantic_panel_emits_manage_presets_request():
    _app()
    panel = SemanticObjectsPanel()
    triggered: list[bool] = []
    panel.preset_manage_requested.connect(lambda: triggered.append(True))

    panel.manage_presets_button.click()

    assert triggered == [True]

    panel.deleteLater()
