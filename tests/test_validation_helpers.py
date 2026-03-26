from __future__ import annotations

import cadquery as cq

from core.validation.helpers import build_violation_report, collect_assembly_solids
from core.validation.models import DRCViolation


def test_collect_assembly_solids_returns_shape_objects():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(1, 1, 1), name="box")

    solids = collect_assembly_solids(assembly)

    assert solids
    assert all(hasattr(solid, "BoundingBox") for solid in solids)


def test_build_violation_report_counts_by_severity():
    violations = [
        DRCViolation("spacing", "error", "too close", 0.05, 0.1),
        DRCViolation("height", "warning", "too tall", 1.2, 1.0),
        DRCViolation("note", "info", "for display", 0.0, 0.0),
    ]

    report = build_violation_report(violations, include_info=True)

    assert report["passed"] is False
    assert report["total_violations"] == 3
    assert report["errors"] == 1
    assert report["warnings"] == 1
    assert report["info"] == 1
    assert report["violations"] == violations
