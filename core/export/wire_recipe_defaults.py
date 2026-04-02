"""Built-in starter templates for wire production export."""

from __future__ import annotations

from .wire_models import WireOrderingConfig
from .wire_recipe_models import WireRecipeTemplate

# The field positions below were derived from the sample RX2000 workbook's
# `WB変換` formulas so that record defaults can target the same 55-word layout
# used by production WB1 files.
RX2000_STARTER_WB1_FIELD_MAP = {
    "role_code": 0,
    "cip_no": 1,
    "loop_setting": 2,
    "z_down_percent": 3,
    "angle_mode": 4,
    "device_no": 5,
    "us_linear_time": 6,
    "down_force_delay": 7,
    "down_force_linear_time": 8,
    "us_power_p": 9,
    "us_power_l": 10,
    "us_time_p": 11,
    "theta_input_correction": 12,
    "search_speed": 13,
    "tool_set_distance": 14,
    "cut_force": 15,
    "pull_distance": 16,
    "start_relative_position": 17,
    "loop_accel": 18,
    "group_no": 19,
    "rotation_height": 20,
    "guide_distance": 21,
    "pull_force": 22,
    "search_distance": 23,
    "pull_height": 24,
    "pushout_xy": 25,
    "pushout_z": 26,
    "pre_rotate_xy": 27,
    "rise_distance_15deg": 28,
    "angle_correction": 29,
    "wait_time": 30,
    "cut_speed": 31,
    "camera_x": 32,
    "al_wire_press_height": 33,
    "camera_y": 34,
    "al_wire_press_distance": 35,
    "camera_z": 36,
    "zup_force": 37,
    "bond_x": 38,
    "touch_correction": 39,
    "bond_y": 40,
    "reserved_ap": 41,
    "bond_z": 42,
    "reserved_ar": 43,
    "contact_surface_position": 44,
    "bond_angle": 45,
    "climb_angle": 46,
    "start_pressure": 47,
    "end_pressure": 48,
    "us_time_l": 49,
    "search_load": 50,
    "descent_amount": 51,
    "pull_angle": 52,
    "cut_correction": 53,
    "loop_correction": 54,
}

RX2000_SHARED_RECORD_DEFAULTS = {
    "cip_no": 0,
    "z_down_percent": 10,
    "angle_mode": 1,
    "device_no": 0,
    "us_linear_time": 0,
    "down_force_delay": 0,
    "down_force_linear_time": 20,
    "us_power_l": 135,
    "theta_input_correction": 0,
    "cut_force": 12,
    "loop_accel": 50,
    "rotation_height": 40,
    "guide_distance": 0,
    "pushout_xy": 0,
    "pushout_z": 0,
    "pre_rotate_xy": 25,
    "angle_correction": 0,
    "wait_time": 30,
    "cut_speed": 16,
    "al_wire_press_distance": 35,
    "zup_force": 12,
    "touch_correction": 50,
    "reserved_ap": 0,
    "reserved_ar": 0,
    "bond_angle": 65356,
    "climb_angle": 10,
    "start_pressure": 200,
    "end_pressure": 240,
    "us_time_l": 170,
    "search_load": 100,
    "descent_amount": 100,
    "pull_angle": 5,
    "cut_correction": 0,
    "loop_correction": 65526,
}

RX2000_ROLE_RECORD_DEFAULTS = {
    "first": {
        "loop_setting": 55,
        "us_power_p": 40,
        "us_time_p": 10,
        "search_speed": 50,
        "tool_set_distance": 40,
        "pull_distance": 3,
        "start_relative_position": 10,
        "pull_force": 12,
        "search_distance": 20,
        "pull_height": 20,
        "rise_distance_15deg": 0,
        "al_wire_press_height": 0,
        "contact_surface_position": 7316,
    },
    "second": {
        "loop_setting": 50,
        "us_power_p": 0,
        "us_time_p": 0,
        "search_speed": 99,
        "tool_set_distance": 67,
        "pull_distance": 40,
        "start_relative_position": 70,
        "pull_force": 19,
        "search_distance": 25,
        "pull_height": 250,
        "rise_distance_15deg": 90,
        "al_wire_press_height": 200,
        "contact_surface_position": 7331,
    },
}


def build_rx2000_default_template() -> WireRecipeTemplate:
    """Return the built-in RX2000 starter template."""

    return WireRecipeTemplate(
        template_id="rx2000-default",
        name="RX2000 Default",
        machine_type="RX2000",
        coord_scale=5.0,
        default_z=1455.2,
        ordering=WireOrderingConfig(
            primary_axis="x",
            primary_direction="asc",
            secondary_direction="asc",
            start_role="first",
            group_no=1,
        ),
        header_defaults={},
        record_defaults=dict(RX2000_SHARED_RECORD_DEFAULTS),
        role_record_defaults={
            role: dict(values) for role, values in RX2000_ROLE_RECORD_DEFAULTS.items()
        },
        wb1_field_map=dict(RX2000_STARTER_WB1_FIELD_MAP),
        wb1_record_defaults={},
        wb1_role_codes={"first": 0, "second": 2},
    )


def default_wire_recipe_templates() -> list[WireRecipeTemplate]:
    """Return all built-in wire export templates."""

    return [build_rx2000_default_template()]


__all__ = [
    "RX2000_ROLE_RECORD_DEFAULTS",
    "RX2000_SHARED_RECORD_DEFAULTS",
    "RX2000_STARTER_WB1_FIELD_MAP",
    "build_rx2000_default_template",
    "default_wire_recipe_templates",
]
