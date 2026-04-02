from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from core.export.wb1_parser import WB1Parser
from core.export.wire_recipe_models import WireRecipeTemplate


def test_wb1_parser_parses_raw_wb1_text_into_structured_j_records():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "group_no": 2,
            "bond_x": 3,
            "bond_y": 4,
            "bond_z": 5,
        },
        wb1_role_codes={"first": 0, "second": 2},
    )
    wb1_content = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "0004,0001,002D,0016,",
            "G,",
            "0002,0032,",
            "H,",
            "0000,0064,",
            "I,",
            "0001,0000,",
            "J,",
            "0000,0001,0002,000A,000F,001E,",
            "0002,0001,0002,000C,001F,002A,",
            "Q",
        ]
    )

    document = WB1Parser().parse_text(wb1_content, template)

    assert document.source == "wb1"
    assert document.preamble_rows == (
        ("0000", "44454D4F2E5742310000"),
        ("0004", "0001", "002D", "0016"),
    )
    assert tuple(document.sections) == ("G", "H", "I", "J", "Q")
    assert len(document.j_records) == 2

    first = document.j_records[0]
    assert first.role == "first"
    assert first.role_code == 0
    assert first.field_tokens["bond_x"] == "000A"
    assert first.field_values["wire_seq"] == 1
    assert first.field_values["group_no"] == 2
    assert first.field_values["bond_x"] == 10
    assert first.field_values["bond_y"] == 15
    assert first.field_values["bond_z"] == 30

    second = document.j_records[1]
    assert second.role == "second"
    assert second.role_code == 2
    assert second.field_values["bond_x"] == 12
    assert second.field_values["bond_y"] == 31
    assert second.field_values["bond_z"] == 42


def test_wb1_parser_reads_wb_sheet_from_xlsm(tmp_path):
    template_path = tmp_path / "template.xlsm"
    _build_xlsm_template_with_wb_sheet(template_path)
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        xlsm_template_path=str(template_path),
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "group_no": 2,
            "bond_x": 3,
            "bond_y": 4,
            "bond_z": 5,
        },
        wb1_role_codes={"first": 0, "second": 2},
    )

    document = WB1Parser().parse_xlsm_wb_sheet(template_path, template)

    assert document.source == "worksheet"
    assert document.preamble_rows == (
        ("0", "44454D4F2E5742310000"),
        ("4", "1", "002D", "16"),
    )
    assert len(document.j_records) == 2

    first = document.j_records[0]
    assert first.role == "first"
    assert first.field_tokens["bond_x"] == "000A"
    assert first.field_values["wire_seq"] == 1
    assert first.field_values["group_no"] == 2
    assert first.field_values["bond_x"] == 10
    assert first.field_values["bond_y"] == 15
    assert first.field_values["bond_z"] == 30

    second = document.j_records[1]
    assert second.role == "second"
    assert second.field_tokens["bond_z"] == "002A"
    assert second.field_values["bond_x"] == 12
    assert second.field_values["bond_y"] == 31
    assert second.field_values["bond_z"] == 42


def _build_xlsm_template_with_wb_sheet(path: Path) -> None:
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Base" sheetId="1" r:id="rId1"/>
    <sheet name="WB" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>
"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.microsoft.com/office/2006/relationships/vbaProject" Target="vbaProject.bin"/>
</Relationships>
"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""
    sheet1_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData/>
</worksheet>
"""
    sheet2_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A2:F14"/>
  <sheetData>
    <row r="2"><c r="A2" t="inlineStr"><is><t>keep-header</t></is></c></row>
    <row r="4"><c r="A4"><v>0</v></c><c r="B4" t="inlineStr"><is><t>44454D4F2E5742310000</t></is></c></row>
    <row r="5"><c r="A5"><v>4</v></c><c r="B5"><v>1</v></c><c r="C5" t="inlineStr"><is><t>002D</t></is></c><c r="D5"><v>16</v></c></row>
    <row r="6"><c r="A6" t="inlineStr"><is><t>G</t></is></c></row>
    <row r="7"><c r="A7"><v>2</v></c><c r="B7"><v>32</v></c></row>
    <row r="8"><c r="A8" t="inlineStr"><is><t>H</t></is></c></row>
    <row r="9"><c r="A9"><v>0</v></c><c r="B9"><v>64</v></c></row>
    <row r="10"><c r="A10" t="inlineStr"><is><t>I</t></is></c></row>
    <row r="11"><c r="A11"><v>1</v></c><c r="B11"><v>0</v></c></row>
    <row r="12"><c r="A12" t="inlineStr"><is><t>J</t></is></c></row>
    <row r="13">
      <c r="A13"><v>0</v></c>
      <c r="B13"><v>1</v></c>
      <c r="C13"><v>2</v></c>
      <c r="D13" t="inlineStr"><is><t>000A</t></is></c>
      <c r="E13" t="inlineStr"><is><t>000F</t></is></c>
      <c r="F13" t="inlineStr"><is><t>001E</t></is></c>
    </row>
    <row r="14">
      <c r="A14"><v>2</v></c>
      <c r="B14"><v>1</v></c>
      <c r="C14"><v>2</v></c>
      <c r="D14" t="inlineStr"><is><t>000C</t></is></c>
      <c r="E14" t="inlineStr"><is><t>001F</t></is></c>
      <c r="F14" t="inlineStr"><is><t>002A</t></is></c>
    </row>
    <row r="15"><c r="A15" t="inlineStr"><is><t>Q</t></is></c></row>
  </sheetData>
</worksheet>
"""
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
        archive.writestr("xl/worksheets/sheet2.xml", sheet2_xml)
        archive.writestr("xl/vbaProject.bin", b"macro-data")
