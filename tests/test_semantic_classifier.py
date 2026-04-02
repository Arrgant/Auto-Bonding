"""Semantic classifier tests driven by the 6-layer rule table."""

from __future__ import annotations

from core.semantic import classify_semantic_layers


def test_classify_semantic_layers_promotes_core_rule_table_objects():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (20.0, 0.0), (20.0, 12.0), (0.0, 12.0)],
            "closed": True,
            "layer": "01_substrate",
        },
        {"type": "CIRCLE", "center": (3.0, 3.0), "radius": 1.0, "layer": "01_substrate"},
        {
            "type": "LWPOLYLINE",
            "points": [(2.0, 2.0), (5.0, 2.0), (5.0, 4.0), (2.0, 4.0)],
            "closed": True,
            "layer": "04_pad",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(14.0, 8.0), (17.0, 8.0), (17.0, 10.0), (14.0, 10.0)],
            "closed": True,
            "layer": "04_pad",
        },
        {"type": "LINE", "start": (3.5, 3.0), "end": (15.5, 9.0), "layer": "06_wire"},
    ]
    layer_info = [
        {
            "name": "01_substrate",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "substrate",
            "entity_count": 2,
            "entity_types": {"LWPOLYLINE": 1, "CIRCLE": 1},
        },
        {
            "name": "04_pad",
            "color": 1,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "die_pad",
            "suggested_role": "pad",
            "entity_count": 2,
            "entity_types": {"LWPOLYLINE": 2},
        },
        {
            "name": "06_wire",
            "color": 3,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "wire",
            "suggested_role": "wire",
            "entity_count": 1,
            "entity_types": {"LINE": 1},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    entity_kinds = {entity.kind for entity in result.entities}
    review_kinds = {candidate.kind for candidate in result.review}

    assert "substrate" in entity_kinds
    assert "hole" in entity_kinds
    assert "pad" in entity_kinds
    assert "wire" in entity_kinds
    assert "hole_candidate" not in review_kinds

    hole_entities = [entity for entity in result.entities if entity.kind == "hole"]
    assert len(hole_entities) == 1
    assert hole_entities[0].properties["hole_kind"] == "tooling"
    assert set(hole_entities[0].properties["edge_contacts"]) == {"left"}


def test_classify_semantic_layers_marks_module_regions_with_left_right_sides():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(2.0, 2.0), (10.0, 2.0), (10.0, 8.0), (2.0, 8.0)],
            "closed": True,
            "layer": "02_module_region",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(14.0, 2.0), (22.0, 2.0), (22.0, 8.0), (14.0, 8.0)],
            "closed": True,
            "layer": "02_module_region",
        },
    ]
    layer_info = [
        {
            "name": "02_module_region",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "module_region",
            "entity_count": 2,
            "entity_types": {"LWPOLYLINE": 2},
        }
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    module_entities = [entity for entity in result.entities if entity.kind == "module_region"]
    assert len(module_entities) == 2
    assert {entity.properties["side"] for entity in module_entities} == {"left", "right"}


def test_classify_semantic_layers_tracks_pad_cluster_details_and_wire_snaps():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)],
            "closed": True,
            "layer": "04_pad",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(5.0, 0.0), (7.0, 0.0), (7.0, 1.0), (5.0, 1.0)],
            "closed": True,
            "layer": "04_pad",
        },
        {"type": "LINE", "start": (-0.2, 0.5), "end": (7.2, 0.5), "layer": "06_wire"},
    ]
    layer_info = [
        {
            "name": "04_pad",
            "color": 1,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "die_pad",
            "suggested_role": "pad",
            "entity_count": 2,
            "entity_types": {"LWPOLYLINE": 2},
        },
        {
            "name": "06_wire",
            "color": 3,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "wire",
            "suggested_role": "wire",
            "entity_count": 1,
            "entity_types": {"LINE": 1},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    pad_entities = [entity for entity in result.entities if entity.kind == "pad"]
    wire_entities = [entity for entity in result.entities if entity.kind == "wire"]

    assert len(pad_entities) == 2
    assert all(entity.properties["cluster_size"] == 2 for entity in pad_entities)
    assert all(entity.properties["size_signature"] == (2.0, 1.0) for entity in pad_entities)
    assert len(wire_entities) == 1
    assert wire_entities[0].properties["start_pad_id"].startswith("pad_candidate_")
    assert wire_entities[0].properties["end_pad_id"].startswith("pad_candidate_")
    assert wire_entities[0].properties["segment_count"] == 1
    assert wire_entities[0].properties["direction_consistency"] == 1.0
    assert wire_entities[0].properties["start_anchor_alignment"] >= 0.99
    assert wire_entities[0].properties["end_anchor_alignment"] >= 0.99
    assert wire_entities[0].geometry["snapped_start_point"] == (0.0, 0.5)
    assert wire_entities[0].geometry["snapped_end_point"] == (7.0, 0.5)


def test_classify_semantic_layers_adds_die_region_module_and_pad_relations():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (20.0, 0.0), (20.0, 12.0), (0.0, 12.0)],
            "closed": True,
            "layer": "02_module_region",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(6.0, 4.0), (12.0, 4.0), (12.0, 8.0), (6.0, 8.0)],
            "closed": True,
            "layer": "05_die_region",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(4.0, 4.5), (5.0, 4.5), (5.0, 5.5), (4.0, 5.5)],
            "closed": True,
            "layer": "04_pad",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(13.0, 6.5), (14.0, 6.5), (14.0, 7.5), (13.0, 7.5)],
            "closed": True,
            "layer": "04_pad",
        },
    ]
    layer_info = [
        {
            "name": "02_module_region",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "module_region",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "05_die_region",
            "color": 2,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "die_region",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "04_pad",
            "color": 1,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "die_pad",
            "suggested_role": "pad",
            "entity_count": 2,
            "entity_types": {"LWPOLYLINE": 2},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    die_entities = [entity for entity in result.entities if entity.kind == "die_region"]

    assert len(die_entities) == 1
    assert die_entities[0].properties["module_overlap_ratio"] >= 0.99
    assert die_entities[0].properties["nearby_pad_count"] == 2
    assert "nearby_pad_ids" in die_entities[0].properties
    assert set(die_entities[0].properties["pad_side_coverage"]) == {"left", "right"}
    assert die_entities[0].properties["pad_side_count"] == 2


def test_classify_semantic_layers_tracks_wire_polyline_consistency_and_die_edge_contacts():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (18.0, 0.0), (18.0, 12.0), (0.0, 12.0)],
            "closed": True,
            "layer": "02_module_region",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(0.4, 4.0), (6.0, 4.0), (6.0, 8.0), (0.4, 8.0)],
            "closed": True,
            "layer": "05_die_region",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(6.5, 4.5), (7.5, 4.5), (7.5, 5.5), (6.5, 5.5)],
            "closed": True,
            "layer": "04_pad",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(6.5, 6.5), (7.5, 6.5), (7.5, 7.5), (6.5, 7.5)],
            "closed": True,
            "layer": "04_pad",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(6.8, 5.0), (9.5, 5.0), (12.0, 6.0), (14.8, 6.0)],
            "closed": False,
            "layer": "06_wire",
        },
    ]
    layer_info = [
        {
            "name": "02_module_region",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "module_region",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "05_die_region",
            "color": 2,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "die_region",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "04_pad",
            "color": 1,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "die_pad",
            "suggested_role": "pad",
            "entity_count": 2,
            "entity_types": {"LWPOLYLINE": 2},
        },
        {
            "name": "06_wire",
            "color": 3,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "wire",
            "suggested_role": "wire",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    wire_entities = [entity for entity in result.entities if entity.kind == "wire"]
    die_entities = [entity for entity in result.entities if entity.kind == "die_region"]

    assert len(wire_entities) == 1
    assert wire_entities[0].properties["segment_count"] == 3
    assert wire_entities[0].properties["bend_count"] == 2
    assert wire_entities[0].properties["direction_consistency"] >= 0.92
    assert len(die_entities) == 1
    assert die_entities[0].properties["touches_module_edge"] is True
    assert "left" in die_entities[0].properties["module_edge_contacts"]


def test_classify_semantic_layers_supports_explicit_hole_layers():
    raw_entities = [
        {"type": "CIRCLE", "center": (10.0, 10.0), "radius": 1.5, "layer": "07_mount_hole"},
    ]
    layer_info = [
        {
            "name": "07_mount_hole",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "hole",
            "entity_count": 1,
            "entity_types": {"CIRCLE": 1},
        }
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    hole_entities = [entity for entity in result.entities if entity.kind == "hole"]
    assert len(hole_entities) == 1
    assert hole_entities[0].properties["hole_kind"] == "layer_defined"


def test_classify_semantic_layers_does_not_duplicate_explicit_hole_layers_inside_substrate():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (40.0, 0.0), (40.0, 24.0), (0.0, 24.0)],
            "closed": True,
            "layer": "01_substrate",
        },
        {"type": "CIRCLE", "center": (4.0, 4.0), "radius": 1.0, "layer": "07_mount_hole"},
    ]
    layer_info = [
        {
            "name": "01_substrate",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "substrate",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "07_mount_hole",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "hole",
            "entity_count": 1,
            "entity_types": {"CIRCLE": 1},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    hole_entities = [entity for entity in result.entities if entity.kind == "hole"]
    assert len(hole_entities) == 1
    assert hole_entities[0].layer_name == "07_mount_hole"


def test_classify_semantic_layers_promotes_repeated_internal_substrate_circles_to_tooling_holes():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (30.0, 0.0), (30.0, 18.0), (0.0, 18.0)],
            "closed": True,
            "layer": "01_substrate",
        },
        {"type": "CIRCLE", "center": (8.0, 9.0), "radius": 0.8, "layer": "01_substrate"},
        {"type": "CIRCLE", "center": (22.0, 9.0), "radius": 0.8, "layer": "01_substrate"},
    ]
    layer_info = [
        {
            "name": "01_substrate",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "substrate",
            "entity_count": 3,
            "entity_types": {"LWPOLYLINE": 1, "CIRCLE": 2},
        }
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    hole_entities = [entity for entity in result.entities if entity.kind == "hole"]
    assert len(hole_entities) == 2
    assert all(entity.properties["hole_kind"] == "tooling" for entity in hole_entities)


def test_classify_semantic_layers_promotes_lead_frame_circle_inside_substrate_to_hole():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (24.0, 0.0), (24.0, 14.0), (0.0, 14.0)],
            "closed": True,
            "layer": "01_substrate",
        },
        {"type": "CIRCLE", "center": (2.0, 2.0), "radius": 0.6, "layer": "03_lead_frame"},
    ]
    layer_info = [
        {
            "name": "01_substrate",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "substrate",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "03_lead_frame",
            "color": 4,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "lead_frame",
            "suggested_role": "lead_frame",
            "entity_count": 1,
            "entity_types": {"CIRCLE": 1},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    hole_entities = [entity for entity in result.entities if entity.kind == "hole"]
    assert len(hole_entities) == 1
    assert hole_entities[0].layer_name == "03_lead_frame"
    assert hole_entities[0].properties["hole_kind"] == "mounting"


def test_classify_semantic_layers_keeps_concentric_rounds_as_round_features():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (80.0, 0.0), (80.0, 50.0), (0.0, 50.0)],
            "closed": True,
            "layer": "01_substrate",
        },
        {"type": "CIRCLE", "center": (18.0, 18.0), "radius": 2.0, "layer": "03_lead_frame"},
        {"type": "CIRCLE", "center": (18.0, 18.0), "radius": 4.0, "layer": "03_lead_frame"},
    ]
    layer_info = [
        {
            "name": "01_substrate",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "substrate",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
        {
            "name": "03_lead_frame",
            "color": 4,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": "lead_frame",
            "suggested_role": "lead_frame",
            "entity_count": 2,
            "entity_types": {"CIRCLE": 2},
        },
    ]

    result = classify_semantic_layers(raw_entities, layer_info)

    hole_entities = [entity for entity in result.entities if entity.kind == "hole"]
    round_entities = [entity for entity in result.entities if entity.kind == "round_feature"]
    round_review = [candidate for candidate in result.review if candidate.kind == "round_feature_candidate"]
    assert len(hole_entities) == 0
    assert len(round_entities) + len(round_review) == 2
