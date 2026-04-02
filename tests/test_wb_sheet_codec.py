from __future__ import annotations

import xml.etree.ElementTree as ET

from core.export.wb_sheet_codec import (
    parse_wb1_content_to_rows,
    render_wb1_rows,
    split_wb1_line_tokens,
    token_is_querytable_numeric,
    worksheet_to_wb_rows,
)

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def test_split_wb1_line_tokens_preserves_interior_empty_fields():
    tokens = split_wb1_line_tokens("0000,,000A,0014,")

    assert tokens == ["0000", "", "000A", "0014"]


def test_parse_and_render_wb1_rows_round_trip_with_empty_fields():
    wb1_content = "\n".join(
        [
            "0000,FILE0000,",
            "0000,,000A,0014,",
            "J,",
        ]
    )

    rows = parse_wb1_content_to_rows(wb1_content)

    assert rows == [
        ["0000", "FILE0000"],
        ["0000", "", "000A", "0014"],
        ["J"],
    ]
    assert render_wb1_rows(rows) == wb1_content


def test_parse_wb1_content_ignores_terminal_dos_eof_marker():
    wb1_content = "0000,FILE0000,\nJ,\n\x1a\n"

    rows = parse_wb1_content_to_rows(wb1_content)

    assert rows == [["0000", "FILE0000"], ["J"]]


def test_worksheet_to_wb_rows_reconstructs_empty_columns():
    worksheet = ET.fromstring(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="{MAIN_NS}">
  <sheetData>
    <row r="4">
      <c r="A4"><v>0</v></c>
      <c r="C4" t="inlineStr"><is><t>000A</t></is></c>
      <c r="D4"><v>14</v></c>
    </row>
    <row r="5">
      <c r="A5" t="inlineStr"><is><t>J</t></is></c>
    </row>
  </sheetData>
</worksheet>
"""
    )

    assert worksheet_to_wb_rows(worksheet) == [["0", "", "000A", "14"], ["J"]]


def test_token_is_querytable_numeric_matches_text_import_behavior():
    assert token_is_querytable_numeric("0000") is True
    assert token_is_querytable_numeric("0014") is True
    assert token_is_querytable_numeric("000A") is False
    assert token_is_querytable_numeric("J") is False
