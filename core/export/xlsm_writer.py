"""Template-driven XLSM writer for wire coordinate exports."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from .wire_models import OrderedWireRecord
from .wire_recipe_models import WireRecipeTemplate

CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)

COORDINATE_HEADERS = (
    "wire_seq",
    "wire_id",
    "group_no",
    "first_point_seq",
    "second_point_seq",
    "first_x",
    "first_y",
    "first_z",
    "second_x",
    "second_y",
    "second_z",
    "length",
    "angle_deg",
)


class XLSMWriter:
    """Copy one macro-enabled workbook template and append a safe export sheet."""

    def write(
        self,
        ordered_wires: list[OrderedWireRecord],
        template: WireRecipeTemplate,
        output_path: str | Path,
        *,
        sheet_name: str = "AUTO_WIRE_EXPORT",
    ) -> Path:
        """Write one XLSM file containing a dedicated coordinate worksheet."""

        template_path = _require_template_path(template)
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with ZipFile(template_path, "r") as archive:
            workbook_tree = ET.fromstring(archive.read("xl/workbook.xml"))
            workbook_rels_tree = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            content_types_tree = ET.fromstring(archive.read("[Content_Types].xml"))

            sheets_node = workbook_tree.find(_qn(MAIN_NS, "sheets"))
            if sheets_node is None:
                raise ValueError("Workbook is missing the sheets collection.")
            existing_sheet_names = {sheet.attrib.get("name", "") for sheet in sheets_node}
            if sheet_name in existing_sheet_names:
                raise ValueError(f"Workbook template already contains a sheet named {sheet_name!r}.")

            next_sheet_number = _next_sheet_number(workbook_rels_tree)
            next_relation_id = _next_relation_id(workbook_rels_tree)
            next_sheet_id = _next_sheet_id(sheets_node)
            worksheet_path = f"xl/worksheets/sheet{next_sheet_number}.xml"
            worksheet_target = f"worksheets/sheet{next_sheet_number}.xml"

            sheet_element = ET.Element(
                _qn(MAIN_NS, "sheet"),
                {
                    "name": sheet_name,
                    "sheetId": str(next_sheet_id),
                    _qn(REL_NS, "id"): f"rId{next_relation_id}",
                },
            )
            sheets_node.append(sheet_element)

            ET.SubElement(
                workbook_rels_tree,
                _qn(PACKAGE_REL_NS, "Relationship"),
                {
                    "Id": f"rId{next_relation_id}",
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                    "Target": worksheet_target,
                },
            )

            ET.SubElement(
                content_types_tree,
                _qn(CONTENT_TYPES_NS, "Override"),
                {
                    "PartName": f"/{worksheet_path}",
                    "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
                },
            )

            replacements = {
                "xl/workbook.xml": _xml_bytes(workbook_tree),
                "xl/_rels/workbook.xml.rels": _xml_bytes(workbook_rels_tree),
                "[Content_Types].xml": _xml_bytes(content_types_tree),
                worksheet_path: _xml_bytes(_build_coordinate_worksheet(ordered_wires)),
            }
            _copy_archive_with_replacements(archive, target_path, replacements)

        return target_path


def _build_coordinate_worksheet(ordered_wires: list[OrderedWireRecord]) -> ET.Element:
    worksheet = ET.Element(_qn(MAIN_NS, "worksheet"))
    rows = [COORDINATE_HEADERS]
    for record in ordered_wires:
        rows.append(
            (
                record.wire_seq,
                record.wire_id,
                record.group_no,
                record.first_point_seq,
                record.second_point_seq,
                record.geometry.first_point.x,
                record.geometry.first_point.y,
                record.geometry.first_point.z,
                record.geometry.second_point.x,
                record.geometry.second_point.y,
                record.geometry.second_point.z,
                record.geometry.length,
                record.geometry.angle_deg,
            )
        )

    dimension = ET.SubElement(
        worksheet,
        _qn(MAIN_NS, "dimension"),
        {"ref": f"A1:{_excel_column(len(COORDINATE_HEADERS))}{len(rows)}"},
    )
    sheet_views = ET.SubElement(worksheet, _qn(MAIN_NS, "sheetViews"))
    ET.SubElement(sheet_views, _qn(MAIN_NS, "sheetView"), {"workbookViewId": "0"})
    ET.SubElement(worksheet, _qn(MAIN_NS, "sheetFormatPr"), {"defaultRowHeight": "15"})
    sheet_data = ET.SubElement(worksheet, _qn(MAIN_NS, "sheetData"))

    for row_index, values in enumerate(rows, start=1):
        row = ET.SubElement(sheet_data, _qn(MAIN_NS, "row"), {"r": str(row_index)})
        for col_index, value in enumerate(values, start=1):
            cell_ref = f"{_excel_column(col_index)}{row_index}"
            if isinstance(value, str):
                cell = ET.SubElement(row, _qn(MAIN_NS, "c"), {"r": cell_ref, "t": "inlineStr"})
                is_node = ET.SubElement(cell, _qn(MAIN_NS, "is"))
                ET.SubElement(is_node, _qn(MAIN_NS, "t")).text = value
            else:
                cell = ET.SubElement(row, _qn(MAIN_NS, "c"), {"r": cell_ref})
                ET.SubElement(cell, _qn(MAIN_NS, "v")).text = _format_number(value)

    ET.SubElement(
        worksheet,
        _qn(MAIN_NS, "pageMargins"),
        {
            "left": "0.7",
            "right": "0.7",
            "top": "0.75",
            "bottom": "0.75",
            "header": "0.3",
            "footer": "0.3",
        },
    )
    return worksheet


def _require_template_path(template: WireRecipeTemplate) -> Path:
    if not template.xlsm_template_path:
        raise ValueError("XLSM template path is not configured.")
    path = Path(template.xlsm_template_path)
    if not path.exists():
        raise FileNotFoundError(f"XLSM template not found: {path}")
    return path


def _copy_archive_with_replacements(
    source_archive: ZipFile,
    target_path: Path,
    replacements: dict[str, bytes],
) -> None:
    with NamedTemporaryFile(delete=False, dir=target_path.parent, suffix=target_path.suffix) as handle:
        temp_path = Path(handle.name)

    try:
        with ZipFile(temp_path, "w", compression=ZIP_DEFLATED) as destination:
            seen_names: set[str] = set()
            for info in source_archive.infolist():
                if info.filename in replacements:
                    destination.writestr(info, replacements.pop(info.filename))
                else:
                    destination.writestr(info, source_archive.read(info.filename))
                seen_names.add(info.filename)

            for name, data in replacements.items():
                if name in seen_names:
                    continue
                destination.writestr(name, data)

        os.replace(temp_path, target_path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _next_sheet_number(workbook_rels_tree: ET.Element) -> int:
    highest = 0
    for relation in workbook_rels_tree:
        target = relation.attrib.get("Target", "")
        if target.startswith("worksheets/sheet") and target.endswith(".xml"):
            number_text = target.removeprefix("worksheets/sheet").removesuffix(".xml")
            try:
                highest = max(highest, int(number_text))
            except ValueError:
                continue
    return highest + 1


def _next_relation_id(workbook_rels_tree: ET.Element) -> int:
    highest = 0
    for relation in workbook_rels_tree:
        relation_id = relation.attrib.get("Id", "")
        if relation_id.startswith("rId"):
            try:
                highest = max(highest, int(relation_id.removeprefix("rId")))
            except ValueError:
                continue
    return highest + 1


def _next_sheet_id(sheets_node: ET.Element) -> int:
    highest = 0
    for sheet in sheets_node:
        try:
            highest = max(highest, int(sheet.attrib.get("sheetId", "0")))
        except ValueError:
            continue
    return highest + 1


def _excel_column(index: int) -> str:
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _format_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _qn(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


__all__ = ["COORDINATE_HEADERS", "XLSMWriter"]
