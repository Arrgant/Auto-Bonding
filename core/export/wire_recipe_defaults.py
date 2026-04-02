"""Built-in starter templates for wire production export."""

from __future__ import annotations

from .wire_models import WireOrderingConfig
from .wire_recipe_models import WireRecipeTemplate

RX2000_STARTER_WB1_FIELD_MAP = {
    "role_code": 0,
    "wire_seq": 1,
    "bond_x": 2,
    "bond_y": 3,
    "bond_z": 4,
    "group_no": 5,
    "point_seq": 6,
}


def build_rx2000_default_template() -> WireRecipeTemplate:
    """Return the built-in RX2000 starter template."""

    return WireRecipeTemplate(
        template_id="rx2000-default",
        name="RX2000 Default",
        machine_type="RX2000",
        coord_scale=1.0,
        default_z=0.0,
        ordering=WireOrderingConfig(
            primary_axis="x",
            primary_direction="asc",
            secondary_direction="asc",
            start_role="first",
            group_no=1,
        ),
        header_defaults={},
        record_defaults={},
        wb1_field_map=dict(RX2000_STARTER_WB1_FIELD_MAP),
        wb1_record_defaults={},
        wb1_role_codes={"first": 0, "second": 2},
    )


def default_wire_recipe_templates() -> list[WireRecipeTemplate]:
    """Return all built-in wire export templates."""

    return [build_rx2000_default_template()]


__all__ = [
    "RX2000_STARTER_WB1_FIELD_MAP",
    "build_rx2000_default_template",
    "default_wire_recipe_templates",
]
