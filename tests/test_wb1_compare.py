from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from core.export.wb1_compare import WB1Comparer
from core.export.xlsm_writer import XLSMWriter
from core.export.wire_recipe_models import WireRecipeTemplate


def test_wb1_comparer_reports_header_and_named_j_field_differences():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "group_no": 2,
            "bond_x": 3,
            "bond_y": 4,
        },
        wb1_role_codes={"first": 0, "second": 2},
    )
    expected_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "0004,0001,002D,0016,",
            "G,",
            "0002,0032,",
            "J,",
            "0000,0001,0002,000A,000F,",
            "Q",
        ]
    )
    actual_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "0004,0001,002E,0016,",
            "G,",
            "0002,0032,",
            "J,",
            "0000,0001,0003,000C,000F,",
            "Q",
        ]
    )

    result = WB1Comparer().compare_texts(expected_wb1, actual_wb1, template)

    assert result.has_differences is True
    assert result.expected_source == "wb1"
    assert result.actual_source == "wb1"
    assert _difference_signature(result.differences) == {
        ("header", "PRE:1:2", "word_2", "002D", "002E"),
        ("j_record", "J:1:2", "group_no", "0002", "0003"),
        ("j_record", "J:1:3", "bond_x", "000A", "000C"),
    }


def test_wb1_comparer_reports_missing_or_extra_j_records():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={"role_code": 0, "wire_seq": 1},
        wb1_role_codes={"first": 0, "second": 2},
    )
    expected_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "J,",
            "0000,0001,",
            "0002,0001,",
            "Q",
        ]
    )
    actual_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "J,",
            "0000,0001,",
            "Q",
        ]
    )

    result = WB1Comparer().compare_texts(expected_wb1, actual_wb1, template)

    assert result.has_differences is True
    assert _difference_signature(result.differences) == {
        ("j_record", "J:2", "record_presence", "present", ""),
    }


def test_wb1_comparer_returns_clean_result_for_identical_documents():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={"role_code": 0, "wire_seq": 1, "bond_x": 2},
        wb1_role_codes={"first": 0, "second": 2},
    )
    wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "J,",
            "0000,0001,000A,",
            "Q",
        ]
    )

    result = WB1Comparer().compare_texts(wb1, wb1, template)

    assert result.has_differences is False
    assert result.difference_count == 0
    assert result.differences == ()


def test_wb1_comparer_can_compare_xlsm_wb_sheets(tmp_path):
    template_path = tmp_path / "template.xlsm"
    _build_xlsm_template_with_wb_sheet(template_path)
    wb1_path = tmp_path / "source.WB1"
    wb1_path.write_text(
        "\n".join(
            [
                "0000,44454D4F2E5742310000,",
                "J,",
                "0000,0001,0002,000A,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        xlsm_template_path=str(template_path),
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "group_no": 2,
            "bond_x": 3,
        },
        wb1_role_codes={"first": 0, "second": 2},
    )

    generated_xlsm_path = tmp_path / "generated.xlsm"
    XLSMWriter().write_wb1_import(wb1_path, template, generated_xlsm_path)

    result = WB1Comparer().compare_xlsm_wb_sheets(template_path, generated_xlsm_path, template)

    assert result.has_differences is True
    assert _difference_signature(result.differences) == {
        ("header", "PRE:0:0", "word_0", "", "0"),
        ("header", "PRE:0:1", "word_1", "", "44454D4F2E5742310000"),
        ("j_record", "J:1", "record_presence", "", "present"),
    }


def _difference_signature(differences):
    return {
        (difference.scope, difference.location, difference.field_name, difference.expected, difference.actual)
        for difference in differences
    }


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
  <dimension ref="A2:A4"/>
  <sheetData>
    <row r="2"><c r="A2" t="inlineStr"><is><t>old</t></is></c></row>
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
