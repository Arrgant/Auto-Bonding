"""Best-effort parsers for WB1 files and XLSM WB worksheets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from .wb_sheet_codec import parse_wb1_content_to_rows, worksheet_to_wb_rows
from .wire_recipe_models import WB1RecordOverrideValue, WireRecipeTemplate

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SECTION_MARKERS = {"G", "H", "I", "J", "Q"}

WBParseSource = Literal["wb1", "worksheet"]


@dataclass(frozen=True)
class ParsedWB1Record:
    """One parsed J-segment record with named field lookups."""

    record_index: int
    role: str | None
    role_code: int | str | None
    tokens: tuple[str, ...]
    field_tokens: dict[str, str]
    field_values: dict[str, int | str]


@dataclass(frozen=True)
class ParsedWB1Document:
    """Structured view of one WB1-like document."""

    source: WBParseSource
    rows: tuple[tuple[str, ...], ...]
    preamble_rows: tuple[tuple[str, ...], ...]
    sections: dict[str, tuple[tuple[str, ...], ...]]
    j_records: tuple[ParsedWB1Record, ...]


class WB1Parser:
    """Parse WB1 text or XLSM WB worksheets into structured records."""

    def parse_file(self, path: str | Path, template: WireRecipeTemplate) -> ParsedWB1Document:
        """Parse one raw WB1 file from disk."""

        content = Path(path).read_text(encoding="utf-8", errors="ignore")
        return self.parse_text(content, template)

    def parse_text(self, wb1_content: str, template: WireRecipeTemplate) -> ParsedWB1Document:
        """Parse raw WB1 text content."""

        rows = parse_wb1_content_to_rows(wb1_content)
        return self.parse_rows(rows, template, source="wb1")

    def parse_rows(
        self,
        rows: list[list[str]],
        template: WireRecipeTemplate,
        *,
        source: WBParseSource,
    ) -> ParsedWB1Document:
        """Parse already-tokenized WB rows."""

        preamble_rows: list[tuple[str, ...]] = []
        section_rows: dict[str, list[tuple[str, ...]]] = {}
        current_section = "PRE"

        normalized_rows = [tuple(row) for row in rows if row]
        for row in normalized_rows:
            marker = _section_marker(row)
            if marker is not None:
                current_section = marker
                section_rows.setdefault(marker, [])
                continue
            if current_section == "PRE":
                preamble_rows.append(row)
            else:
                section_rows.setdefault(current_section, []).append(row)

        j_records = tuple(
            _parse_j_record(index, tokens, template, source=source)
            for index, tokens in enumerate(section_rows.get("J", []), start=1)
        )
        return ParsedWB1Document(
            source=source,
            rows=tuple(normalized_rows),
            preamble_rows=tuple(preamble_rows),
            sections={name: tuple(values) for name, values in sorted(section_rows.items())},
            j_records=j_records,
        )

    def parse_xlsm_wb_sheet(
        self,
        path: str | Path,
        template: WireRecipeTemplate,
        *,
        start_row: int = 4,
    ) -> ParsedWB1Document:
        """Parse the WB worksheet inside one macro workbook."""

        workbook_path = Path(path)
        with ZipFile(workbook_path, "r") as archive:
            workbook_tree = ET.fromstring(archive.read("xl/workbook.xml"))
            workbook_rels_tree = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            wb_sheet_path = _find_sheet_path(workbook_tree, workbook_rels_tree, "WB")
            if wb_sheet_path is None:
                raise ValueError("Workbook does not contain a WB worksheet.")
            worksheet = ET.fromstring(archive.read(wb_sheet_path))
        rows = worksheet_to_wb_rows(worksheet, start_row=start_row)
        return self.parse_rows(rows, template, source="worksheet")


def _parse_j_record(
    record_index: int,
    tokens: tuple[str, ...],
    template: WireRecipeTemplate,
    *,
    source: WBParseSource,
) -> ParsedWB1Record:
    field_tokens: dict[str, str] = {}
    field_values: dict[str, int | str] = {}
    for field_name, token_index in sorted(template.wb1_field_map.items(), key=lambda item: item[1]):
        if token_index >= len(tokens):
            continue
        token = tokens[token_index]
        field_tokens[field_name] = token
        decoded = _decode_token_value(token, source=source)
        field_values[field_name] = decoded

    role_token = field_tokens.get("role_code", tokens[0] if tokens else "")
    decoded_role = _decode_token_value(role_token, source=source)
    return ParsedWB1Record(
        record_index=record_index,
        role=_resolve_role_name(role_token, decoded_role, template.wb1_role_codes),
        role_code=decoded_role,
        tokens=tokens,
        field_tokens=field_tokens,
        field_values=field_values,
    )


def _section_marker(row: tuple[str, ...]) -> str | None:
    if len(row) != 1:
        return None
    marker = row[0].strip().upper()
    if marker in SECTION_MARKERS:
        return marker
    return None


def _resolve_role_name(
    token: str,
    decoded: int | str,
    role_codes: dict[str, WB1RecordOverrideValue],
) -> str | None:
    normalized_token = token.strip().upper()
    for role_name, expected in role_codes.items():
        if isinstance(expected, int):
            if isinstance(decoded, int) and decoded == expected:
                return role_name
            continue
        expected_token = str(expected).strip().upper()
        if expected_token == normalized_token:
            return role_name
        expected_decoded = _decode_token_value(expected_token, source="wb1")
        if isinstance(decoded, int) and isinstance(expected_decoded, int) and decoded == expected_decoded:
            return role_name
    return None


def _decode_token_value(token: str, *, source: WBParseSource) -> int | str:
    normalized = token.strip().upper()
    if not normalized:
        return ""
    if _looks_like_hex_word(normalized):
        if source == "worksheet" and normalized.isdigit():
            return int(normalized, 10)
        return int(normalized, 16)
    if normalized.isdigit():
        return int(normalized, 10)
    return normalized


def _looks_like_hex_word(token: str) -> bool:
    if len(token) > 4:
        return False
    return all(char in "0123456789ABCDEF" for char in token)


def _find_sheet_path(
    workbook_tree: ET.Element,
    workbook_rels_tree: ET.Element,
    sheet_name: str,
) -> str | None:
    sheets_node = workbook_tree.find(_qn(MAIN_NS, "sheets"))
    if sheets_node is None:
        return None
    for sheet in sheets_node:
        if sheet.attrib.get("name") != sheet_name:
            continue
        relation_id = sheet.attrib.get(_qn(REL_NS, "id"))
        if not relation_id:
            return None
        for relation in workbook_rels_tree:
            if relation.attrib.get("Id") != relation_id:
                continue
            target = relation.attrib.get("Target")
            if not target:
                return None
            return f"xl/{target}"
    return None


def _qn(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


__all__ = ["ParsedWB1Document", "ParsedWB1Record", "WB1Parser"]
