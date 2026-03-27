from __future__ import annotations

import math

import ezdxf

from core.raw_dxf import extract_coordinates_from_raw_entities, load_raw_dxf_entities


def test_load_raw_dxf_entities_collects_layers_and_counts(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("SIGNAL", color=1)
    doc.layers.add("MECH", color=3)

    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "SIGNAL"})
    msp.add_circle((5, 5), 2, dxfattribs={"layer": "MECH"})

    dxf_path = tmp_path / "layers.dxf"
    doc.saveas(dxf_path)

    entities, scene_rect, counts, layer_info = load_raw_dxf_entities(dxf_path, {"SIGNAL": "wire"})

    assert len(entities) == 2
    assert counts["LINE"] == 1
    assert counts["CIRCLE"] == 1
    assert scene_rect[2] > 0
    assert scene_rect[3] > 0

    signal_layer = next(layer for layer in layer_info if layer["name"] == "SIGNAL")
    mech_layer = next(layer for layer in layer_info if layer["name"] == "MECH")

    assert signal_layer["mapped_type"] == "wire"
    assert signal_layer["entity_count"] == 1
    assert signal_layer["entity_types"] == {"LINE": 1}
    assert mech_layer["entity_types"] == {"CIRCLE": 1}


def test_load_raw_dxf_entities_expands_bulge_polyline(tmp_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0.0, 0.0, 1.0), (10.0, 0.0, 0.0)],
        format="xyb",
        dxfattribs={"layer": "ARC_PATH"},
    )

    dxf_path = tmp_path / "bulge.dxf"
    doc.saveas(dxf_path)

    entities, _, counts, _ = load_raw_dxf_entities(dxf_path)

    assert counts["LWPOLYLINE"] == 1
    assert len(entities) == 1
    assert entities[0]["type"] == "LWPOLYLINE"
    assert len(entities[0]["points"]) > 2


def test_load_raw_dxf_entities_can_filter_enabled_layers(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("1_SIGNAL", color=1)
    doc.layers.add("2_MECH", color=3)

    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "1_SIGNAL"})
    msp.add_circle((5, 5), 2, dxfattribs={"layer": "2_MECH"})

    dxf_path = tmp_path / "filtered_layers.dxf"
    doc.saveas(dxf_path)

    entities, _, counts, layer_info = load_raw_dxf_entities(
        dxf_path,
        {"1_SIGNAL": "wire"},
        enabled_layers={"1_SIGNAL"},
    )

    assert len(entities) == 1
    assert counts["LINE"] == 1
    assert counts["CIRCLE"] == 0
    signal_layer = next(layer for layer in layer_info if layer["name"] == "1_SIGNAL")
    mech_layer = next(layer for layer in layer_info if layer["name"] == "2_MECH")
    assert signal_layer["enabled"] is True
    assert mech_layer["enabled"] is False


def test_load_raw_dxf_entities_suggests_semantic_roles(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("01_substrate", color=7)
    doc.layers.add("06_wire", color=1)

    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (10, 0), (10, 6), (0, 6)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    msp.add_line((1, 1), (9, 5), dxfattribs={"layer": "06_wire"})

    dxf_path = tmp_path / "semantic_layers.dxf"
    doc.saveas(dxf_path)

    _, _, _, layer_info = load_raw_dxf_entities(dxf_path)

    substrate_layer = next(layer for layer in layer_info if layer["name"] == "01_substrate")
    wire_layer = next(layer for layer in layer_info if layer["name"] == "06_wire")

    assert substrate_layer["suggested_role"] == "substrate"
    assert wire_layer["suggested_role"] == "wire"


def test_extract_coordinates_from_raw_entities_deduplicates_points():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (1.0, 0.0)},
        {"type": "LWPOLYLINE", "points": [(1.0, 0.0), (2.0, 0.0)], "closed": False},
        {"type": "CIRCLE", "center": (2.0, 0.0), "radius": 0.5},
        {"type": "POINT", "location": (0.0, 0.0)},
    ]

    points = extract_coordinates_from_raw_entities(raw_entities)

    assert len(points) == 3
    assert {(point.x, point.y, point.z) for point in points} == {
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (2.0, 0.0, 0.0),
    }
