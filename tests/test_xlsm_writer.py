from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from core.export.wire_models import OrderedWireRecord, WireGeometry, WirePoint
from core.export.wire_recipe_models import WireRecipeTemplate
from core.export.xlsm_writer import XLSMWriter

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def test_xlsm_writer_appends_coordinate_sheet_without_removing_macros(tmp_path):
    template_path = tmp_path / "template.xlsm"
    _build_minimal_xlsm_template(template_path)

    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        xlsm_template_path=str(template_path),
    )
    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0001",
            wire_seq=1,
            group_no=2,
            first_point_seq=1,
            second_point_seq=2,
            geometry=_wire_geometry("W0001", (1.0, 2.0), (3.5, 4.5)),
        )
    ]

    output_path = tmp_path / "out.xlsm"
    XLSMWriter().write(ordered_wires, template, output_path)

    with ZipFile(output_path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        content_types = ET.fromstring(archive.read("[Content_Types].xml"))
        sheet_xml = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
        vba_project = archive.read("xl/vbaProject.bin")

    ns = {"main": MAIN_NS, "rel": DOC_REL_NS, "pkg": "http://schemas.openxmlformats.org/package/2006/content-types"}
    sheets = workbook.find("main:sheets", ns)
    assert sheets is not None
    sheet_names = [sheet.attrib["name"] for sheet in sheets]
    assert sheet_names == ["Base", "AUTO_WIRE_EXPORT"]

    relation_targets = [rel.attrib["Target"] for rel in workbook_rels]
    assert "worksheets/sheet2.xml" in relation_targets

    overrides = [node.attrib["PartName"] for node in content_types.findall("pkg:Override", ns)]
    assert "/xl/worksheets/sheet2.xml" in overrides

    rows = sheet_xml.find(f"{{{MAIN_NS}}}sheetData")
    assert rows is not None
    assert len(rows.findall(f"{{{MAIN_NS}}}row")) == 2
    assert vba_project == b"macro-data"


def test_xlsm_writer_populates_existing_wb_sheet_when_wb1_template_is_available(tmp_path):
    template_path = tmp_path / "template-with-wb.xlsm"
    _build_xlsm_template_with_wb_sheet(template_path)
    wb1_template_path = tmp_path / "template.WB1"
    wb1_template_path.write_text(
        "\n".join(
            [
                "0000,54454D504C4154452E5742310000,",
                "J,",
                "0000,0000,0000,0000,",
                "0002,0000,0000,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        xlsm_template_path=str(template_path),
        wb1_template_path=str(wb1_template_path),
        coord_scale=10.0,
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "bond_x": 2,
            "bond_y": 3,
        },
    )
    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0001",
            wire_seq=1,
            group_no=2,
            first_point_seq=1,
            second_point_seq=2,
            geometry=_wire_geometry("W0001", (1.0, 2.0), (3.5, 4.5)),
        )
    ]

    output_path = tmp_path / "out.xlsm"
    XLSMWriter().write(ordered_wires, template, output_path)

    with ZipFile(output_path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        wb_target = _find_sheet_target(workbook, workbook_rels, "WB")
        export_target = _find_sheet_target(workbook, workbook_rels, "AUTO_WIRE_EXPORT")
        assert wb_target is not None
        assert export_target is not None
        wb_sheet = ET.fromstring(archive.read(wb_target))
        rows = wb_sheet.find(f"{{{MAIN_NS}}}sheetData")
        assert rows is not None
        wb_values = _sheet_values(rows)
        dimension = wb_sheet.find(f"{{{MAIN_NS}}}dimension")

    assert wb_values["A2"] == "keep-header"
    assert wb_values["A4"] == "0000"
    assert wb_values["B4"] == "6F75742E5742310000"
    assert wb_values["A5"] == "J"
    assert wb_values["A6"] == "0000"
    assert wb_values["B6"] == "0001"
    assert wb_values["C6"] == "000A"
    assert wb_values["D6"] == "0014"
    assert wb_values["A7"] == "0002"
    assert wb_values["B7"] == "0001"
    assert wb_values["C7"] == "0023"
    assert wb_values["D7"] == "002D"
    assert wb_values["A8"] == "Q"
    assert dimension is not None and dimension.attrib["ref"] == "A2:D8"


def test_xlsm_writer_applies_pfile_cell_overrides_when_sheet_exists(tmp_path):
    template_path = tmp_path / "template-with-pfile.xlsm"
    _build_xlsm_template_with_pfile_sheet(template_path)

    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        xlsm_template_path=str(template_path),
        pfile_field_map={"search_force": "A4", "wait_time": "B4", "wire_mode": "C13"},
        pfile_named_defaults={"search_force": 25, "wait_time": 100, "wire_mode": "AUTO"},
        pfile_cell_overrides={"B4": 9999, "AF12": 100, "C13": "MODE"},
    )
    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0001",
            wire_seq=1,
            group_no=2,
            first_point_seq=1,
            second_point_seq=2,
            geometry=_wire_geometry("W0001", (1.0, 2.0), (3.5, 4.5)),
        )
    ]

    output_path = tmp_path / "out-pfile.xlsm"
    XLSMWriter().write(ordered_wires, template, output_path)

    with ZipFile(output_path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        pfile_target = _find_sheet_target(workbook, workbook_rels, "PFILE")
        assert pfile_target is not None
        pfile_sheet = ET.fromstring(archive.read(pfile_target))
        rows = pfile_sheet.find(f"{{{MAIN_NS}}}sheetData")
        assert rows is not None
        values = _sheet_values(rows)
        dimension = pfile_sheet.find(f"{{{MAIN_NS}}}dimension")

    assert values["A2"] == "pfile-header"
    assert values["A4"] == "25"
    assert values["B4"] == "9999"
    assert values["AF12"] == "100"
    assert values["C13"] == "MODE"
    assert dimension is not None and dimension.attrib["ref"] == "A2:AF13"


def _build_minimal_xlsm_template(path: Path) -> None:
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Base" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.microsoft.com/office/2006/relationships/vbaProject" Target="vbaProject.bin"/>
</Relationships>
"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""
    sheet1_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData/>
</worksheet>
"""
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
        archive.writestr("xl/vbaProject.bin", b"macro-data")


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
  <dimension ref="A2:B4"/>
  <sheetData>
    <row r="2"><c r="A2" t="inlineStr"><is><t>keep-header</t></is></c></row>
    <row r="3"><c r="A3" t="inlineStr"><is><t>keep-meta</t></is></c></row>
    <row r="4"><c r="A4" t="inlineStr"><is><t>old</t></is></c></row>
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


def _build_xlsm_template_with_pfile_sheet(path: Path) -> None:
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Base" sheetId="1" r:id="rId1"/>
    <sheet name="PFILE" sheetId="2" r:id="rId2"/>
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
  <dimension ref="A2:B4"/>
  <sheetData>
    <row r="2"><c r="A2" t="inlineStr"><is><t>pfile-header</t></is></c></row>
    <row r="4"><c r="A4"><v>0</v></c><c r="B4"><v>0</v></c></row>
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


def _find_sheet_target(workbook: ET.Element, workbook_rels: ET.Element, sheet_name: str) -> str | None:
    sheets = workbook.find(f"{{{MAIN_NS}}}sheets")
    if sheets is None:
        return None
    relation_id = None
    for sheet in sheets:
        if sheet.attrib.get("name") == sheet_name:
            relation_id = sheet.attrib.get(f"{{{DOC_REL_NS}}}id")
            break
    if relation_id is None:
        return None
    for rel in workbook_rels:
        if rel.attrib.get("Id") == relation_id:
            return f"xl/{rel.attrib['Target']}"
    return None


def _sheet_values(rows: ET.Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in rows.findall(f"{{{MAIN_NS}}}row"):
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            ref = cell.attrib["r"]
            text_node = cell.find(f".//{{{MAIN_NS}}}t")
            if text_node is not None:
                values[ref] = text_node.text or ""
                continue
            value_node = cell.find(f"{{{MAIN_NS}}}v")
            if value_node is not None:
                values[ref] = value_node.text or ""
    return values


def _wire_geometry(wire_id: str, first_xy: tuple[float, float], second_xy: tuple[float, float]) -> WireGeometry:
    first_point = WirePoint(point_id=f"{wire_id}-P1", wire_id=wire_id, role="first", x=first_xy[0], y=first_xy[1])
    second_point = WirePoint(
        point_id=f"{wire_id}-P2",
        wire_id=wire_id,
        role="second",
        x=second_xy[0],
        y=second_xy[1],
    )
    return WireGeometry(
        wire_id=wire_id,
        layer_name="06_wire",
        source_type="LINE",
        source_entity_indices=(0,),
        route_points=(first_xy, second_xy),
        first_point=first_point,
        second_point=second_point,
        length=1.0,
        angle_deg=0.0,
        bbox=(min(first_xy[0], second_xy[0]), min(first_xy[1], second_xy[1]), max(first_xy[0], second_xy[0]), max(first_xy[1], second_xy[1])),
    )
