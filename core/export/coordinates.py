"""Coordinate export helpers for downstream wire-bonding equipment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import cadquery as cq


@dataclass
class BondPoint:
    """One exported bonding coordinate."""

    x: float
    y: float
    z: float
    wire_type: int = 1  # 1 = first bond point, 2 = second bond point


class CoordinateExporter:
    """Export coordinate lists in a handful of machine-oriented formats."""

    def __init__(self):
        self.format_handlers = {
            "KS": self._export_ks,
            "K&S": self._export_ks,
            "KULICKE": self._export_ks,
            "ASM": self._export_asm,
            "ASM_PACIFIC": self._export_asm,
            "SHINKAWA": self._export_shinkawa,
            "CMD": self._export_shinkawa,
            "CSV": self._export_csv,
        }

    def extract_bond_points(self, assembly: cq.Assembly) -> List[BondPoint]:
        """Extract bond points from a 3D assembly.

        This is still a placeholder implementation. It returns a stable two-point
        sample so the export pipeline remains testable while richer extraction
        logic is developed.
        """

        del assembly
        return [
            BondPoint(0.0, 0.0, 0.0, wire_type=1),
            BondPoint(5.0, 0.0, 0.5, wire_type=2),
        ]

    def export(self, assembly: cq.Assembly, output_path: str, machine_type: str = "KS") -> bool:
        """Export coordinates in the requested machine format."""

        handler = self.format_handlers.get(machine_type.upper())
        if not handler:
            print(f"Unsupported export format: {machine_type}")
            return False

        points = self.extract_bond_points(assembly)
        return handler(points, output_path)

    def _export_ks(self, points: List[BondPoint], output_path: str) -> bool:
        """Export Kulicke & Soffa style `WRF` content."""

        try:
            with open(output_path, "w") as file:
                file.write("*WRF_FILE\n")
                file.write("; Auto-Bonding Generated\n")
                file.write("; X,Y,Z,WIRE_TYPE\n")

                for point in points:
                    file.write(f"{point.x:.4f},{point.y:.4f},{point.z:.4f},{point.wire_type}\n")

            return True
        except Exception as exc:
            print(f"Failed to export K&S format: {exc}")
            return False

    def _export_asm(self, points: List[BondPoint], output_path: str) -> bool:
        """Export ASM Pacific style coordinate content."""

        try:
            with open(output_path, "w") as file:
                file.write("ABS_FILE\n")
                file.write("; Auto-Bonding Generated\n")

                for point in points:
                    file.write(f"X={point.x:.4f} Y={point.y:.4f} Z={point.z:.4f} T={point.wire_type}\n")

            return True
        except Exception as exc:
            print(f"Failed to export ASM format: {exc}")
            return False

    def _export_shinkawa(self, points: List[BondPoint], output_path: str) -> bool:
        """Export Shinkawa style command content."""

        try:
            with open(output_path, "w") as file:
                file.write("CMD_FILE\n")
                file.write("; Auto-Bonding Generated\n")

                for point in points:
                    file.write(f"GOTO X{point.x:.4f} Y{point.y:.4f} Z{point.z:.4f}\n")

            return True
        except Exception as exc:
            print(f"Failed to export Shinkawa format: {exc}")
            return False

    def _export_csv(self, points: List[BondPoint], output_path: str) -> bool:
        """Export a simple CSV coordinate table."""

        try:
            import csv

            with open(output_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["X", "Y", "Z", "WIRE_TYPE"])

                for point in points:
                    writer.writerow(
                        [
                            f"{point.x:.4f}",
                            f"{point.y:.4f}",
                            f"{point.z:.4f}",
                            point.wire_type,
                        ]
                    )

            return True
        except Exception as exc:
            print(f"Failed to export CSV format: {exc}")
            return False

    def export_batch(
        self,
        assemblies: Dict[str, cq.Assembly],
        output_dir: str,
        machine_type: str = "KS",
    ) -> Dict[str, bool]:
        """Export multiple assemblies into one output directory."""

        results: Dict[str, bool] = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for name, assembly in assemblies.items():
            safe_name = Path(name).stem
            output_file = output_path / f"{safe_name}.{machine_type.lower()}"
            results[name] = self.export(assembly, str(output_file), machine_type)

        return results
