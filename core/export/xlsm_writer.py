"""Template-driven XLSM writer for wire coordinate exports."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from .wb1_writer import WB1Writer
from .wb_sheet_codec import parse_wb1_content_to_rows, token_is_querytable_numeric
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

    def __init__(self):
        self._wb1_writer = WB1Writer()

    def write(
        self,
        ordered_wires: list[OrderedWireRecord],
        template: WireRecipeTemplate,
        output_path: str | Path,
        *,
        sheet_name: str = "AUTO_WIRE_EXPORT",
        wb1_output_name: str | None = None,
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

            wb_sheet_path = _find_sheet_path(workbook_tree, workbook_rels_tree, "WB")
            pfile_sheet_path = _find_sheet_path(workbook_tree, workbook_rels_tree, "PFILE")
            replacements = {
                "xl/workbook.xml": _xml_bytes(workbook_tree),
                "xl/_rels/workbook.xml.rels": _xml_bytes(workbook_rels_tree),
                "[Content_Types].xml": _xml_bytes(content_types_tree),
                worksheet_path: _xml_bytes(_build_coordinate_worksheet(ordered_wires, default_z=template.default_z)),
            }
            wb_sheet_replacement = self._build_wb_sheet_replacement(
                archive,
                ordered_wires,
                template,
                wb_sheet_path=wb_sheet_path,
                wb1_output_name=wb1_output_name or f"{target_path.stem}.WB1",
            )
            if wb_sheet_replacement is not None and wb_sheet_path is not None:
                replacements[wb_sheet_path] = wb_sheet_replacement
            pfile_sheet_replacement = self._build_pfile_sheet_replacement(
                archive,
                template,
                pfile_sheet_path=pfile_sheet_path,
            )
            if pfile_sheet_replacement is not None and pfile_sheet_path is not None:
                replacements[pfile_sheet_path] = pfile_sheet_replacement
            _copy_archive_with_replacements(archive, target_path, replacements)

        return target_path

    def write_wb1_import(
        self,
        wb1_path: str | Path,
        template: WireRecipeTemplate,
        output_path: str | Path,
    ) -> Path:
        """Copy one XLSM template and import a raw WB1 file into its WB sheet."""

        template_path = _require_template_path(template)
        source_wb1_path = Path(wb1_path)
        if not source_wb1_path.exists():
            raise FileNotFoundError(f"WB1 source not found: {source_wb1_path}")

        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        wb1_content = source_wb1_path.read_text(encoding="utf-8", errors="ignore")

        with ZipFile(template_path, "r") as archive:
            workbook_tree = ET.fromstring(archive.read("xl/workbook.xml"))
            workbook_rels_tree = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

            wb_sheet_path = _find_sheet_path(workbook_tree, workbook_rels_tree, "WB")
            if wb_sheet_path is None:
                raise ValueError("Workbook template does not contain a WB worksheet.")
            pfile_sheet_path = _find_sheet_path(workbook_tree, workbook_rels_tree, "PFILE")

            worksheet = ET.fromstring(archive.read(wb_sheet_path))
            _populate_wb_worksheet(worksheet, wb1_content)
            replacements = {wb_sheet_path: _xml_bytes(worksheet)}

            pfile_sheet_replacement = self._build_pfile_sheet_replacement(
                archive,
                template,
                pfile_sheet_path=pfile_sheet_path,
            )
            if pfile_sheet_replacement is not None and pfile_sheet_path is not None:
                replacements[pfile_sheet_path] = pfile_sheet_replacement

            _copy_archive_with_replacements(archive, target_path, replacements)

        return target_path

    def _build_wb_sheet_replacement(
        self,
        archive: ZipFile,
        ordered_wires: list[OrderedWireRecord],
        template: WireRecipeTemplate,
        *,
        wb_sheet_path: str | None,
        wb1_output_name: str,
    ) -> bytes | None:
        if wb_sheet_path is None:
            return None
        if not template.wb1_template_path or not Path(template.wb1_template_path).exists():
            return None

        wb1_content = self._wb1_writer.render(ordered_wires, template, output_name=wb1_output_name)
        worksheet = ET.fromstring(archive.read(wb_sheet_path))
        _populate_wb_worksheet(worksheet, wb1_content)
        return _xml_bytes(worksheet)

    def _build_pfile_sheet_replacement(
        self,
        archive: ZipFile,
        template: WireRecipeTemplate,
        *,
        pfile_sheet_path: str | None,
    ) -> bytes | None:
        if pfile_sheet_path is None:
            return None
        resolved_overrides = template.resolve_pfile_cell_overrides()
        if not resolved_overrides:
            return None

        worksheet = ET.fromstring(archive.read(pfile_sheet_path))
        _apply_sheet_cell_overrides(worksheet, resolved_overrides)
        return _xml_bytes(worksheet)


def _build_coordinate_worksheet(
    ordered_wires: list[OrderedWireRecord],
    *,
    default_z: float,
) -> ET.Element:
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
                record.geometry.first_point.resolved_z(default_z),
                record.geometry.second_point.x,
                record.geometry.second_point.y,
                record.geometry.second_point.resolved_z(default_z),
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


def _populate_wb_worksheet(worksheet: ET.Element, wb1_content: str, *, start_row: int = 4) -> None:
    sheet_data = worksheet.find(_qn(MAIN_NS, "sheetData"))
    if sheet_data is None:
        sheet_data = ET.SubElement(worksheet, _qn(MAIN_NS, "sheetData"))

    preserved_rows = [row for row in sheet_data.findall(_qn(MAIN_NS, "row")) if int(row.attrib.get("r", "0")) < start_row]
    preserved_max_column = 1
    for row in preserved_rows:
        for cell in row.findall(_qn(MAIN_NS, "c")):
            preserved_max_column = max(preserved_max_column, _column_index_from_ref(cell.attrib.get("r", "A1")))
    sheet_data.clear()
    for row in preserved_rows:
        sheet_data.append(row)

    wb_rows = parse_wb1_content_to_rows(wb1_content)
    max_fields = preserved_max_column
    for offset, fields in enumerate(wb_rows):
        row_index = start_row + offset
        row = ET.Element(_qn(MAIN_NS, "row"), {"r": str(row_index)})
        max_fields = max(max_fields, len(fields))
        for column_index, value in enumerate(fields, start=1):
            cell_ref = f"{_excel_column(column_index)}{row_index}"
            if value == "":
                continue
            if token_is_querytable_numeric(value):
                cell = ET.SubElement(row, _qn(MAIN_NS, "c"), {"r": cell_ref})
                ET.SubElement(cell, _qn(MAIN_NS, "v")).text = str(int(value))
            else:
                cell = ET.SubElement(
                    row,
                    _qn(MAIN_NS, "c"),
                    {
                        "r": cell_ref,
                        "t": "inlineStr",
                    },
                )
                inline_string = ET.SubElement(cell, _qn(MAIN_NS, "is"))
                ET.SubElement(inline_string, _qn(MAIN_NS, "t")).text = value
        sheet_data.append(row)

    dimension = worksheet.find(_qn(MAIN_NS, "dimension"))
    if dimension is None:
        dimension = ET.Element(_qn(MAIN_NS, "dimension"))
        worksheet.insert(0, dimension)

    max_row = max([start_row + len(wb_rows) - 1, *[int(row.attrib.get("r", "0")) for row in preserved_rows]], default=start_row)
    min_row = min([int(row.attrib.get("r", "0")) for row in sheet_data.findall(_qn(MAIN_NS, "row"))], default=start_row)
    dimension.set("ref", f"A{min_row}:{_excel_column(max_fields)}{max_row}")


def _apply_sheet_cell_overrides(worksheet: ET.Element, overrides: dict[str, object]) -> None:
    if not overrides:
        return
    sheet_data = worksheet.find(_qn(MAIN_NS, "sheetData"))
    if sheet_data is None:
        sheet_data = ET.SubElement(worksheet, _qn(MAIN_NS, "sheetData"))

    row_map = {int(row.attrib.get("r", "0")): row for row in sheet_data.findall(_qn(MAIN_NS, "row"))}
    applied_refs: list[str] = []

    for cell_ref, value in sorted(overrides.items(), key=lambda item: _cell_sort_key(item[0])):
        row_number, _ = _split_cell_ref(cell_ref)
        row = row_map.get(row_number)
        if row is None:
            row = ET.Element(_qn(MAIN_NS, "row"), {"r": str(row_number)})
            _insert_row_sorted(sheet_data, row)
            row_map[row_number] = row
        cell = _find_row_cell(row, cell_ref)
        if cell is None:
            cell = ET.Element(_qn(MAIN_NS, "c"), {"r": cell_ref})
            _insert_cell_sorted(row, cell)
        _set_cell_value(cell, value)
        applied_refs.append(cell_ref)

    if applied_refs:
        _expand_dimension_for_refs(worksheet, applied_refs)


def _require_template_path(template: WireRecipeTemplate) -> Path:
    if not template.xlsm_template_path:
        raise ValueError("XLSM template path is not configured.")
    path = Path(template.xlsm_template_path)
    if not path.exists():
        raise FileNotFoundError(f"XLSM template not found: {path}")
    return path


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


def _set_cell_value(cell: ET.Element, value: object) -> None:
    for child in list(cell):
        if child.tag in {_qn(MAIN_NS, "v"), _qn(MAIN_NS, "is")}:
            cell.remove(child)

    if isinstance(value, str):
        cell.set("t", "inlineStr")
        inline_string = ET.SubElement(cell, _qn(MAIN_NS, "is"))
        ET.SubElement(inline_string, _qn(MAIN_NS, "t")).text = value
        return

    if isinstance(value, bool):
        value = 1 if value else 0
    if not isinstance(value, (int, float)):
        raise TypeError(f"Unsupported worksheet cell override value: {value!r}")
    if "t" in cell.attrib:
        cell.attrib.pop("t", None)
    ET.SubElement(cell, _qn(MAIN_NS, "v")).text = _format_number(value)


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


def _split_cell_ref(cell_ref: str) -> tuple[int, int]:
    letters = []
    digits = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char.upper())
        elif char.isdigit():
            digits.append(char)
    row_number = int("".join(digits) or "1")
    column_number = _column_index_from_ref("".join(letters) or "A")
    return row_number, column_number


def _cell_sort_key(cell_ref: str) -> tuple[int, int]:
    row_number, column_number = _split_cell_ref(cell_ref)
    return row_number, column_number


def _find_row_cell(row: ET.Element, cell_ref: str) -> ET.Element | None:
    for cell in row.findall(_qn(MAIN_NS, "c")):
        if cell.attrib.get("r") == cell_ref:
            return cell
    return None


def _insert_row_sorted(sheet_data: ET.Element, row: ET.Element) -> None:
    row_number = int(row.attrib["r"])
    inserted = False
    for index, existing_row in enumerate(sheet_data.findall(_qn(MAIN_NS, "row"))):
        if int(existing_row.attrib.get("r", "0")) > row_number:
            sheet_data.insert(index, row)
            inserted = True
            break
    if not inserted:
        sheet_data.append(row)


def _insert_cell_sorted(row: ET.Element, cell: ET.Element) -> None:
    _, target_column = _split_cell_ref(cell.attrib["r"])
    inserted = False
    for index, existing_cell in enumerate(row.findall(_qn(MAIN_NS, "c"))):
        _, existing_column = _split_cell_ref(existing_cell.attrib.get("r", "A1"))
        if existing_column > target_column:
            row.insert(index, cell)
            inserted = True
            break
    if not inserted:
        row.append(cell)


def _expand_dimension_for_refs(worksheet: ET.Element, cell_refs: list[str]) -> None:
    if not cell_refs:
        return
    dimension = worksheet.find(_qn(MAIN_NS, "dimension"))
    rows = []
    columns = []
    for cell_ref in cell_refs:
        row_number, column_number = _split_cell_ref(cell_ref)
        rows.append(row_number)
        columns.append(column_number)

    min_row = min(rows)
    max_row = max(rows)
    min_column = min(columns)
    max_column = max(columns)

    if dimension is not None and "ref" in dimension.attrib:
        start_ref, _, end_ref = dimension.attrib["ref"].partition(":")
        existing_start_row, existing_start_col = _split_cell_ref(start_ref)
        existing_end_row, existing_end_col = _split_cell_ref(end_ref or start_ref)
        min_row = min(min_row, existing_start_row)
        max_row = max(max_row, existing_end_row)
        min_column = min(min_column, existing_start_col)
        max_column = max(max_column, existing_end_col)
    else:
        if dimension is None:
            dimension = ET.Element(_qn(MAIN_NS, "dimension"))
            worksheet.insert(0, dimension)

    dimension.set("ref", f"{_excel_column(min_column)}{min_row}:{_excel_column(max_column)}{max_row}")


def _qn(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


__all__ = ["COORDINATE_HEADERS", "XLSMWriter"]
