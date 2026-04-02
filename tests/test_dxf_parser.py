"""DXF parser unit tests."""

from __future__ import annotations

import ezdxf

from core import DXFParser


def test_parse_file_filters_unknown_layers(tmp_path):
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_line((0, 0), (1, 0), dxfattribs={"layer": "WIRE"})
    modelspace.add_circle((2, 2), 0.5, dxfattribs={"layer": "PAD"})
    modelspace.add_line((5, 5), (6, 6), dxfattribs={"layer": "IGNORE"})

    file_path = tmp_path / "parser_layers.dxf"
    document.saveas(file_path)

    parser = DXFParser()
    elements = parser.parse_file(str(file_path))

    assert len(elements) == 2
    assert [element.element_type for element in elements] == ["wire", "die_pad"]


def test_expand_polyline_points_samples_bulge_segments():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    polyline = modelspace.add_lwpolyline([(0, 0, 1.0), (1, 0, 0.0)], format="xyb", dxfattribs={"layer": "WIRE"})

    parser = DXFParser()
    points = parser._expand_polyline_points(polyline)

    assert len(points) > 2
    assert points[0] == [0.0, 0.0, 0.0]
    assert points[-1] == [1.0, 0.0, 0.0]


def test_parse_point_preserves_xyz(tmp_path):
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_point((1.5, 2.5, 3.5), dxfattribs={"layer": "BOND"})

    file_path = tmp_path / "parser_point.dxf"
    document.saveas(file_path)

    parser = DXFParser()
    elements = parser.parse_file(str(file_path))

    assert len(elements) == 1
    assert elements[0].geometry == {"x": 1.5, "y": 2.5, "z": 3.5}


def test_parse_document_respects_enabled_layers_and_manual_mapping():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_circle((2, 2), 0.5, dxfattribs={"layer": "1_CUSTOM"})
    modelspace.add_line((0, 0), (5, 0), dxfattribs={"layer": "2_SKIP"})

    parser = DXFParser(layer_mapping={"1_CUSTOM": "die_pad"}, enabled_layers={"1_CUSTOM"})
    elements = parser.parse_document(document)

    assert len(elements) == 1
    assert elements[0].element_type == "die_pad"
    assert elements[0].layer == "1_CUSTOM"


def test_parse_document_supports_recommended_rule_table_layer_names():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0, 0), (10, 0), (10, 6), (0, 6)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_circle((1.5, 1.5), 0.4, dxfattribs={"layer": "01_substrate"})
    modelspace.add_lwpolyline(
        [(0, 0), (2, 0), (2, 1), (0, 1)],
        close=True,
        dxfattribs={"layer": "04_pad"},
    )
    modelspace.add_line((0, 0), (5, 0), dxfattribs={"layer": "06_wire"})

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert [element.element_type for element in elements] == ["substrate", "hole", "die_pad", "wire"]
    assert elements[1].properties["cut"] is True


def test_parse_document_recognizes_circle_like_substrate_polyline_as_hole():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0, 0), (20, 0), (20, 12), (0, 12)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_lwpolyline(
        [(1.1, 1.5, 0.4142), (1.5, 1.9, 0.4142), (1.9, 1.5, 0.4142), (1.5, 1.1, 0.4142)],
        format="xyb",
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert [element.element_type for element in elements] == ["substrate", "hole"]
    assert elements[1].properties["cut"] is True


def test_parse_document_recognizes_internal_circle_on_non_substrate_layer_as_hole():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0, 0), (20, 0), (20, 12), (0, 12)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_circle((2.0, 2.0), 0.5, dxfattribs={"layer": "MECH"})

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert [element.element_type for element in elements] == ["substrate", "hole"]
    assert elements[1].layer == "MECH"
    assert elements[1].properties["cut"] is True


def test_parse_document_recognizes_lead_frame_layer_circle_as_hole_inside_substrate():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0, 0), (24, 0), (24, 14), (0, 14)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_circle((2.0, 2.0), 0.6, dxfattribs={"layer": "03_lead_frame"})

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert [element.element_type for element in elements] == ["substrate", "hole"]
    assert elements[1].layer == "03_lead_frame"
    assert elements[1].properties["cut"] is True


def test_parse_document_maps_real_world_chip_layer_alias_to_die_pad():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(4, 4), (8, 4), (8, 7), (4, 7)],
        close=True,
        dxfattribs={"layer": "05_chip"},
    )

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert len(elements) == 1
    assert elements[0].element_type == "die_pad"
    assert elements[0].layer == "05_chip"


def test_parse_document_recognizes_repeated_internal_cross_layer_rounds_as_holes():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0, 0), (100, 0), (100, 60), (0, 60)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_circle((32.0, 30.0), 5.0, dxfattribs={"layer": "03_lead_frame"})
    modelspace.add_circle((68.0, 30.0), 5.0, dxfattribs={"layer": "03_lead_frame"})

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert [element.element_type for element in elements] == ["substrate", "hole", "hole"]
    assert all(element.properties.get("cut") is True for element in elements[1:])


def test_parse_document_keeps_concentric_cross_layer_rounds_as_round_features():
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0, 0), (80, 0), (80, 50), (0, 50)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_circle((18.0, 18.0), 2.0, dxfattribs={"layer": "03_lead_frame"})
    modelspace.add_circle((18.0, 18.0), 4.0, dxfattribs={"layer": "03_lead_frame"})

    parser = DXFParser()
    elements = parser.parse_document(document)

    assert [element.element_type for element in elements] == ["substrate", "round_feature", "round_feature"]
