"""Preview entity helper tests."""

from __future__ import annotations

from core.preview_entities import build_preview_entities


def test_build_preview_entities_merges_connected_collinear_lines():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (2.0, 0.0), "layer": "1_trace"},
        {"type": "LINE", "start": (2.0, 0.0), "end": (5.0, 0.0), "layer": "1_trace"},
        {"type": "LINE", "start": (9.0, 0.0), "end": (9.0, 2.0), "layer": "2_other"},
    ]
    layer_info = [
        {
            "name": "1_trace",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "entity_count": 2,
            "entity_types": {"LINE": 2},
        },
        {
            "name": "2_other",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "entity_count": 1,
            "entity_types": {"LINE": 1},
        },
    ]

    preview_entities = build_preview_entities(raw_entities, layer_info)

    assert len(preview_entities) == 2
    merged = preview_entities[0]
    assert merged.entity["type"] == "LINE"
    assert merged.entity["start"] == (0.0, 0.0)
    assert merged.entity["end"] == (5.0, 0.0)
    assert merged.source_indices == (0, 1)


def test_build_preview_entities_keeps_non_collinear_lines_separate():
    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (2.0, 0.0), "layer": "1_trace"},
        {"type": "LINE", "start": (2.0, 0.0), "end": (2.0, 3.0), "layer": "1_trace"},
    ]

    preview_entities = build_preview_entities(raw_entities, [])

    assert len(preview_entities) == 2
    assert all(item.source_indices == (index,) for index, item in enumerate(preview_entities))
