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
