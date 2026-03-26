"""Pipeline payload tests."""

from __future__ import annotations

import ezdxf

from core import prepare_document


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
        "elements",
        "converted_counts",
        "coordinates",
        "drc_report",
        "assembly",
        "used_fallback",
        "note",
    }
    assert payload["raw_counts"]["LINE"] == 1
    assert payload["drc_report"]["passed"] in {True, False}
