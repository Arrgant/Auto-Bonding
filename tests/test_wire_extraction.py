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


def test_extract_wire_geometries_recursively_reads_insert_and_polyline_paths():
    raw_entities = [
        {
            "type": "INSERT",
            "layer": "06_wire",
            "entities": [
                {
                    "type": "POLYLINE",
                    "points": [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)],
                    "closed": False,
                    "layer": "0",
                },
                {
                    "type": "LINE",
                    "start": (5.0, 5.0),
                    "end": (10.0, 5.0),
                    "layer": "0",
                },
            ],
        },
    ]
    layer_info = [
        {
            "name": "06_wire",
            "mapped_type": "wire",
            "suggested_role": "wire",
            "entity_types": {"INSERT": 1, "POLYLINE": 1, "LINE": 1},
        }
    ]

    wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert len(wires) == 1
    assert wires[0].route_points == ((0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (10.0, 5.0))
    assert wires[0].source_type == "MERGED_PATH"
    assert audit.wire_layer_entity_type_counts["INSERT"] == 1
    assert audit.wire_layer_entity_type_counts["POLYLINE"] == 1
    assert audit.wire_layer_entity_type_counts["LINE"] == 1
    assert audit.raw_candidate_wire_count == 2
    assert audit.pre_merge_wire_path_count == 2
    assert audit.extracted_wire_count == 1
    assert audit.final_wire_paths[0].bend_count == 2


def test_extract_wire_geometries_filters_pad_box_diagonals_but_keeps_long_interconnects():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (1.0, 0.0), (1.0, 0.5), (0.0, 0.5)],
            "closed": True,
            "layer": "06_wire",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (1.0, 0.5)],
            "closed": False,
            "layer": "06_wire",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(1.0, 0.0), (10.0, 0.0), (20.0, 5.0)],
            "closed": False,
            "layer": "06_wire",
        },
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert len(wires) == 1
    assert wires[0].route_points == ((1.0, 0.0), (10.0, 0.0), (20.0, 5.0))
    assert audit.raw_candidate_wire_count == 2
    assert audit.pad_filtered_wire_count == 1
    assert audit.pre_merge_wire_path_count == 1
    assert audit.skipped_counts_by_reason["pad_outline"] == 1
    assert audit.skipped_counts_by_reason["pad_internal_short_line"] == 1


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


def test_extract_wire_geometries_with_audit_reports_wire_layer_entity_type_stats():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (1.0, 0.0), "layer": "06_wire"},
        {"type": "INSERT", "entities": [], "layer": "06_wire"},
    ]
    layer_info = [
        {
            "name": "06_wire",
            "mapped_type": "wire",
            "suggested_role": "wire",
            "entity_types": {
                "LINE": 2,
                "LWPOLYLINE": 3,
                "POLYLINE": 4,
                "INSERT": 5,
                "ARC": 6,
                "SPLINE": 7,
            },
        }
    ]

    _wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert audit.wire_layer_entity_type_counts == {
        "LINE": 2,
        "LWPOLYLINE": 3,
        "POLYLINE": 4,
        "INSERT": 5,
        "ARC": 6,
        "SPLINE": 7,
    }


def test_extract_wire_geometries_expands_insert_entities_and_polyline_routes():
    raw_entities = [
        {
            "type": "INSERT",
            "layer": "06_wire",
            "entities": [
                {
                    "type": "POLYLINE",
                    "layer": "0",
                    "points": [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)],
                    "closed": False,
                },
                {
                    "type": "LINE",
                    "layer": "0",
                    "start": (2.0, 2.0),
                    "end": (4.0, 2.0),
                },
            ],
        }
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires = extract_wire_geometries(raw_entities, layer_info)

    assert len(wires) == 1
    assert wires[0].route_points == ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (4.0, 2.0))
    assert wires[0].source_type == "MERGED_PATH"
    assert wires[0].source_entity_indices == (0,)


def test_extract_wire_geometries_filters_pad_symbol_diagonals_inside_small_rectangles():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (1.0, 0.0), (1.0, 0.8), (0.0, 0.8)],
            "closed": True,
            "layer": "06_wire",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (1.0, 0.8)],
            "closed": False,
            "layer": "06_wire",
        },
        {"type": "LINE", "start": (0.5, 0.8), "end": (8.0, 4.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert len(wires) == 1
    assert wires[0].route_points == ((0.5, 0.8), (8.0, 4.0))
    assert audit.pad_filtered_wire_count == 1
    assert audit.skipped_counts_by_reason["pad_outline"] == 1
    assert audit.skipped_counts_by_reason["pad_internal_short_line"] == 1
    assert audit.raw_candidate_wire_count == 2
    assert audit.pre_merge_wire_path_count == 1
    assert audit.extracted_wire_count == 1


def test_extract_wire_geometries_with_audit_reports_two_segment_merge_candidates():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (10.0, 0.0), "layer": "06_wire"},
        {"type": "LINE", "start": (10.0, 0.0), "end": (20.0, 5.0), "layer": "06_wire"},
        {"type": "LINE", "start": (100.0, 0.0), "end": (110.0, 0.0), "layer": "06_wire"},
    ]
    layer_info = [{"name": "06_wire", "mapped_type": "wire", "suggested_role": "wire"}]

    wires, audit = extract_wire_geometries_with_audit(raw_entities, layer_info)

    assert [wire.wire_id for wire in wires] == ["W0001", "W0002"]
    assert wires[0].route_points == ((0.0, 0.0), (10.0, 0.0), (20.0, 5.0))
    assert wires[0].source_entity_indices == (0, 1)
    assert wires[1].route_points == ((100.0, 0.0), (110.0, 0.0))
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

    report = format_wire_extraction_audit_report(audit)

    assert "06_wire entity stats:" in report
    assert "- LINE: 4" in report
    assert "Raw candidate wire paths: 4" in report
    assert "Pad-symbol filtered paths: 0" in report
    assert "Merged wire paths: 4 -> 2" in report
    assert "- unsupported_entity_type: 1" in report
    assert "  - #1 layer=06_wire type=POINT reason=unsupported_entity_type" in report
    assert "Potential split-wire joins before merge:" in report
    assert "- W0001(second) <-> W0002(second) @ (10.000000, 0.000000) [same_role_conflict]" in report
    assert "- W0003(second) <-> W0004(first) @ (110.000000, 0.000000) [continuous]" in report
    assert "- W0001 -> W0002 @ (10.000000, 0.000000) action=reverse_second_then_join reverse=W0002" in report
    assert "- W0003 -> W0004 @ (110.000000, 0.000000) action=join_as_is reverse=none" in report
    assert "Final wire paths:" in report
    assert "- W0001: length=20.000000 start=(0.000000, 0.000000) end=(20.000000, 0.000000) bend_count=1" in report


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
