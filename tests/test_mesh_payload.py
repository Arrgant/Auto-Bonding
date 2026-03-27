"""Mesh payload helper tests."""

from __future__ import annotations

import cadquery as cq
import pytest

from ui.widgets.mesh_payload import build_layer_mesh_payloads, build_mesh_payload


def test_build_mesh_payload_supports_coarse_and_fine_quality():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10.0, 6.0, 2.0), name="box")

    coarse_bytes, coarse_vertices, coarse_diagonal = build_mesh_payload(assembly, "coarse")
    fine_bytes, fine_vertices, fine_diagonal = build_mesh_payload(assembly, "fine")

    assert coarse_vertices > 0
    assert fine_vertices >= coarse_vertices
    assert coarse_diagonal == pytest.approx(fine_diagonal, rel=1e-6)
    assert coarse_bytes.size() > 0
    assert fine_bytes.size() > 0


def test_build_mesh_payload_supports_shared_center_override():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().center(50.0, 30.0).box(4.0, 4.0, 2.0), name="offset_box")

    mesh_bytes, vertex_count, diagonal = build_mesh_payload(
        assembly,
        "coarse",
        center_override=(0.0, 0.0, 0.0),
        diagonal_override=100.0,
    )

    assert vertex_count > 0
    assert diagonal >= 100.0
    assert mesh_bytes.size() > 0


def test_build_mesh_payload_keeps_local_tessellation_when_diagonal_is_overridden():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(10.0, 6.0, 2.0), name="box")

    base_bytes, base_vertices, _ = build_mesh_payload(assembly, "coarse")
    override_bytes, override_vertices, override_diagonal = build_mesh_payload(
        assembly,
        "coarse",
        diagonal_override=200.0,
    )

    assert base_vertices == override_vertices
    assert base_bytes.size() == override_bytes.size()
    assert override_diagonal >= 200.0


def test_build_mesh_payload_can_filter_dense_progressive_children():
    assembly = cq.Assembly()
    assembly.add(cq.Workplane().box(20.0, 20.0, 2.0), name="large_box")

    for index in range(80):
        x_offset = float(index % 20) * 0.4
        y_offset = float(index // 20) * 0.4
        assembly.add(cq.Workplane().center(x_offset, y_offset).box(0.1, 0.1, 0.1), name=f"tiny_{index}")

    full_bytes, full_vertices, _ = build_mesh_payload(assembly, "coarse", diagonal_override=100.0)
    filtered_bytes, filtered_vertices, _ = build_mesh_payload(
        assembly,
        "coarse",
        diagonal_override=100.0,
        progressive_filter=True,
    )

    assert full_vertices > 0
    assert filtered_vertices > 0
    assert filtered_vertices < full_vertices
    assert filtered_bytes.size() < full_bytes.size()


def test_build_layer_mesh_payloads_keep_distinct_layer_colors():
    assembly = cq.Assembly()
    assembly.add(
        cq.Workplane().box(10.0, 6.0, 2.0),
        name="layer_one_box",
        metadata={"layer": "01_base"},
    )
    assembly.add(
        cq.Workplane().center(0.0, 0.0).box(4.0, 4.0, 1.0),
        name="layer_two_box",
        metadata={"layer": "02_top"},
    )

    layer_meshes = build_layer_mesh_payloads(
        assembly,
        {"01_base": "#FF8A65", "02_top": "#4DD0E1"},
    )

    assert [payload["layer_name"] for payload in layer_meshes] == ["01_base", "02_top"]
    assert layer_meshes[0]["color_hex"] != layer_meshes[1]["color_hex"]
    assert all(payload["vertex_count"] > 0 for payload in layer_meshes)
