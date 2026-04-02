"""Template-driven WB1 writer for wire production files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .wire_models import OrderedWireRecord, WirePoint
from .wire_recipe_models import WB1RecordOverrideValue, WireRecipeTemplate

SECTION_MARKERS = {"G,", "H,", "I,", "J,", "Q"}


class WB1Writer:
    """Write WB1 content by cloning a sample template and replacing J records."""

    def render(
        self,
        ordered_wires: Iterable[OrderedWireRecord],
        template: WireRecipeTemplate,
        *,
        output_name: str,
    ) -> str:
        """Render WB1 text using one saved template definition."""

        template_path = _require_template_path(template)
        lines = template_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not lines:
            raise ValueError("WB1 template file is empty.")

        section_start, section_end = _find_j_section(lines)
        first_prototype, second_prototype = _resolve_record_prototypes(lines, section_start, section_end, template)
        generated_records = self._build_j_records(
            ordered_wires,
            template,
            first_prototype=first_prototype,
            second_prototype=second_prototype,
        )

        _apply_header_defaults(lines, template.header_defaults)
        lines[0] = _replace_filename_header(lines[0], output_name)
        updated_lines = lines[: section_start + 1] + generated_records + lines[section_end:]
        return "\n".join(updated_lines) + "\n"

    def write(
        self,
        ordered_wires: Iterable[OrderedWireRecord],
        template: WireRecipeTemplate,
        output_path: str | Path,
        *,
        output_name: str | None = None,
    ) -> Path:
        """Render and write one WB1 file to disk."""

        target_path = Path(output_path)
        resolved_name = output_name or target_path.name
        content = self.render(ordered_wires, template, output_name=resolved_name)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return target_path

    def _build_j_records(
        self,
        ordered_wires: Iterable[OrderedWireRecord],
        template: WireRecipeTemplate,
        *,
        first_prototype: list[str],
        second_prototype: list[str],
    ) -> list[str]:
        lines: list[str] = []
        for record in ordered_wires:
            lines.append(
                self._format_record(
                    list(first_prototype),
                    template,
                    ordered_record=record,
                    point=record.geometry.first_point,
                    point_seq=record.first_point_seq,
                    role="first",
                )
            )
            lines.append(
                self._format_record(
                    list(second_prototype),
                    template,
                    ordered_record=record,
                    point=record.geometry.second_point,
                    point_seq=record.second_point_seq,
                    role="second",
                )
            )
        return lines

    def _format_record(
        self,
        fields: list[str],
        template: WireRecipeTemplate,
        *,
        ordered_record: OrderedWireRecord,
        point: WirePoint,
        point_seq: int,
        role: str,
    ) -> str:
        field_map = dict(template.wb1_field_map)
        fields = _ensure_record_capacity(fields, field_map, template.wb1_record_defaults)

        for index, value in template.wb1_record_defaults.items():
            fields[index] = _encode_override_value(value)
        for field_name, value in template.record_defaults.items():
            _set_field(fields, field_map, field_name, value)
        for field_name, value in template.role_record_defaults.get(role, {}).items():
            _set_field(fields, field_map, field_name, value)

        _set_field(fields, field_map, "role_code", template.wb1_role_codes.get(role, 0))
        _set_field(fields, field_map, "wire_seq", ordered_record.wire_seq)
        _set_field(fields, field_map, "group_no", ordered_record.group_no)
        _set_field(fields, field_map, "point_seq", point_seq)
        _set_field(fields, field_map, "bond_x", _scaled_coord(point.x, template.coord_scale))
        _set_field(fields, field_map, "bond_y", _scaled_coord(point.y, template.coord_scale))
        _set_field(fields, field_map, "bond_z", _scaled_coord(point.z or template.default_z, template.coord_scale))
        if template.bond_angle_mode == "wire_vector":
            _set_field(fields, field_map, "bond_angle", _wire_vector_angle_word(ordered_record))
        _set_field(fields, field_map, "camera_x", 0)
        _set_field(fields, field_map, "camera_y", 0)
        _set_field(fields, field_map, "camera_z", 0)
        return ",".join(fields) + ","


def _require_template_path(template: WireRecipeTemplate) -> Path:
    if not template.wb1_template_path:
        raise ValueError("WB1 template path is not configured.")
    path = Path(template.wb1_template_path)
    if not path.exists():
        raise FileNotFoundError(f"WB1 template not found: {path}")
    return path


def _find_j_section(lines: list[str]) -> tuple[int, int]:
    try:
        start = lines.index("J,")
    except ValueError as exc:
        raise ValueError("WB1 template is missing the J section marker.") from exc

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index] in SECTION_MARKERS:
            end = index
            break
    return start, end


def _resolve_record_prototypes(
    lines: list[str],
    section_start: int,
    section_end: int,
    template: WireRecipeTemplate,
) -> tuple[list[str], list[str]]:
    record_lines = [line for line in lines[section_start + 1 : section_end] if line.strip()]
    if record_lines:
        first_tokens = _split_record_tokens(record_lines[0])
        second_tokens = _split_record_tokens(record_lines[1]) if len(record_lines) > 1 else list(first_tokens)
        return first_tokens, second_tokens

    inferred_length = _infer_record_length(template)
    zeros = ["0000"] * inferred_length
    return list(zeros), list(zeros)


def _infer_record_length(template: WireRecipeTemplate) -> int:
    highest = -1
    if template.wb1_field_map:
        highest = max(highest, max(template.wb1_field_map.values()))
    if template.wb1_record_defaults:
        highest = max(highest, max(template.wb1_record_defaults))
    return max(highest + 1, 8)


def _split_record_tokens(line: str) -> list[str]:
    return [token for token in line.split(",") if token]


def _replace_filename_header(line: str, output_name: str) -> str:
    tokens = [token for token in line.split(",") if token]
    if len(tokens) < 2 or tokens[0] != "0000":
        return line
    filename_hex = output_name.encode("ascii", errors="ignore").hex().upper() + "0000"
    return f"{tokens[0]},{filename_hex},"


def _ensure_record_capacity(
    fields: list[str],
    field_map: dict[str, int],
    record_defaults: dict[int, WB1RecordOverrideValue],
) -> list[str]:
    highest = max([len(fields) - 1, *field_map.values(), *record_defaults.keys()], default=len(fields) - 1)
    if len(fields) <= highest:
        fields.extend(["0000"] * (highest + 1 - len(fields)))
    return fields


def _apply_header_defaults(lines: list[str], header_defaults: dict[str, object]) -> None:
    if not header_defaults:
        return
    sections = _find_sections(lines)
    for key, value in header_defaults.items():
        location = _parse_header_location(key)
        if location is None:
            continue
        line_index = _resolve_header_line_index(lines, sections, location)
        if line_index is None:
            continue
        lines[line_index] = _apply_word_override(lines[line_index], location.word_index, value)


def _find_sections(lines: list[str]) -> dict[str, int]:
    return {line.rstrip(","): index for index, line in enumerate(lines) if line in SECTION_MARKERS}


def _parse_header_location(key: object) -> _HeaderLocation | None:
    if not isinstance(key, str):
        return None
    parts = key.split(":")
    if len(parts) != 3:
        return None
    section_name = parts[0].strip().upper()
    if section_name == "PREAMBLE":
        section_name = "PRE"
    try:
        line_offset = int(parts[1])
        word_index = int(parts[2])
    except ValueError:
        return None
    if line_offset < 0 or word_index < 0:
        return None
    return _HeaderLocation(section_name=section_name, line_offset=line_offset, word_index=word_index)


def _resolve_header_line_index(
    lines: list[str],
    sections: dict[str, int],
    location: _HeaderLocation,
) -> int | None:
    if location.section_name == "PRE":
        if location.line_offset >= len(lines):
            return None
        section_floor = min(sections.values(), default=len(lines))
        if location.line_offset >= section_floor:
            return None
        return location.line_offset

    section_start = sections.get(location.section_name)
    if section_start is None:
        return None
    next_markers = [index for name, index in sections.items() if index > section_start]
    section_end = min(next_markers, default=len(lines))
    target_index = section_start + 1 + location.line_offset
    if target_index >= section_end:
        return None
    return target_index


def _apply_word_override(line: str, word_index: int, value: object) -> str:
    fields = _split_record_tokens(line)
    if word_index >= len(fields):
        fields.extend(["0000"] * (word_index + 1 - len(fields)))
    fields[word_index] = _encode_override_value(value)
    return ",".join(fields) + ","


def _set_field(
    fields: list[str],
    field_map: dict[str, int],
    field_name: str,
    value: object,
) -> None:
    index = field_map.get(field_name)
    if index is None:
        return
    fields[index] = _encode_override_value(value)


def _encode_override_value(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if not normalized:
            return "0000"
        return normalized
    if isinstance(value, (bool, int, float)):
        return _encode_hex_word(int(value))
    raise TypeError(f"Unsupported WB1 override value: {value!r}")


def _scaled_coord(value: float, coord_scale: float) -> int:
    return int(round(value * coord_scale))


def _wire_vector_angle_word(record: OrderedWireRecord) -> int:
    return int(round(record.geometry.angle_deg))


def _encode_hex_word(value: int) -> str:
    if value < -32768 or value > 65535:
        raise ValueError(f"WB1 word value out of range: {value}")
    return f"{value & 0xFFFF:04X}"


@dataclass(frozen=True)
class _HeaderLocation:
    section_name: str
    line_offset: int
    word_index: int


__all__ = ["WB1Writer"]
