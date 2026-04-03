"""Source-of-truth metadata for RX2000 WB1 field sourcing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .wire_recipe_defaults import RX2000_STARTER_WB1_FIELD_MAP
from .wire_recipe_models import WireRecipeTemplate

DxfAvailability = Literal["direct", "derived", "3d_only", "no"]
WB1WriteCategory = Literal[
    "output_name",
    "template_header",
    "template_raw_index",
    "template_shared",
    "template_role",
    "dynamic_geometry",
    "dynamic_ordering",
    "hardcoded_zero",
    "prototype_copy",
]


@dataclass(frozen=True)
class WB1FieldSourceInfo:
    """Describe where one WB1 field can come from."""

    field_name: str
    dxf_availability: DxfAvailability
    current_source: str
    current_from_dxf: bool
    note: str


@dataclass(frozen=True)
class WB1WritePlanItem:
    """Describe one WB1 location that the current exporter may modify."""

    segment: str
    location: str
    field_name: str
    index: int | None
    categories: tuple[WB1WriteCategory, ...]
    writes_from_dxf: bool
    detail: str


RX2000_WB1_FIELD_SOURCES: dict[str, WB1FieldSourceInfo] = {
    "role_code": WB1FieldSourceInfo(
        field_name="role_code",
        dxf_availability="derived",
        current_source="wire endpoint role",
        current_from_dxf=True,
        note="Comes from the extracted first/second point ordering for each wire.",
    ),
    "cip_no": WB1FieldSourceInfo(
        field_name="cip_no",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine/product routing code; not present in wire geometry.",
    ),
    "loop_setting": WB1FieldSourceInfo(
        field_name="loop_setting",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Loop recipe depends on process, not on raw DXF geometry alone.",
    ),
    "z_down_percent": WB1FieldSourceInfo(
        field_name="z_down_percent",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine motion tuning parameter.",
    ),
    "angle_mode": WB1FieldSourceInfo(
        field_name="angle_mode",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Mode switch, not a direct geometric value.",
    ),
    "device_no": WB1FieldSourceInfo(
        field_name="device_no",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Product/device recipe identifier.",
    ),
    "us_linear_time": WB1FieldSourceInfo(
        field_name="us_linear_time",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Ultrasonic timing parameter from process recipe.",
    ),
    "down_force_delay": WB1FieldSourceInfo(
        field_name="down_force_delay",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine timing parameter from process recipe.",
    ),
    "down_force_linear_time": WB1FieldSourceInfo(
        field_name="down_force_linear_time",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine timing parameter from process recipe.",
    ),
    "us_power_p": WB1FieldSourceInfo(
        field_name="us_power_p",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Primary ultrasonic power; process-driven.",
    ),
    "us_power_l": WB1FieldSourceInfo(
        field_name="us_power_l",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Secondary ultrasonic power; process-driven.",
    ),
    "us_time_p": WB1FieldSourceInfo(
        field_name="us_time_p",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Primary ultrasonic time; process-driven.",
    ),
    "theta_input_correction": WB1FieldSourceInfo(
        field_name="theta_input_correction",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Calibration/correction term, not raw geometry.",
    ),
    "search_speed": WB1FieldSourceInfo(
        field_name="search_speed",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Search motion speed comes from process recipe.",
    ),
    "tool_set_distance": WB1FieldSourceInfo(
        field_name="tool_set_distance",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Tool setup distance comes from process recipe.",
    ),
    "cut_force": WB1FieldSourceInfo(
        field_name="cut_force",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Cutting force is process-driven.",
    ),
    "pull_distance": WB1FieldSourceInfo(
        field_name="pull_distance",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Pull distance is process-driven.",
    ),
    "start_relative_position": WB1FieldSourceInfo(
        field_name="start_relative_position",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Relative machine start offset, not a raw wire coordinate.",
    ),
    "loop_accel": WB1FieldSourceInfo(
        field_name="loop_accel",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Loop motion acceleration belongs to recipe tuning.",
    ),
    "group_no": WB1FieldSourceInfo(
        field_name="group_no",
        dxf_availability="derived",
        current_source="clustered ordering / fixed fallback",
        current_from_dxf=True,
        note="Current RX2000 default template derives group numbers from spatial wire clusters, while fixed mode is still available for custom templates.",
    ),
    "rotation_height": WB1FieldSourceInfo(
        field_name="rotation_height",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine motion parameter from template.",
    ),
    "guide_distance": WB1FieldSourceInfo(
        field_name="guide_distance",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Guide/tooling distance from template.",
    ),
    "pull_force": WB1FieldSourceInfo(
        field_name="pull_force",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Pull force from recipe.",
    ),
    "search_distance": WB1FieldSourceInfo(
        field_name="search_distance",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Search distance from recipe.",
    ),
    "pull_height": WB1FieldSourceInfo(
        field_name="pull_height",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Pull height from recipe.",
    ),
    "pushout_xy": WB1FieldSourceInfo(
        field_name="pushout_xy",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Push-out correction belongs to machine/process calibration.",
    ),
    "pushout_z": WB1FieldSourceInfo(
        field_name="pushout_z",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Push-out correction belongs to machine/process calibration.",
    ),
    "pre_rotate_xy": WB1FieldSourceInfo(
        field_name="pre_rotate_xy",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Pre-rotate correction belongs to machine/process calibration.",
    ),
    "rise_distance_15deg": WB1FieldSourceInfo(
        field_name="rise_distance_15deg",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Recipe-specific rise parameter.",
    ),
    "angle_correction": WB1FieldSourceInfo(
        field_name="angle_correction",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Correction field, not raw geometry.",
    ),
    "wait_time": WB1FieldSourceInfo(
        field_name="wait_time",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine timing parameter from recipe.",
    ),
    "cut_speed": WB1FieldSourceInfo(
        field_name="cut_speed",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Cutting speed from recipe.",
    ),
    "camera_x": WB1FieldSourceInfo(
        field_name="camera_x",
        dxf_availability="no",
        current_source="hardcoded zero / future transform",
        current_from_dxf=False,
        note="Needs camera-to-bond calibration or external machine coordinate transform.",
    ),
    "al_wire_press_height": WB1FieldSourceInfo(
        field_name="al_wire_press_height",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Recipe-specific machine motion parameter.",
    ),
    "camera_y": WB1FieldSourceInfo(
        field_name="camera_y",
        dxf_availability="no",
        current_source="hardcoded zero / future transform",
        current_from_dxf=False,
        note="Needs camera-to-bond calibration or external machine coordinate transform.",
    ),
    "al_wire_press_distance": WB1FieldSourceInfo(
        field_name="al_wire_press_distance",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Recipe-specific machine motion parameter.",
    ),
    "camera_z": WB1FieldSourceInfo(
        field_name="camera_z",
        dxf_availability="no",
        current_source="hardcoded zero / future transform",
        current_from_dxf=False,
        note="Needs camera-to-bond calibration or external machine coordinate transform.",
    ),
    "zup_force": WB1FieldSourceInfo(
        field_name="zup_force",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine force parameter from recipe.",
    ),
    "bond_x": WB1FieldSourceInfo(
        field_name="bond_x",
        dxf_availability="direct",
        current_source="wire geometry first/second point",
        current_from_dxf=True,
        note="Directly comes from the wire endpoint X coordinate after scaling.",
    ),
    "touch_correction": WB1FieldSourceInfo(
        field_name="touch_correction",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Touch correction belongs to process calibration.",
    ),
    "bond_y": WB1FieldSourceInfo(
        field_name="bond_y",
        dxf_availability="direct",
        current_source="wire geometry first/second point",
        current_from_dxf=True,
        note="Directly comes from the wire endpoint Y coordinate after scaling.",
    ),
    "reserved_ap": WB1FieldSourceInfo(
        field_name="reserved_ap",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Reserved/unknown slot; keep template-controlled.",
    ),
    "bond_z": WB1FieldSourceInfo(
        field_name="bond_z",
        dxf_availability="3d_only",
        current_source="default_z fallback",
        current_from_dxf=False,
        note="Can come from source geometry only if the import pipeline has real Z data; current 2D flow uses template default Z.",
    ),
    "reserved_ar": WB1FieldSourceInfo(
        field_name="reserved_ar",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Reserved/unknown slot; keep template-controlled.",
    ),
    "contact_surface_position": WB1FieldSourceInfo(
        field_name="contact_surface_position",
        dxf_availability="no",
        current_source="role template default",
        current_from_dxf=False,
        note="Process-specific contact setting from recipe.",
    ),
    "bond_angle": WB1FieldSourceInfo(
        field_name="bond_angle",
        dxf_availability="derived",
        current_source="shared template default / optional wire_vector mode",
        current_from_dxf=False,
        note="The exporter can optionally write a wire-vector-plus-90 heuristic, but RX2000 default templates still keep bond angle template-driven until machine validation confirms the rule.",
    ),
    "climb_angle": WB1FieldSourceInfo(
        field_name="climb_angle",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine motion parameter from recipe.",
    ),
    "start_pressure": WB1FieldSourceInfo(
        field_name="start_pressure",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Bond force recipe parameter.",
    ),
    "end_pressure": WB1FieldSourceInfo(
        field_name="end_pressure",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Bond force recipe parameter.",
    ),
    "us_time_l": WB1FieldSourceInfo(
        field_name="us_time_l",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Secondary ultrasonic time; process-driven.",
    ),
    "search_load": WB1FieldSourceInfo(
        field_name="search_load",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Search/load parameter from recipe.",
    ),
    "descent_amount": WB1FieldSourceInfo(
        field_name="descent_amount",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Recipe-specific descent parameter.",
    ),
    "pull_angle": WB1FieldSourceInfo(
        field_name="pull_angle",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine pull angle is recipe-driven in the current model.",
    ),
    "cut_correction": WB1FieldSourceInfo(
        field_name="cut_correction",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine correction parameter.",
    ),
    "loop_correction": WB1FieldSourceInfo(
        field_name="loop_correction",
        dxf_availability="no",
        current_source="shared template default",
        current_from_dxf=False,
        note="Machine correction parameter.",
    ),
}


def rx2000_fields_available_from_dxf() -> tuple[str, ...]:
    """Return RX2000 J fields that are at least theoretically available from DXF geometry."""

    ordered = sorted(RX2000_STARTER_WB1_FIELD_MAP.items(), key=lambda item: item[1])
    return tuple(
        field_name
        for field_name, _ in ordered
        if RX2000_WB1_FIELD_SOURCES[field_name].dxf_availability != "no"
    )


def rx2000_fields_currently_written_from_dxf() -> tuple[str, ...]:
    """Return RX2000 J fields currently populated from geometry/order data, not templates."""

    ordered = sorted(RX2000_STARTER_WB1_FIELD_MAP.items(), key=lambda item: item[1])
    return tuple(
        field_name
        for field_name, _ in ordered
        if RX2000_WB1_FIELD_SOURCES[field_name].current_from_dxf
    )


def build_wb1_write_plan(template: WireRecipeTemplate) -> tuple[WB1WritePlanItem, ...]:
    """Return a structured list of WB1 locations the exporter currently touches."""

    plan: list[WB1WritePlanItem] = [
        WB1WritePlanItem(
            segment="PRE",
            location="line0:filename",
            field_name="file_name_header",
            index=None,
            categories=("output_name",),
            writes_from_dxf=False,
            detail="Rewrites the machine header filename token from the chosen export file name.",
        )
    ]

    for key in sorted(template.header_defaults):
        plan.append(
            WB1WritePlanItem(
                segment=key.split(":", 1)[0].upper(),
                location=key,
                field_name="header_word",
                index=None,
                categories=("template_header",),
                writes_from_dxf=False,
                detail="Template-driven header word override.",
            )
        )

    role_fields: set[str] = set()
    for values in template.role_record_defaults.values():
        role_fields.update(values)

    reverse_field_map = {index: field_name for field_name, index in template.wb1_field_map.items()}
    for index in sorted(reverse_field_map):
        field_name = reverse_field_map[index]
        categories = _j_field_write_categories(template, field_name, index, role_fields)
        source_info = RX2000_WB1_FIELD_SOURCES.get(field_name)
        writes_from_dxf = any(
            category in {"dynamic_geometry", "dynamic_ordering"} for category in categories
        )
        if source_info is not None:
            detail = source_info.note
        elif "prototype_copy" in categories:
            detail = "Falls back to the prototype J row copied from the WB1 template."
        else:
            detail = "Current source depends on the template configuration for this field."
        plan.append(
            WB1WritePlanItem(
                segment="J",
                location=f"J:{index}",
                field_name=field_name,
                index=index,
                categories=categories,
                writes_from_dxf=writes_from_dxf,
                detail=detail,
            )
        )

    for index in sorted(template.wb1_record_defaults):
        if index in reverse_field_map:
            continue
        plan.append(
            WB1WritePlanItem(
                segment="J",
                location=f"J:{index}",
                field_name=f"word_{index}",
                index=index,
                categories=("template_raw_index",),
                writes_from_dxf=False,
                detail="Raw WB1 word override by index.",
            )
        )

    return tuple(plan)


def current_j_segment_write_plan(template: WireRecipeTemplate) -> tuple[WB1WritePlanItem, ...]:
    """Return only the J-segment part of the current write plan."""

    return tuple(item for item in build_wb1_write_plan(template) if item.segment == "J")


def current_j_segment_dxf_fields(template: WireRecipeTemplate) -> tuple[WB1WritePlanItem, ...]:
    """Return only J-segment fields currently derived from geometry or ordering."""

    return tuple(item for item in current_j_segment_write_plan(template) if item.writes_from_dxf)


def _j_field_write_categories(
    template: WireRecipeTemplate,
    field_name: str,
    index: int,
    role_fields: set[str],
) -> tuple[WB1WriteCategory, ...]:
    categories: list[WB1WriteCategory] = []
    if index in template.wb1_record_defaults:
        categories.append("template_raw_index")
    if field_name in template.record_defaults:
        categories.append("template_shared")
    if field_name in role_fields:
        categories.append("template_role")
    if field_name in {"role_code", "group_no"}:
        categories.append("dynamic_ordering")
    if field_name in {"wire_seq", "point_seq"}:
        categories.append("dynamic_ordering")
    if field_name in {"bond_x", "bond_y", "bond_z"}:
        categories.append("dynamic_geometry")
    if field_name == "bond_angle" and template.bond_angle_mode == "wire_vector":
        categories.append("dynamic_geometry")
    if field_name in {"camera_x", "camera_y", "camera_z"}:
        categories.append("hardcoded_zero")
    if not categories:
        categories.append("prototype_copy")
    return tuple(categories)


__all__ = [
    "DxfAvailability",
    "RX2000_WB1_FIELD_SOURCES",
    "WB1WriteCategory",
    "WB1FieldSourceInfo",
    "WB1WritePlanItem",
    "build_wb1_write_plan",
    "current_j_segment_dxf_fields",
    "current_j_segment_write_plan",
    "rx2000_fields_available_from_dxf",
    "rx2000_fields_currently_written_from_dxf",
]
