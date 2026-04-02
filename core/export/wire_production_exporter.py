"""High-level wire production export orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .wb1_writer import WB1Writer
from .wire_models import OrderedWireRecord, WireGeometry
from .wire_ordering import order_wire_geometries
from .wire_recipe_models import WireRecipeTemplate
from .xlsm_writer import XLSMWriter


@dataclass(frozen=True)
class WireProductionExportResult:
    """Paths and ordered records created during one export run."""

    ordered_records: list[OrderedWireRecord]
    wb1_path: Path | None = None
    xlsm_path: Path | None = None


class WireProductionExporter:
    """Coordinate ordering plus WB1/XLSM file generation."""

    def __init__(self):
        self._wb1_writer = WB1Writer()
        self._xlsm_writer = XLSMWriter()

    def build_ordered_records(
        self,
        wire_geometries: list[WireGeometry],
        template: WireRecipeTemplate,
    ) -> list[OrderedWireRecord]:
        """Create deterministic production order using the template defaults."""

        return order_wire_geometries(wire_geometries, template.ordering)

    def export_bundle(
        self,
        wire_geometries: list[WireGeometry],
        template: WireRecipeTemplate,
        output_dir: str | Path,
        *,
        base_name: str,
        export_wb1: bool = True,
        export_xlsm: bool = True,
        xlsm_sheet_name: str = "AUTO_WIRE_EXPORT",
    ) -> WireProductionExportResult:
        """Export one or both production files from structured wire geometry."""

        issues = self.validate_export_request(
            wire_geometries,
            template,
            base_name=base_name,
            export_wb1=export_wb1,
            export_xlsm=export_xlsm,
        )
        if issues:
            raise ValueError("\n".join(issues))

        ordered_records = self.build_ordered_records(wire_geometries, template)
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        wb1_path: Path | None = None
        xlsm_path: Path | None = None

        if export_wb1:
            wb1_path = output_root / f"{base_name}.WB1"
            self._wb1_writer.write(
                ordered_records,
                template,
                wb1_path,
                output_name=wb1_path.name,
            )

        if export_xlsm:
            xlsm_path = output_root / f"{base_name}.xlsm"
            self._xlsm_writer.write(
                ordered_records,
                template,
                xlsm_path,
                sheet_name=xlsm_sheet_name,
                wb1_output_name=f"{base_name}.WB1",
            )

        return WireProductionExportResult(
            ordered_records=ordered_records,
            wb1_path=wb1_path,
            xlsm_path=xlsm_path,
        )

    def validate_export_request(
        self,
        wire_geometries: list[WireGeometry],
        template: WireRecipeTemplate,
        *,
        base_name: str,
        export_wb1: bool,
        export_xlsm: bool,
    ) -> list[str]:
        """Return user-facing validation errors for one export request."""

        issues: list[str] = []
        if not wire_geometries:
            issues.append("No wire geometries are available for export.")
        if not base_name.strip():
            issues.append("Base file name is required.")
        if not export_wb1 and not export_xlsm:
            issues.append("Select at least one export target.")
        if export_wb1 and not template.wb1_template_path:
            issues.append("WB1 template path is required for WB1 export.")
        if export_wb1 and template.wb1_template_path and not Path(template.wb1_template_path).exists():
            issues.append(f"WB1 template not found: {template.wb1_template_path}")
        if export_xlsm and not template.xlsm_template_path:
            issues.append("XLSM template path is required for XLSM export.")
        if export_xlsm and template.xlsm_template_path and not Path(template.xlsm_template_path).exists():
            issues.append(f"XLSM template not found: {template.xlsm_template_path}")
        return issues


__all__ = ["WireProductionExporter", "WireProductionExportResult"]
