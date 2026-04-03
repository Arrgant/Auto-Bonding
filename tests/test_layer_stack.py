"""Layer stacking helper tests."""

from __future__ import annotations

from core.layer_stack import (
    build_layer_order_map,
    build_stacked_preview_assembly,
    layer_sort_key,
    stack_preview_layer_names,
)


def test_layer_sort_key_prefers_leading_numbers():
    assert layer_sort_key("1_top") < layer_sort_key("2_mid")
    assert layer_sort_key("10_last") < layer_sort_key("A_misc")


def test_build_layer_order_map_uses_layer_info_and_raw_entities():
    layer_info = [
        {
            "name": "2_signal",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        }
    ]
    raw_entities = [
        {"type": "CIRCLE", "center": (0.0, 0.0), "radius": 1.0, "layer": "1_base"},
        {"type": "CIRCLE", "center": (4.0, 0.0), "radius": 1.0, "layer": "2_signal"},
    ]

    order = build_layer_order_map(layer_info, raw_entities)

    assert order["1_base"] == 0
    assert order["2_signal"] == 1


def test_build_stacked_preview_assembly_stacks_layers_in_numeric_order():
    raw_entities = [
        {"type": "CIRCLE", "center": (0.0, 0.0), "radius": 1.0, "layer": "1_base"},
        {
            "type": "LWPOLYLINE",
            "points": [(3.0, 0.0), (5.0, 0.0), (5.0, 2.0), (3.0, 2.0)],
            "closed": True,
            "layer": "2_top",
        },
    ]
    layer_info = [
        {
            "name": "1_base",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "entity_count": 1,
            "entity_types": {"CIRCLE": 1},
        },
        {
            "name": "2_top",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
    ]

    assembly = build_stacked_preview_assembly(
        raw_entities,
        layer_info,
        {
            0: 0.4,
            1: 0.6,
        },
    )

    assert assembly is not None
    compound = assembly.toCompound()
    bbox = compound.BoundingBox()
    assert bbox.zlen >= 1.0


def test_build_stacked_preview_assembly_uses_layer_thicknesses_and_visibility():
    raw_entities = [
        {
            "type": "LWPOLYLINE",
            "points": [(0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (0.0, 2.0)],
            "closed": True,
            "layer": "01_substrate",
        },
        {
            "type": "LWPOLYLINE",
            "points": [(1.0, 3.0), (3.0, 3.0), (3.0, 4.0), (1.0, 4.0)],
            "closed": True,
            "layer": "04_pad",
        },
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
            "name": "04_pad",
            "color": 1,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": "pad",
            "entity_count": 1,
            "entity_types": {"LWPOLYLINE": 1},
        },
    ]

    assembly = build_stacked_preview_assembly(
        raw_entities,
        layer_info,
        {},
        layer_thicknesses={"01_substrate": 0.8, "04_pad": 0.2},
        visible_layers={"01_substrate"},
    )

    assert assembly is not None
    bbox = assembly.toCompound().BoundingBox()
    assert bbox.zlen >= 0.8
    assert bbox.zlen < 1.1


def test_stack_preview_layer_names_skips_wire_layers():
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
            "enabled": True,
            "entity_count": 4,
            "entity_types": {"LWPOLYLINE": 4},
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
            "enabled": True,
            "entity_count": 40,
            "entity_types": {"LWPOLYLINE": 40},
        },
    ]

    names = stack_preview_layer_names(layer_info)

    assert names == {"04_pad"}
