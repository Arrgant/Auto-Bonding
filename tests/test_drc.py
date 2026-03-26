"""
DRC unit tests.
"""

import pytest
import cadquery as cq

from core import BondingDiagramConverter, BondingElement, DRCChecker, DRCViolation


class TestDRCChecker:
    """DRC checker tests."""

    def test_init(self):
        checker = DRCChecker()
        assert checker.rules["min_wire_spacing"] == 0.1
        assert checker.rules["max_loop_height"] == 1.0
        assert checker.rules["min_pad_size"] == 0.2

    def test_init_with_rules(self):
        rules = {
            "min_wire_spacing": 0.15,
            "max_loop_height": 1.5,
            "min_pad_size": 0.3,
        }
        checker = DRCChecker(rules)
        assert checker.rules["min_wire_spacing"] == 0.15
        assert checker.rules["max_loop_height"] == 1.5
        assert checker.rules["min_pad_size"] == 0.3

    def test_check_wire_spacing_pass(self):
        checker = DRCChecker({"min_wire_spacing": 0.1})

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0)))
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0.5, 0, 0)))

        violations = checker.check_wire_spacing(assembly)
        assert len(violations) == 0

    def test_check_wire_spacing_fail(self):
        checker = DRCChecker({"min_wire_spacing": 0.5})

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0)))
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0.2, 0, 0)))

        violations = checker.check_wire_spacing(assembly)
        assert len(violations) > 0
        assert violations[0].violation_type == "spacing"

    def test_check_loop_height_pass(self):
        checker = DRCChecker({"max_loop_height": 1.0})

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0.5)))

        violations = checker.check_loop_height(assembly)
        assert len(violations) == 0

    def test_check_loop_height_fail(self):
        checker = DRCChecker({"max_loop_height": 0.5})

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 1.0)))

        violations = checker.check_loop_height(assembly)
        assert len(violations) > 0
        assert violations[0].violation_type == "height"

    def test_check_pad_size_pass(self):
        checker = DRCChecker({"min_pad_size": 0.1})

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(0.5, 0.5, 0.1), loc=cq.Location((0, 0, 0)))

        violations = checker.check_pad_size(assembly)
        assert len(violations) == 0

    def test_check_pad_size_fail(self):
        checker = DRCChecker({"min_pad_size": 0.5})

        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(0.2, 0.2, 0.1), loc=cq.Location((0, 0, 0)))

        violations = checker.check_pad_size(assembly)
        assert len(violations) > 0
        assert violations[0].violation_type == "pad_size"

    def test_run_and_report(self):
        checker = DRCChecker(
            {
                "min_wire_spacing": 0.1,
                "max_loop_height": 1.0,
                "min_pad_size": 0.2,
            }
        )

        converter = BondingDiagramConverter()
        elements = [
            BondingElement(
                element_type="die_pad",
                layer="DIE",
                geometry={"x": 0, "y": 0, "z": 0, "width": 1.0, "height": 1.0},
                properties={"thickness": 0.1},
            ),
        ]
        assembly = converter.convert_elements(elements)

        report = checker.run_and_report(assembly)

        assert "passed" in report
        assert "total_violations" in report
        assert "errors" in report
        assert "warnings" in report
        assert "violations" in report

    def test_violation_severity(self):
        violation = DRCViolation(
            violation_type="spacing",
            severity="error",
            description="too close",
            actual_value=0.05,
            required_value=0.1,
        )

        assert violation.severity == "error"
        assert violation.rule_category == "general"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
