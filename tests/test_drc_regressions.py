from __future__ import annotations

import cadquery as cq
import pytest

from core.validation.drc import DRCChecker


def test_check_wire_spacing_uses_world_coordinates():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0)), name="left")
    assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0.5, 0, 0)), name="right")

    checker = DRCChecker({"min_wire_spacing": 0.1})
    violations = checker.check_wire_spacing(assembly)

    assert violations == []


def test_check_loop_height_uses_absolute_z_height():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 1.0)), name="high")

    checker = DRCChecker({"max_loop_height": 0.5})
    violations = checker.check_loop_height(assembly)

    assert len(violations) == 1
    assert violations[0].violation_type == "height"
    assert violations[0].actual_value == pytest.approx(1.05, rel=1e-3)
