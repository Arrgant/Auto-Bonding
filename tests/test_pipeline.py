"""Pipeline payload tests."""

from __future__ import annotations

import ezdxf

from core import BondingElement, load_import_preview, prepare_document, prepare_document_from_preview
from core.pipeline import group_elements_by_layer


def test_prepare_document_returns_complete_payload(tmp_path):
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_line((0, 0), (5, 0), dxfattribs={"layer": "WIRE"})

    file_path = tmp_path / "payload.dxf"
    document.saveas(file_path)

    payload = prepare_document(
        file_path,
        {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
        },
    )

    assert set(payload.keys()) == {
        "raw_entities",
        "scene_rect",
        "raw_counts",
        "layer_info",
        "parser_elements",
        "semantic_result",
        "elements",
        "converted_counts",
        "coordinates",
        "wire_geometries",
        "drc_report",
        "assembly",
        "used_fallback",
        "note",
    }
    assert payload["raw_counts"]["LINE"] == 1
    assert len(payload["wire_geometries"]) == 1
    assert payload["drc_report"]["passed"] in {True, False}


def test_preview_stage_can_be_promoted_to_prepared_document(tmp_path):
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_line((0, 0), (5, 0), dxfattribs={"layer": "WIRE"})

    file_path = tmp_path / "staged_payload.dxf"
    document.saveas(file_path)

    preview = load_import_preview(file_path)
    payload = prepare_document_from_preview(
        preview,
        {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
        },
    )

    assert preview["raw_counts"]["LINE"] == 1
    assert payload["raw_counts"]["LINE"] == 1
    assert payload["raw_entities"] == preview["raw_entities"]
    assert payload["scene_rect"] == preview["scene_rect"]
    assert payload["semantic_result"] == preview["semantic_result"]
    assert payload["wire_geometries"] == preview["wire_geometries"]


def test_prepare_document_from_preview_can_defer_drc_report(tmp_path):
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_line((0, 0), (5, 0), dxfattribs={"layer": "WIRE"})

    file_path = tmp_path / "deferred_drc_payload.dxf"
    document.saveas(file_path)

    preview = load_import_preview(file_path)
    payload = prepare_document_from_preview(
        preview,
        {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
            "defer_drc_report": True,
        },
    )

    assert payload["drc_report"]["passed"] is True
    assert payload["drc_report"]["total_violations"] == 0
    assert "Deferred detailed DRC during import for faster loading." in payload["note"]


def test_group_elements_by_layer_uses_numeric_first_sort():
    elements = [
        BondingElement("wire", "10_ROUTE", {}, {}),
        BondingElement("wire", "2_METAL", {}, {}),
        BondingElement("die_pad", "2_METAL", {}, {}),
        BondingElement("lead_frame", "PADS", {}, {}),
        BondingElement("wire", "1_BASE", {}, {}),
    ]

    grouped = group_elements_by_layer(elements)

    assert [layer_name for layer_name, _ in grouped] == ["1_BASE", "2_METAL", "10_ROUTE", "PADS"]
    assert len(grouped[1][1]) == 2
