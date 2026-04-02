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
            )

        return WireProductionExportResult(
            ordered_records=ordered_records,
            wb1_path=wb1_path,
            xlsm_path=xlsm_path,
        )


__all__ = ["WireProductionExporter", "WireProductionExportResult"]
