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


def test_load_raw_dxf_entities_extracts_text_and_mtext(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("05_NOTE", color=2)

    msp = doc.modelspace()
    text = msp.add_text(
        "PAD-A1",
        dxfattribs={"layer": "05_NOTE", "height": 2.5, "rotation": 30.0},
    )
    text.dxf.insert = (10.0, 20.0, 0.0)
    mtext = msp.add_mtext(
        "TOP\\PBOTTOM",
        dxfattribs={"layer": "05_NOTE", "char_height": 3.0, "width": 14.0, "rotation": 15.0},
    )
    mtext.dxf.insert = (40.0, 50.0, 0.0)

    dxf_path = tmp_path / "text_entities.dxf"
    doc.saveas(dxf_path)

    entities, scene_rect, counts, layer_info = load_raw_dxf_entities(dxf_path)

    assert counts["TEXT"] == 1
    assert counts["MTEXT"] == 1
    assert scene_rect[2] > 30.0
    assert scene_rect[3] > 30.0

    text_entity = next(entity for entity in entities if entity["type"] == "TEXT")
    mtext_entity = next(entity for entity in entities if entity["type"] == "MTEXT")
    note_layer = next(layer for layer in layer_info if layer["name"] == "05_NOTE")

    assert text_entity["text"] == "PAD-A1"
    assert text_entity["insert"] == (10.0, 20.0)
    assert text_entity["height"] == 2.5
    assert text_entity["rotation"] == 30.0

    assert mtext_entity["text"] == "TOP\nBOTTOM"
    assert mtext_entity["insert"] == (40.0, 50.0)
    assert mtext_entity["height"] == 3.0
    assert mtext_entity["rotation"] == 15.0
    assert note_layer["entity_types"] == {"MTEXT": 1, "TEXT": 1}


def test_load_raw_dxf_entities_extracts_hatch_polyline_paths(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("04_COPPER", color=2)

    msp = doc.modelspace()
    hatch = msp.add_hatch(color=2, dxfattribs={"layer": "04_COPPER"})
    hatch.paths.add_polyline_path(
        [
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 0.0),
            (10.0, 6.0, 0.0),
            (0.0, 6.0, 0.0),
        ],
        is_closed=True,
    )

    dxf_path = tmp_path / "hatch.dxf"
    doc.saveas(dxf_path)

    entities, scene_rect, counts, layer_info = load_raw_dxf_entities(dxf_path)

    assert counts["HATCH"] == 1
    assert scene_rect[2] > 0
    assert scene_rect[3] > 0

    hatch_entity = next(entity for entity in entities if entity["type"] == "HATCH")
    copper_layer = next(layer for layer in layer_info if layer["name"] == "04_COPPER")

    assert hatch_entity["solid_fill"] is True
    assert len(hatch_entity["paths"]) == 1
    assert hatch_entity["paths"][0][:4] == [
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 6.0),
        (0.0, 6.0),
    ]
    assert copper_layer["entity_types"] == {"HATCH": 1}


def test_load_raw_dxf_entities_extracts_insert_virtual_entities(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("07_MARK", color=4)

    marker_block = doc.blocks.new(name="MARKER")
    marker_block.add_circle((0.0, 0.0), 2.0, dxfattribs={"layer": "0"})
    marker_text = marker_block.add_text("PIN", dxfattribs={"height": 1.2, "layer": "0"})
    marker_text.dxf.insert = (3.0, 0.0, 0.0)

    msp = doc.modelspace()
    msp.add_blockref(
        "MARKER",
        (10.0, 20.0),
        dxfattribs={"layer": "07_MARK", "rotation": 30.0, "xscale": 2.0, "yscale": 1.5},
    )

    dxf_path = tmp_path / "insert_block.dxf"
    doc.saveas(dxf_path)

    entities, scene_rect, counts, layer_info = load_raw_dxf_entities(dxf_path)

    assert counts["INSERT"] == 1
    assert scene_rect[2] > 0
    assert scene_rect[3] > 0

    insert_entity = next(entity for entity in entities if entity["type"] == "INSERT")
    mark_layer = next(layer for layer in layer_info if layer["name"] == "07_MARK")
    child_types = {entity["type"] for entity in insert_entity["entities"]}

    assert insert_entity["name"] == "MARKER"
    assert insert_entity["insert"] == (10.0, 20.0)
    assert insert_entity["rotation"] == 30.0
    assert child_types == {"ELLIPSE", "TEXT"}
    assert all(entity["layer"] == "07_MARK" for entity in insert_entity["entities"])
    assert mark_layer["entity_types"] == {"INSERT": 1}


def test_load_raw_dxf_entities_extracts_solid_and_insert_attributes(tmp_path):
    doc = ezdxf.new()
    doc.layers.add("08_SHAPE", color=5)
    doc.layers.add("09_LABEL", color=6)

    tag_block = doc.blocks.new(name="TAGBLOCK")
    tag_block.add_attdef(
        "PAD_ID",
        (1.0, 2.0),
        "A1",
        height=1.8,
        rotation=25.0,
        dxfattribs={"layer": "0"},
    )

    msp = doc.modelspace()
    msp.add_solid(
        [(0.0, 0.0), (10.0, 0.0), (0.0, 6.0), (10.0, 6.0)],
        dxfattribs={"layer": "08_SHAPE"},
    )
    insert = msp.add_blockref("TAGBLOCK", (20.0, 30.0), dxfattribs={"layer": "09_LABEL"})
    insert.add_attrib(
        "PAD_ID",
        "B2",
        insert=(20.0, 30.0),
        dxfattribs={"height": 2.0, "rotation": 15.0, "layer": "09_LABEL"},
    )

    dxf_path = tmp_path / "solid_and_attrib.dxf"
    doc.saveas(dxf_path)

    entities, _, counts, _ = load_raw_dxf_entities(dxf_path)

    assert counts["SOLID"] == 1
    assert counts["INSERT"] == 1

    solid_entity = next(entity for entity in entities if entity["type"] == "SOLID")
    insert_entity = next(entity for entity in entities if entity["type"] == "INSERT")
    attrib_entity = next(entity for entity in insert_entity["entities"] if entity["type"] == "ATTRIB")

    assert solid_entity["points"] == [
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 6.0),
        (0.0, 6.0),
    ]
    assert attrib_entity["text"] == "B2"
    assert attrib_entity["insert"] == (20.0, 30.0)
    assert attrib_entity["height"] == 2.0
    assert attrib_entity["layer"] == "09_LABEL"


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
