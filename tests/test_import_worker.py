from pathlib import Path

import ezdxf
from PySide6.QtWidgets import QApplication

from services import ProjectDocument
from ui.import_worker import ImportWorker
from ui.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_import_worker_defers_wire_geometry_for_fast_import(tmp_path):
    document = ezdxf.new("R2010")
    document.layers.add("01_substrate", color=3)
    document.layers.add("06_wire", color=6)
    modelspace = document.modelspace()
    modelspace.add_lwpolyline(
        [(0.0, 0.0), (8.0, 0.0), (8.0, 6.0), (0.0, 6.0)],
        close=True,
        dxfattribs={"layer": "01_substrate"},
    )
    modelspace.add_lwpolyline(
        [(1.0, 1.0), (2.0, 1.0), (2.5, 2.0)],
        dxfattribs={"layer": "06_wire"},
    )
    file_path = tmp_path / "fast-import-wire.dxf"
    document.saveas(file_path)

    payloads: list[dict[str, object]] = []
    result: dict[str, object] = {}
    worker = ImportWorker(
        Path(file_path),
        {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
            "defer_wire_geometry": True,
            "defer_drc_report": True,
        },
    )
    worker.progress_ready.connect(lambda _path, payload: payloads.append(dict(payload)))
    worker.finished.connect(lambda _path, prepared: result.setdefault("prepared", prepared))
    worker.failed.connect(lambda _path, error: result.setdefault("error", error))

    worker.run()

    assert "error" not in result
    prepared = result["prepared"]
    assert prepared is not None
    assert all(payload["layer_name"] != "06_wire" for payload in prepared["layer_meshes"])
    assert any(payload["layer_name"] == "01_substrate" for payload in prepared["layer_meshes"])
    assert all(
        getattr(child, "metadata", {}).get("element_type") != "wire"
        for child in prepared["assembly"].children
    )

    wire_progress = next(payload for payload in payloads if payload["layer_name"] == "06_wire")
    assert wire_progress["deferred"] is True
    assert "Kept 06_wire in 2D during import for faster loading." in prepared["note"]
    assert prepared["drc_report"]["total_violations"] == 0


def test_main_window_rebuilds_wire_geometry_for_step_export(tmp_path):
    _app()

    document = ezdxf.new("R2010")
    document.layers.add("06_wire", color=6)
    modelspace = document.modelspace()
    modelspace.add_line((0.0, 0.0), (5.0, 0.0), dxfattribs={"layer": "06_wire"})
    file_path = tmp_path / "wire-step.dxf"
    document.saveas(file_path)

    result: dict[str, object] = {}
    worker = ImportWorker(
        Path(file_path),
        {
            "mode": "standard",
            "default_wire_diameter": 0.025,
            "default_material": "gold",
            "defer_wire_geometry": True,
            "defer_drc_report": True,
        },
    )
    worker.finished.connect(lambda _path, prepared: result.setdefault("prepared", prepared))
    worker.failed.connect(lambda _path, error: result.setdefault("error", error))
    worker.run()

    assert "error" not in result
    prepared = result["prepared"]
    window = MainWindow()
    window.document = ProjectDocument(
        path=Path(file_path),
        size_bytes=file_path.stat().st_size,
        raw_entities=prepared["raw_entities"],
        scene_rect=prepared["scene_rect"],
        raw_counts=prepared["raw_counts"],
        layer_info=prepared["layer_info"],
        parser_elements=prepared["parser_elements"],
        wire_geometries=prepared["wire_geometries"],
        drc_report=prepared["drc_report"],
        assembly=prepared["assembly"],
        note=prepared["note"],
    )

    assert not window._assembly_contains_element_type(window.document.assembly, "wire")
    rebuilt = window._full_step_export_assembly()

    assert rebuilt is not None
    assert window._assembly_contains_element_type(rebuilt, "wire")
    window.close()
