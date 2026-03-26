"""Shared helper functions for DRC workflows."""

from __future__ import annotations

from typing import Any

import cadquery as cq

from ..pipeline_types import DRCReport
from .models import DRCViolation


def collect_assembly_solids(assembly: cq.Assembly) -> list[Any]:
    """Collect solids with assembly transforms applied."""

    try:
        compound = assembly.toCompound()
        solids = compound.Solids()
        if solids:
            return solids
    except Exception:
        pass

    solids: list[Any] = []

    try:
        solids.extend(assembly.solids().vals())
    except Exception:
        pass

    child_objects = getattr(assembly, "objects", {})
    for child in child_objects.values():
        obj = getattr(child, "obj", None)
        if obj is not None and hasattr(obj, "solids"):
            try:
                solids.extend(obj.solids().vals())
            except Exception:
                pass

    return solids


def shape_distance(shape_a: Any, shape_b: Any) -> float:
    """Return the minimum distance between two cadquery shapes."""

    if hasattr(shape_a, "distToShape"):
        return shape_a.distToShape(shape_b)[0]
    if hasattr(shape_a, "distance"):
        return shape_a.distance(shape_b)
    raise AttributeError("Shape does not support distance queries")


def build_violation_report(violations: list[DRCViolation], include_info: bool = False) -> DRCReport:
    """Summarize violations into the report shape used by the app."""

    errors = [item for item in violations if item.severity == "error"]
    warnings = [item for item in violations if item.severity == "warning"]

    report = {
        "passed": len(violations) == 0,
        "total_violations": len(violations),
        "errors": len(errors),
        "warnings": len(warnings),
        "violations": violations,
    }

    if include_info:
        info = [item for item in violations if item.severity not in {"error", "warning"}]
        report["info"] = len(info)

    return report
