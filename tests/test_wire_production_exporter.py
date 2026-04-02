from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from core.export import WireProductionExporter
from core.export.wire_models import WireGeometry, WireOrderingConfig, WirePoint
from core.export.wire_recipe_models import WireRecipeTemplate


def test_wire_production_exporter_writes_both_outputs(tmp_path):
    wb1_template = tmp_path / "template.WB1"
    wb1_template.write_text(
        "\n".join(
            [
                "0000,544553542E5742310000,",
                "J,",
                "0000,0000,0000,0000,0000,",
                "0002,0000,0000,0000,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )
    xlsm_template = tmp_path / "template.xlsm"
    _build_minimal_xlsm_template(xlsm_template)

    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_template_path=str(wb1_template),
        xlsm_template_path=str(xlsm_template),
        coord_scale=10.0,
        ordering=WireOrderingConfig(primary_axis="x", group_no=3),
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "bond_x": 2,
            "bond_y": 3,
            "group_no": 4,
        },
    )
    wires = [
        _wire_geometry("W0002", (5.0, 0.0), (6.0, 0.0)),
        _wire_geometry("W0001", (1.0, 2.0), (3.0, 4.0)),
    ]

    result = WireProductionExporter().export_bundle(
        wires,
        template,
        tmp_path / "output",
        base_name="PART001",
    )

    assert result.wb1_path == tmp_path / "output" / "PART001.WB1"
    assert result.xlsm_path == tmp_path / "output" / "PART001.xlsm"
    assert [record.wire_id for record in result.ordered_records] == ["W0001", "W0002"]
    assert result.wb1_path.read_text(encoding="utf-8").splitlines()[2] == "0000,0001,000A,0014,0003,"

    with ZipFile(result.xlsm_path) as archive:
        assert "xl/worksheets/sheet2.xml" in archive.namelist()


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
