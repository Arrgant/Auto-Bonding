from __future__ import annotations

import math
from collections import Counter

import pytest

from core.fallback import infer_elements_from_raw_entities


def test_infer_elements_from_raw_entities_preserves_basic_geometry():
    circle_points = [
        (math.cos(index * math.pi / 4.0), math.sin(index * math.pi / 4.0))
        for index in range(8)
    ]

    raw_entities = [
        {"type": "LINE", "start": (0.0, 0.0), "end": (5.0, 0.0), "layer": "WIRE"},
        {"type": "CIRCLE", "center": (8.0, 8.0), "radius": 1.5, "layer": "PAD"},
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (3.0, 0.0), (3.0, 2.0), (0.0, 2.0)],
            "closed": True,
            "layer": "FRAME",
        },
        {
            "type": "LWPOLYLINE",
            "points": circle_points,
            "closed": True,
            "layer": "ROUND",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(10.0, 0.0), (12.0, 0.0)],
            "closed": False,
            "layer": "OPEN",
        },
    ]
    config = {
        "default_wire_diameter": 0.025,
        "default_material": "gold",
    }

    elements = infer_elements_from_raw_entities(raw_entities, config)
    counts = Counter(element.element_type for element in elements)

    assert counts["wire"] == 2
    assert counts["die_pad"] == 3

    circle_pad = next(
        element for element in elements if element.layer == "PAD" and element.properties.get("shape") == "circle"
    )
    assert circle_pad.geometry["radius"] == 1.5

    round_pad = next(
        element for element in elements if element.layer == "ROUND" and element.properties.get("shape") == "circle"
    )
    assert round_pad.geometry["radius"] == pytest.approx(1.0, rel=0.2)

    open_wire = next(element for element in elements if element.layer == "OPEN")
    assert open_wire.geometry["p1"] == [10.0, 0.0, 0.0]
    assert open_wire.geometry["p2"] == [12.0, 0.0, 0.0]
