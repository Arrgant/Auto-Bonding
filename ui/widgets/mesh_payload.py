"""Mesh payload helpers for the Qt3D assembly preview."""

from __future__ import annotations

import math
import struct
from typing import Any

import cadquery as cq
from PySide6.QtCore import QByteArray

from core.layer_colors import hex_to_rgb
from core.layer_stack import layer_sort_key
from core.pipeline_types import LayerMeshPayload

MESH_QUALITY_SETTINGS = {
    "coarse": {
        "tolerance_divisor": 6.0,
        "min_tolerance": 2.0,
        "max_triangles": 8000,
    },
    "fine": {
        "tolerance_divisor": 12.0,
        "min_tolerance": 1.0,
        "max_triangles": 30000,
    },
}

PROGRESSIVE_CHILD_THRESHOLD = 48
PROGRESSIVE_MAX_PARTS = 120
PROGRESSIVE_MIN_PARTS = 12
PROGRESSIVE_MIN_DIAGONAL_RATIO = 0.0125
PROGRESSIVE_MIN_DIAGONAL_ABS = 0.35


def normalize_vertex(vertex: Any, center: tuple[float, float, float]) -> tuple[float, float, float]:
    raw = vertex.toTuple() if hasattr(vertex, "toTuple") else tuple(vertex)
    return (
        float(raw[0]) - center[0],
        float(raw[1]) - center[1],
        float(raw[2]) - center[2],
    )


def triangle_normal(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    p3: tuple[float, float, float],
) -> tuple[float, float, float]:
    ux, uy, uz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    vx, vy, vz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-9:
        return 0.0, 0.0, 1.0
    return nx / length, ny / length, nz / length


def _progressive_compound(assembly: Any, diagonal_hint: float) -> Any:
    """Build a lighter compound for progressive first-paint rendering."""

    children = list(getattr(assembly, "children", []))
    if len(children) <= PROGRESSIVE_CHILD_THRESHOLD:
        return assembly.toCompound()

    candidates: list[tuple[float, Any]] = []
    for child in children:
        try:
            compound = child.toCompound()
            bbox = compound.BoundingBox()
        except Exception:
            continue

        diagonal = max(float(bbox.xlen), float(bbox.ylen), float(bbox.zlen), 0.0)
        if diagonal > 0:
            candidates.append((diagonal, compound))

    if len(candidates) <= PROGRESSIVE_CHILD_THRESHOLD:
        return assembly.toCompound()

    reference_diagonal = max(float(diagonal_hint), max(diagonal for diagonal, _ in candidates), 1.0)
    minimum_diagonal = max(
        reference_diagonal * PROGRESSIVE_MIN_DIAGONAL_RATIO,
        PROGRESSIVE_MIN_DIAGONAL_ABS,
    )

    kept = [(diagonal, compound) for diagonal, compound in candidates if diagonal >= minimum_diagonal]
    if len(kept) < PROGRESSIVE_MIN_PARTS:
        kept = sorted(candidates, key=lambda item: item[0], reverse=True)[:PROGRESSIVE_MIN_PARTS]
    elif len(kept) > PROGRESSIVE_MAX_PARTS:
        kept = sorted(kept, key=lambda item: item[0], reverse=True)[:PROGRESSIVE_MAX_PARTS]

    return cq.Compound.makeCompound([compound for _, compound in kept])


