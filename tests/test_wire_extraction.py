from __future__ import annotations

import math

from core.export import WireOrderingConfig, extract_wire_geometries, order_wire_geometries


def test_extract_wire_geometries_filters_to_wire_layers_and_assigns_ids():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (0.0, 1.0), "end": (10.0, 1.0), "layer": "MECH"},
    ]
    layer_info = [
        {"name": "06_wire", "mapped_type": None, "suggested_role": "wire"},
        {"name": "MECH", "mapped_type": None, "suggested_role": None},
    ]

    wires = extract_wire_geometries(raw_entities, layer_info)

    assert len(wires) == 1
    wire = wires[0]
    assert wire.wire_id == "W0001"
    assert wire.layer_name == "06_wire"
    assert wire.first_point.point_id == "W0001-P1"
    assert wire.second_point.point_id == "W0001-P2"
    assert wire.first_point.x == 0.0
    assert wire.second_point.x == 10.0
    assert math.isclose(wire.length, 10.0)
    assert math.isclose(wire.angle_deg, 0.0)
    assert wire.bbox == (0.0, 0.0, 10.0, 0.0)


def test_extract_wire_geometries_supports_open_polylines_and_arcs():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)],
            "closed": False,
            "layer": "06_wire",
        },
        {
            "type": "ARC",
            "center": (5.0, 5.0),
            "radius": 2.0,
            "start_angle": 0.0,
            "end_angle": 90.0,
            "points": [(7.0, 5.0), (6.0, 6.0), (5.0, 7.0)],
            "layer": "06_wire",
        },
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires = extract_wire_geometries(raw_entities, layer_info)

    assert [wire.source_type for wire in wires] == ["LWPOLYLINE", "ARC"]
    assert wires[0].route_points == ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0))
    assert wires[1].first_point.x == 7.0
    assert wires[1].second_point.y == 7.0


def test_order_wire_geometries_assigns_wire_and_point_sequences():
    raw_entities = [
        {"type": "LINE", "start": (20.0, 5.0), "end": (30.0, 5.0), "layer": "06_wire"},
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires = extract_wire_geometries(raw_entities, layer_info)
    ordered = order_wire_geometries(wires, WireOrderingConfig(primary_axis="x", start_role="first"))

    assert [record.wire_id for record in ordered] == ["W0002", "W0001"]
    assert [record.wire_seq for record in ordered] == [1, 2]
    assert ordered[0].first_point_seq == 1
    assert ordered[0].second_point_seq == 2
    assert ordered[1].first_point_seq == 3
    assert ordered[1].second_point_seq == 4
