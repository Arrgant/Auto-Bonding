"""Built-in starter templates for wire production export."""

from __future__ import annotations

from .wire_models import WireOrderingConfig
from .wire_recipe_models import TemplateScalar, WireRecipeTemplate

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

RX2000_HEADER_ROW_TOKENS = {
    "PRE:1": ["0004", "0001", "002D", "0016"],
    "G:1": ["0002", "0032", "0000", "0000", "DFF2", "000A", "FB53", "0000", "0E4D", "0000", "0000", "0000"],
    "H:0": ["0000", "0064", "0032", "0032", "0032", "0001"],
    "I:0": [
        "0001", "0000", "0001", "1C40", "0002", "0002", "0000", "0000", "0001", "000A", "0000", "0000",
        "0002", "0001", "0000", "0000", "0000", "0000", "0000", "0000", "0000", "0000", "0000", "0000",
        "0000", "0064", "0064", "0064", "0000", "0000", "0000", "0000", "0000", "0000", "0000", "0000",
        "0000", "0000", "0000", "0000", "0000", "0000", "0000", "0000",
    ],
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

RX2000_PFILE_ROWS = [
    [25, 9999, 9999, 1170, 500, 4000, 40, 2, 9999, 9999, 350, 1000, 200, 2360, 0, 100, 1000, 4000, 100, 3, 2000, 9999, 600, 750, 500, 1000, 20, 3, 1, 9999, 0, 0],
    [25, 9999, 9999, 1170, 500, 4000, 40, 2, 9999, 9999, 350, 1000, 9, 2360, 0, 100, 1000, 4000, 100, 3, 2000, 9999, 600, 700, 500, 1000, 20, 3, 1, 9999, 0, 0],
    [150, 250, 0, 150, 0, 150, 5, 500, 300, 2000, 400, 5, 100, 8000, 1000, 25, 1, 0, 0, 2, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [1050, 0, 0, 0, 0, 0, 0, 1, 20, 30, 51, 70, 1, 2, 100, 20, 25, 7483, 2386, 4, 4, 8000, 4265, 30, 0, 0, 0, 0, 0, 0, 0, 0],
    [100, 800, 800, 10, 100, 50, 200, 100, 0, 0, 0, 0, 0, 0, 0, 0, 186, 255, 89, 106, 182, 255, 78, 98, 513, 694, 784, 101, 494, 647, 731, 931],
    [0, 0, 200, 20, 10, 156, 5000, 0, 0, 0, 0, 0, 60, 0, 200, 0, 118, 147, 857, 892, 0, 0, 0, 10, 0, 0, 0, 2021, 2, 15, 9, 56],
    [100, 1000, 24, 5000, 5000, 5000, 0, 0, 100, 1000, 24, 5000, 5000, 5000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [9999, 9999, 0, 1850, 8000, 9999, 0, 0, 9950, 9999, 0, 1977, 9999, 9999, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0],
    [30, 2500, 55, 60, 3600, 9000, 0, 0, 20, 6000, 1200, 30, 2500, 55, 1, 300, 0, 7, 5, 5, 0, 30, 30, 30, 60, 0, 0, 60, 60, 60, 0, 100],
    [0, 2, 3, 4, 6, 8, 10, 12, 0, 2, 3, 4, 6, 8, 10, 12, 1000, 1000, 100, 5, 100, 5, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]


def _flatten_header_rows(row_tokens: dict[str, list[str]]) -> dict[str, TemplateScalar]:
    flattened: dict[str, TemplateScalar] = {}
    for prefix, tokens in row_tokens.items():
        for word_index, token in enumerate(tokens):
            flattened[f"{prefix}:{word_index}"] = token
    return flattened


def _flatten_pfile_rows(rows: list[list[int]], *, start_row: int = 4) -> dict[str, TemplateScalar]:
    flattened: dict[str, TemplateScalar] = {}
    for row_offset, values in enumerate(rows):
        row_number = start_row + row_offset
        for column_index, value in enumerate(values, start=1):
            flattened[f"{_excel_column(column_index)}{row_number}"] = value
    return flattened


def _excel_column(index: int) -> str:
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


RX2000_HEADER_DEFAULTS = _flatten_header_rows(RX2000_HEADER_ROW_TOKENS)
RX2000_PFILE_CELL_OVERRIDES = _flatten_pfile_rows(RX2000_PFILE_ROWS)

# Only direct, clearly labeled PFILE cells are promoted into named defaults here.
# Unlabeled cells and transformed formulas (for example Q11/100 in the workbook)
# stay in the raw cell override bucket until we model their display-unit conversions.
RX2000_PFILE_FIELD_MAP = {
    "search_force": "A8",
    "search_force_limit": "I8",
    "cut_force": "D8",
    "cut_force_limit": "L8",
    "wait_time": "E8",
    "wait_time_limit": "M8",
    "linear_time": "F8",
    "linear_time_limit": "N8",
    "h1_us_low_128_output_bit": "Q8",
    "h1_us_low_128_current_ma": "Y8",
    "h1_us_low_192_output_bit": "R8",
    "h1_us_low_192_current_ma": "Z8",
    "h1_us_hi_128_output_bit": "S8",
    "h1_us_hi_128_current_ma": "AA8",
    "h1_us_hi_192_output_bit": "T8",
    "h1_us_hi_192_current_ma": "AB8",
    "h2_us_low_128_output_bit": "U8",
    "h2_us_low_128_current_ma": "AC8",
    "h2_us_low_192_output_bit": "V8",
    "h2_us_low_192_current_ma": "AD8",
    "h2_us_hi_128_output_bit": "W8",
    "h2_us_hi_128_current_ma": "AE8",
    "h2_us_hi_192_output_bit": "X8",
    "h2_us_hi_192_current_ma": "AF8",
    "us_off_mode": "A9",
    "h1_recog_wait_ms": "I9",
    "h2_recog_wait_ms": "J9",
    "length_check_limit_pulse": "D9",
    "length_check_limit_guard_pulse": "L9",
    "wire_cutting_count": "E9",
    "recog_xy_acc_ms": "M9",
    "manual_low_speed_hz": "F9",
    "manual_high_speed_hz": "G9",
    "theta_2nd_rate": "O9",
    "h_disp_mode": "H9",
    "check_mode": "P9",
    "x_1_dot_data": "Q9",
    "y_1_dot_data": "R9",
    "x_2_dot_data": "S9",
    "y_2_dot_data": "T9",
    "display_no": "U9",
    "h_disp_no": "V9",
    "year": "AB9",
    "month": "AC9",
    "day": "AD9",
    "hour": "AE9",
    "minute": "AF9",
    "h1_cutter": "A10",
    "h1_cutter_x1000_count": "B10",
    "h1_tool": "C10",
    "h1_guide": "D10",
    "h1_block": "E10",
    "h1_tube": "F10",
    "h2_cutter": "I10",
    "h2_cutter_x1000_count": "J10",
    "h2_tool": "K10",
    "h2_guide": "L10",
    "h2_block": "M10",
    "h2_tube": "N10",
    "h1_x_origin_plus": "A11",
    "h1_y_origin_plus": "B11",
    "h1_z_origin_plus": "C11",
    "h1_theta_origin_plus": "D11",
    "h1_x_positive_limit": "E11",
    "h1_y_positive_limit": "F11",
    "h1_tool_plus": "G11",
    "h1_y_limit": "H11",
    "h2_x_origin_plus": "I11",
    "h2_y_origin_plus": "J11",
    "h2_z_origin_plus": "K11",
    "h2_theta_origin_plus": "L11",
    "h2_x_positive_limit": "M11",
    "h2_y_positive_limit": "N11",
    "h2_tool_plus": "O11",
    "h2_y_limit": "P11",
    "usual_low_speed_khz": "A12",
    "usual_high_speed_khz": "B12",
    "usual_acc_ms": "C12",
    "recog_acc_ms": "D12",
    "camera_high_pulse": "E12",
    "z_lower_limit_pulse": "F12",
    "chip_search_pulse": "G12",
    "frame_search_pulse": "H12",
    "theta_fl_times_25_hz": "I12",
    "theta_fh_times_25_hz": "J12",
    "theta_rate": "K12",
    "loop_low_speed_khz": "L12",
    "loop_high_speed_khz": "M12",
    "correction_mode": "O12",
    "correction_limit_pulse": "P12",
    "mis_touch_down_bit": "Q12",
    "mis_touch_down_limit_bit": "Y12",
    "recog_retry_count": "R12",
    "recog_retry_limit_count": "Z12",
    "z_move_height_mm": "S12",
    "z_move_height_limit_mm": "AA12",
    "feed_height_mm": "T12",
    "feed_height_limit_mm": "AB12",
    "wire_check_small_to_1mm_count": "A13",
    "wire_check_small_to_2mm_count": "B13",
    "wire_check_small_to_3mm_count": "C13",
    "wire_check_small_to_4mm_count": "D13",
    "wire_check_small_to_6mm_count": "E13",
    "wire_check_small_to_8mm_count": "F13",
    "wire_check_small_to_10mm_count": "G13",
    "wire_check_small_over_10mm_count": "H13",
    "wire_check_large_to_1mm_count": "I13",
    "wire_check_large_to_2mm_count": "J13",
    "wire_check_large_to_3mm_count": "K13",
    "wire_check_large_to_4mm_count": "L13",
    "wire_check_large_to_6mm_count": "M13",
    "wire_check_large_to_8mm_count": "N13",
    "wire_check_large_to_10mm_count": "O13",
    "wire_check_large_over_10mm_count": "P13",
    "send_limit_ms": "Q13",
    "spool_limit_ms": "R13",
    "h1_spool_on_ms": "S13",
    "h1_spool_off_ms": "T13",
    "h2_spool_on_ms": "U13",
    "h2_spool_off_ms": "V13",
    "lowlimit_count": "W13",
}


def _split_pfile_overrides(
    overrides: dict[str, TemplateScalar],
    field_map: dict[str, str],
) -> tuple[dict[str, TemplateScalar], dict[str, TemplateScalar]]:
    named_defaults: dict[str, TemplateScalar] = {}
    remaining = dict(overrides)
    for field_name, cell_ref in field_map.items():
        if cell_ref in remaining:
            named_defaults[field_name] = remaining.pop(cell_ref)
    return named_defaults, remaining


RX2000_PFILE_NAMED_DEFAULTS, RX2000_PFILE_UNMAPPED_CELL_OVERRIDES = _split_pfile_overrides(
    RX2000_PFILE_CELL_OVERRIDES,
    RX2000_PFILE_FIELD_MAP,
)


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
            group_mode="clustered",
            group_no=1,
        ),
        header_defaults=dict(RX2000_HEADER_DEFAULTS),
        pfile_field_map=dict(RX2000_PFILE_FIELD_MAP),
        pfile_named_defaults=dict(RX2000_PFILE_NAMED_DEFAULTS),
        pfile_cell_overrides=dict(RX2000_PFILE_UNMAPPED_CELL_OVERRIDES),
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
    "RX2000_HEADER_DEFAULTS",
    "RX2000_HEADER_ROW_TOKENS",
    "RX2000_PFILE_CELL_OVERRIDES",
    "RX2000_PFILE_FIELD_MAP",
    "RX2000_PFILE_NAMED_DEFAULTS",
    "RX2000_PFILE_ROWS",
    "RX2000_PFILE_UNMAPPED_CELL_OVERRIDES",
    "RX2000_ROLE_RECORD_DEFAULTS",
    "RX2000_SHARED_RECORD_DEFAULTS",
    "RX2000_STARTER_WB1_FIELD_MAP",
    "build_rx2000_default_template",
    "default_wire_recipe_templates",
]
