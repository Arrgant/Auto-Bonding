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
