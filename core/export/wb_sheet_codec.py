"""Helpers for converting between WB1 text rows and XLSM WB sheet rows."""

from __future__ import annotations

import xml.etree.ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def parse_wb1_content_to_rows(wb1_content: str) -> list[list[str]]:
    """Return WB1 lines as token rows while preserving interior empty fields."""

    rows: list[list[str]] = []
    for line in wb1_content.splitlines():
        stripped = _sanitize_wb1_line(line.rstrip("\r"))
        if not stripped.strip():
            continue
        rows.append(split_wb1_line_tokens(stripped))
    return rows


def split_wb1_line_tokens(line: str) -> list[str]:
    """Split one WB1 line into tokens without collapsing interior blanks."""

    tokens = line.split(",")
    if tokens and tokens[-1] == "":
        tokens = tokens[:-1]
    return tokens


def render_wb1_rows(rows: list[list[str]]) -> str:
    """Serialize parsed WB rows back into WB1 line format."""

    return "\n".join(",".join(row) + "," for row in rows)


def token_is_querytable_numeric(token: str) -> bool:
    """Return whether Excel text import would treat the token as numeric."""

    return bool(token) and token.isdigit()


def worksheet_to_wb_rows(worksheet: ET.Element, *, start_row: int = 4) -> list[list[str]]:
    """Extract WB token rows from one worksheet XML tree."""

    sheet_data = worksheet.find(_qn("sheetData"))
    if sheet_data is None:
        return []

    rows: list[list[str]] = []
    for row in sheet_data.findall(_qn("row")):
        row_number = int(row.attrib.get("r", "0"))
        if row_number < start_row:
            continue
        cell_map: dict[int, str] = {}
        max_column = 0
        for cell in row.findall(_qn("c")):
            column_index = _column_index_from_ref(cell.attrib.get("r", "A1"))
            max_column = max(max_column, column_index)
            cell_map[column_index] = worksheet_cell_text(cell)
        if max_column == 0:
            continue
        rows.append([cell_map.get(index, "") for index in range(1, max_column + 1)])
    return rows


def worksheet_cell_text(cell: ET.Element) -> str:
    """Return one worksheet cell value as text."""

    inline_text = cell.find(f".//{_qn('t')}")
    if inline_text is not None:
        return inline_text.text or ""
    value_node = cell.find(_qn("v"))
    if value_node is not None:
        return value_node.text or ""
    return ""


def _column_index_from_ref(cell_ref: str) -> int:
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char.upper())
        else:
            break
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return max(index, 1)


def _qn(local_name: str) -> str:
    return f"{{{MAIN_NS}}}{local_name}"


def _sanitize_wb1_line(line: str) -> str:
    return "".join(char for char in line if char == "\t" or ord(char) >= 32)


__all__ = [
    "MAIN_NS",
    "parse_wb1_content_to_rows",
    "render_wb1_rows",
    "split_wb1_line_tokens",
    "token_is_querytable_numeric",
    "worksheet_cell_text",
    "worksheet_to_wb_rows",
]