def _mesh_payload_from_compound(
    compound: Any,
    quality: str,
    *,
    center_override: tuple[float, float, float] | None = None,
    diagonal_override: float | None = None,
) -> tuple[QByteArray, int, float]:
    if compound is None:
        return QByteArray(), 0, 1.0

    settings = MESH_QUALITY_SETTINGS.get(quality, MESH_QUALITY_SETTINGS["coarse"])
    bbox = compound.BoundingBox()
    geometry_diagonal = max(float(bbox.xlen), float(bbox.ylen), float(bbox.zlen), 1.0)
    render_diagonal = max(geometry_diagonal, float(diagonal_override or 0.0), 1.0)
    tolerance = max(geometry_diagonal / float(settings["tolerance_divisor"]), float(settings["min_tolerance"]))
    vertices, triangles = compound.tessellate(tolerance)
    if not triangles:
        return QByteArray(), 0, render_diagonal

    max_triangles = int(settings["max_triangles"])
    stride = max(1, math.ceil(len(triangles) / max_triangles))
    sampled_triangles = triangles[::stride]
    center = center_override or (
        float(bbox.xmin + bbox.xmax) / 2.0,
        float(bbox.ymin + bbox.ymax) / 2.0,
        float(bbox.zmin + bbox.zmax) / 2.0,
    )

    payload = bytearray()
    vertex_count = 0
    for indexes in sampled_triangles:
        p1 = normalize_vertex(vertices[indexes[0]], center)
        p2 = normalize_vertex(vertices[indexes[1]], center)
        p3 = normalize_vertex(vertices[indexes[2]], center)
        nx, ny, nz = triangle_normal(p1, p2, p3)
        payload.extend(struct.pack("6f", *p1, nx, ny, nz))
        payload.extend(struct.pack("6f", *p2, nx, ny, nz))
        payload.extend(struct.pack("6f", *p3, nx, ny, nz))
        vertex_count += 3

    return QByteArray(bytes(payload)), vertex_count, render_diagonal


def build_mesh_payload(
    assembly: Any,
    quality: str = "coarse",
    *,
    center_override: tuple[float, float, float] | None = None,
    diagonal_override: float | None = None,
    progressive_filter: bool = False,
) -> tuple[QByteArray, int, float]:
    """Build a Qt3D-ready vertex payload from a CadQuery assembly."""

    settings = MESH_QUALITY_SETTINGS.get(quality, MESH_QUALITY_SETTINGS["coarse"])
    if not hasattr(assembly, "toCompound"):
        return QByteArray(), 0, 1.0

    compound = (
        _progressive_compound(assembly, float(diagonal_override or 0.0))
        if progressive_filter
        else assembly.toCompound()
    )
    return _mesh_payload_from_compound(
        compound,
        quality,
        center_override=center_override,
        diagonal_override=diagonal_override,
    )


def build_layer_mesh_payloads(
    assembly: Any,
    layer_colors: dict[str, str],
    quality: str = "coarse",
) -> list[LayerMeshPayload]:
    """Build one mesh payload per layer so the 3D preview can color them separately."""

    if not hasattr(assembly, "children"):
        return []

    try:
        compound = assembly.toCompound()
        bbox = compound.BoundingBox()
    except Exception:
        return []

    center_override = (
        float(bbox.xmin + bbox.xmax) / 2.0,
        float(bbox.ymin + bbox.ymax) / 2.0,
        float(bbox.zmin + bbox.zmax) / 2.0,
    )
    diagonal_override = max(float(bbox.xlen), float(bbox.ylen), float(bbox.zlen), 1.0)

    grouped: dict[str, list[Any]] = {}
    for child in getattr(assembly, "children", []):
        metadata = dict(getattr(child, "metadata", {}) or {})
        layer_name = str(metadata.get("layer") or "0")
        try:
            child_compound = child.toCompound()
        except Exception:
            continue
        grouped.setdefault(layer_name, []).append(child_compound)

    payloads: list[LayerMeshPayload] = []
    for layer_name in sorted(grouped, key=layer_sort_key):
        compounds = grouped[layer_name]
        if not compounds:
            continue
        layer_compound = compounds[0] if len(compounds) == 1 else cq.Compound.makeCompound(compounds)
        mesh_bytes, vertex_count, diagonal = _mesh_payload_from_compound(
            layer_compound,
            quality,
            center_override=center_override,
            diagonal_override=diagonal_override,
        )
        if vertex_count <= 0:
            continue
        payloads.append(
            {
                "layer_name": layer_name,
                "color_hex": layer_colors.get(layer_name, "#E8E8E8"),
                "mesh_bytes": mesh_bytes,
                "vertex_count": vertex_count,
                "diagonal": diagonal,
            }
        )

    return payloads


def layer_payload_rgb(payload: LayerMeshPayload) -> tuple[int, int, int]:
    """Return the RGB tuple for one layer payload."""

    return hex_to_rgb(payload["color_hex"])


__all__ = [
    "MESH_QUALITY_SETTINGS",
    "build_mesh_payload",
    "build_layer_mesh_payloads",
    "layer_payload_rgb",
    "normalize_vertex",
    "triangle_normal",
]
