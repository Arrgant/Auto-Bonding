"""Design rule checks for converted bonding assemblies."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import cadquery as cq

from .drc_checks import (
    check_current_capacity as run_current_capacity_check,
    check_igbt_pad_size as run_igbt_pad_size_check,
    check_loop_height as run_loop_height_check,
    check_standard_pad_size as run_standard_pad_size_check,
    check_voltage_spacing as run_voltage_spacing_check,
    check_wire_spacing as run_wire_spacing_check,
    check_wire_span as run_wire_span_check,
)
from .drc_rules import IGBT_RULE_DEFAULTS, resolve_drc_rules
from .helpers import build_violation_report, collect_assembly_solids
from .models import DRCMode, DRCViolation


class DRCChecker:
    """Run geometry- and rule-based checks against a converted assembly."""

    IGBT_RULES = IGBT_RULE_DEFAULTS

    def __init__(self, rules: Optional[Dict] = None, mode: DRCMode = DRCMode.STANDARD):
        self.mode = mode
        self.is_igbt = mode in {DRCMode.IGBT, DRCMode.AUTOMOTIVE}
        self.rules = resolve_drc_rules(rules, mode)

    def _collect_solids(self, assembly: cq.Assembly) -> List[Any]:
        """Expose solid collection as an overridable seam for tests/customization."""

        return collect_assembly_solids(assembly)

    def check_all(self, assembly: cq.Assembly, elements: Optional[List] = None) -> List[DRCViolation]:
        """Run every enabled check and return a flat violation list."""

        violations: list[DRCViolation] = []
        violations.extend(self.check_wire_spacing(assembly))
        violations.extend(self.check_loop_height(assembly))
        violations.extend(self.check_pad_size(assembly))

        if self.is_igbt:
            violations.extend(self.check_wire_span(assembly, elements))
            violations.extend(self.check_current_capacity(elements))
            if elements:
                violations.extend(self.check_voltage_spacing(elements))

        return violations

    def check_wire_spacing(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """Validate minimum spacing between every solid pair."""

        solids = self._collect_solids(assembly)
        return run_wire_spacing_check(solids, self.rules["min_wire_spacing"])

    def check_loop_height(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """Validate maximum absolute height above the reference plane."""

        solids = self._collect_solids(assembly)
        return run_loop_height_check(solids, self.rules["max_loop_height"])

    def check_pad_size(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """Validate pad footprint dimensions."""

        solids = self._collect_solids(assembly)
        if self.is_igbt:
            return run_igbt_pad_size_check(solids, self.rules)
        return run_standard_pad_size_check(solids, self.rules.get("min_pad_size", 0.2))

    def check_wire_span(self, assembly: cq.Assembly, elements: Optional[List] = None) -> List[DRCViolation]:
        """Validate unsupported span lengths for IGBT-oriented inputs."""

        del assembly
        return run_wire_span_check(elements, self.rules)

    def check_current_capacity(self, elements: Optional[List] = None) -> List[DRCViolation]:
        """Validate estimated current demand against rough conductor capacity."""

        return run_current_capacity_check(elements, self.rules)

    def check_voltage_spacing(self, elements: Optional[List] = None) -> List[DRCViolation]:
        """Validate spacing against the inferred operating voltage class."""

        return run_voltage_spacing_check(elements, self.rules)

    def run_and_report(self, assembly: cq.Assembly) -> Dict[str, Any]:
        """Run all checks and return the normalized report payload."""

        return build_violation_report(self.check_all(assembly))

    def print_report(self, report: Dict[str, Any]):
        """Print a human-readable DRC report."""

        if report["passed"]:
            print("DRC passed.")
            return

        print(f"DRC failed: {report['errors']} errors, {report['warnings']} warnings")

        if report["errors"] > 0:
            print("\nErrors:")
            for violation in [item for item in report["violations"] if item.severity == "error"]:
                print(
                    f"  - {violation.description} "
                    f"(actual: {violation.actual_value:.4f}, required: {violation.required_value:.4f})"
                )

        if report["warnings"] > 0:
            print("\nWarnings:")
            for violation in [item for item in report["violations"] if item.severity == "warning"]:
                print(
                    f"  - {violation.description} "
                    f"(actual: {violation.actual_value:.4f}, required: {violation.required_value:.4f})"
                )
