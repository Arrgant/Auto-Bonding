from __future__ import annotations

import math

from core.export import (
    WireOrderingConfig,
    build_wire_merge_proposals,
    extract_wire_geometries,
    extract_wire_geometries_with_audit,
    format_wire_extraction_audit_report,
    order_wire_geometries,
    write_wire_extraction_audit_report,
)


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
    assert wire.first_point.z is None
    assert wire.second_point.z is None
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


def test_order_wire_geometries_can_cluster_group_numbers_from_geometry():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (0.0, 10.0), "end": (10.0, 10.0), "layer": "06_wire"},
        {"type": "LINE", "start": (100.0, 0.0), "end": (110.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (100.0, 10.0), "end": (110.0, 10.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires = extract_wire_geometries(raw_entities, layer_info)
    ordered = order_wire_geometries(
        wires,
        WireOrderingConfig(primary_axis="x", group_mode="clustered", group_no=5),
    )

    assert [record.wire_id for record in ordered] == ["W0001", "W0002", "W0003", "W0004"]
    assert [record.group_no for record in ordered] == [5, 5, 6, 6]
    assert [record.wire_seq for record in ordered] == [1, 2, 3, 4]


def test_extract_wire_geometries_with_audit_reports_skipped_wire_layer_entities():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (1.0, 0.0), (0.0, 0.0)],
            "closed": True,
            "layer": "06_wire",
        },
        {"type": "POINT", "location": (2.0, 2.0), "layer": "06_wire"},
        {"type": "LINE", "start": (5.0, 5.0), "end": (5.0, 5.0), "layer": "06_wire"},
        {"type": "LINE", "start": (0.0, 1.0), "end": (10.0, 1.0), "layer": "MECH"},
    ]
    layer_info = [
        {"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"},
        {"name": "MECH", "mapped_type": None, "suggested_role": None},
    ]

    wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert [wire.wire_id for wire in wires] == ["W0001"]
    assert audit.wire_layers == ("06_wire",)
    assert audit.candidate_entity_count == 4
    assert audit.extracted_wire_count == 1
    assert audit.extracted_counts_by_type == {"LINE": 1}
    assert audit.skipped_counts_by_reason == {
        "closed_lwpolyline": 1,
        "unsupported_entity_type": 1,
        "zero_length_or_insufficient_points": 1,
    }
    assert [
        (item.entity_index, item.entity_type, item.reason)
        for item in audit.skipped_entities
    ] == [
        (1, "LWPOLYLINE", "closed_lwpolyline"),
        (2, "POINT", "unsupported_entity_type"),
        (3, "LINE", "zero_length_or_insufficient_points"),
    ]


def test_extract_wire_geometries_with_audit_reports_two_segment_merge_candidates():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (10.0, 0.0), "end": (20.0, 5.0), "layer": "06_wire"},
        {"type": "LINE", "start": (100.0, 0.0), "end": (110.0, 0.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert [wire.wire_id for wire in wires] == ["W0001", "W0002", "W0003"]
    assert [
        (
            item.first_wire_id,
            item.second_wire_id,
            item.shared_x,
            item.shared_y,
            item.first_endpoint_role,
            item.second_endpoint_role,
            item.endpoint_alignment,
        )
        for item in audit.merge_candidates
    ] == [
        ("W0001", "W0002", 10.0, 0.0, "second", "first", "continuous"),
    ]


def test_extract_wire_geometries_with_audit_ignores_branch_junctions_as_merge_candidates():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (10.0, 0.0), "end": (20.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (10.0, 0.0), "end": (10.0, 10.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    _wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert audit.merge_candidates == ()


def test_extract_wire_geometries_with_audit_flags_same_role_merge_direction_conflicts():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (20.0, 5.0), "end": (10.0, 0.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    _wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert [
        (
            item.first_wire_id,
            item.second_wire_id,
            item.first_endpoint_role,
            item.second_endpoint_role,
            item.endpoint_alignment,
        )
        for item in audit.merge_candidates
    ] == [
        ("W0001", "W0002", "second", "second", "same_role_conflict"),
    ]


def test_build_wire_merge_proposals_suggests_join_order_and_fragment_reversal():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (20.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (30.0, 0.0), "end": (40.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (40.0, 0.0), "end": (50.0, 0.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    _wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert [
        (
            proposal.source_wire_id,
            proposal.target_wire_id,
            proposal.action,
            proposal.reverse_wire_ids,
            proposal.source_endpoint_role,
            proposal.target_endpoint_role,
        )
        for proposal in build_wire_merge_proposals(audit)
    ] == [
        (
            "W0001",
            "W0002",
            "reverse_second_then_join",
            ("W0002",),
            "second",
            "second",
        ),
        ("W0003", "W0004", "join_as_is", (), "second", "first"),
    ]


def test_format_wire_extraction_audit_report_lists_skips_and_conflicts_first():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "POINT", "location": (5.0, 5.0), "layer": "06_wire"},
        {"type": "LINE", "start": (20.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (100.0, 0.0), "end": (110.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (110.0, 0.0), "end": (120.0, 0.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    _wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert format_wire_extraction_audit_report(audit) == (
        "Wire Extraction Audit\n"
        "Wire layers: 06_wire\n"
        "Converted entities: 4/5\n"
        "\n"
        "Extracted entity types:\n"
        "- LINE: 4\n"
        "\n"
        "Skipped entities:\n"
        "- unsupported_entity_type: 1\n"
        "  - #1 layer=06_wire type=POINT reason=unsupported_entity_type\n"
        "\n"
        "Potential split-wire joins:\n"
        "- W0001(second) <-> W0003(second) @ (10.000000, 0.000000) [same_role_conflict]\n"
        "- W0004(second) <-> W0005(first) @ (110.000000, 0.000000) [continuous]\n"
        "\n"
        "Suggested merge actions:\n"
        "- W0001 -> W0003 @ (10.000000, 0.000000) action=reverse_second_then_join reverse=W0003\n"
        "- W0004 -> W0005 @ (110.000000, 0.000000) action=join_as_is reverse=none\n"
    )


def test_write_wire_extraction_audit_report_writes_report_text(tmp_path):
    _wires, audit = extract_wire_geometries_with_audit(
        [
            {"type": "LINE", "start": (0.0, 0.0), "end": (1.0, 0.0), "layer": "06_wire"},
            {"type": "POINT", "location": (2.0, 2.0), "layer": "06_wire"},
        ],
        [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}],
    )

    output_path = write_wire_extraction_audit_report(audit, tmp_path / "audit" / "wire.txt")

    assert output_path == tmp_path / "audit" / "wire.txt"
    assert output_path.read_text(encoding="utf-8") == format_wire_extraction_audit_report(audit)
