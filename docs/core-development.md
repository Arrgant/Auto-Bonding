# Core Development Notes

This document captures the current responsibilities, data flow, and safe extension points for the DXF conversion core.

It is intentionally focused on the modules that sit on the critical path between importing a DXF file and producing preview/export artifacts:

- `core/raw_dxf.py`
- `core/fallback.py`
- `core/validation/models.py`
- `core/validation/helpers.py`
- `core/validation/drc.py`
- `core/pipeline.py`

## Pipeline At A Glance

`prepare_document()` in `core/pipeline.py` is the main orchestration entry point used by the desktop app.

Current flow:

1. Load raw DXF entities and layer metadata with `load_raw_dxf_entities()`.
2. Try the semantic DXF parser with `DXFParser.parse_file()`.
3. If semantic parsing yields no bonding elements, fall back to `infer_elements_from_raw_entities()`.
4. Convert `BondingElement` objects into a CadQuery assembly with `BondingDiagramConverter`.
5. Extract bond coordinates from the assembly, or fall back to raw entity coordinates if the assembly result is too sparse.
6. Run DRC checks with `DRCChecker`.
7. Return a document dictionary that the UI can render directly.

The main design rule here is:

- `pipeline.py` should coordinate work, not own detailed DXF heuristics or rule logic.

If a future change needs new geometry heuristics or new rule logic, prefer extending the dedicated module and keeping `pipeline.py` thin.

## `core/raw_dxf.py`

Purpose:

- Read low-level DXF entities with `ezdxf`.
- Produce a UI-friendly scene rectangle for 2D preview.
- Collect per-layer metadata for status display and future import controls.
- Provide a raw coordinate fallback when higher-level modeling does not yield enough points.

Key public functions:

- `load_raw_dxf_entities(file_path, layer_mapping=None)`
- `extract_coordinates_from_raw_entities(raw_entities)`

Important invariants:

- Raw entities are normalized into plain dictionaries so downstream modules do not depend on `ezdxf` objects.
- The returned `scene_rect` uses the current Qt preview convention, including Y-axis inversion for display.
- `layer_info` is sorted by descending entity count, then by name. The UI currently relies on this for stable display.
- `extract_coordinates_from_raw_entities()` deduplicates using rounded `(x, y, z)` keys at 4 decimal places.

Supported raw entity types today:

- `LINE`
- `CIRCLE`
- `ARC`
- `LWPOLYLINE`
- `POINT`

Implementation notes:

- Arc-like `LWPOLYLINE` segments are expanded through `bulge_to_arc()`. This is important because some real DXF inputs encode holes and rounded features as bulged lightweight polylines instead of `CIRCLE`.
- Bounds are updated from sampled points, not only control points. This keeps the 2D preview framing accurate for arcs.

Safe extension guidance:

- Add new raw entity adapters here if the UI needs to visualize them or the fallback path needs them.
- Keep the output dictionaries simple and JSON-like.
- Avoid embedding business meaning here. `raw_dxf.py` should describe geometry, not decide whether something is a pad, wire, or mounting hole.

Primary tests:

- `tests/test_raw_dxf.py`

## `core/fallback.py`

Purpose:

- Infer a minimal set of `BondingElement` objects from raw geometry when semantic layer-based parsing does not match the input file.

This module exists to keep the app usable on imperfect or loosely structured DXF files. It is intentionally heuristic-based.

Key public function:

- `infer_elements_from_raw_entities(raw_entities, config)`

Current heuristics:

- `LINE` becomes a simple `wire`.
- `ARC` becomes a wire from sampled start/end points.
- `CIRCLE` becomes a circular `die_pad`.
- Closed `LWPOLYLINE` can become:
  - a circular `die_pad` if it looks circle-like
  - a rectangular `die_pad` if its bounding box area is large enough
- Open `LWPOLYLINE` can become a `wire` if its path length is long enough

Config knobs used by this module:

- `fallback_closed_polyline_min_area`
- `fallback_open_polyline_min_length`
- `fallback_min_round_radius`
- `fallback_max_closed_polylines`
- `fallback_max_open_polylines`
- `fallback_max_round_features`
- `default_wire_diameter`
- `default_material`

Important invariants:

- This path is a fallback, not the source of truth for bonding semantics.
- Ranking and caps (`max_*`) are deliberate. They keep noisy DXF files from exploding into huge preview assemblies.
- The module returns `BondingElement` objects only. It should not perform CadQuery operations itself.

Safe extension guidance:

- Prefer additive heuristics over replacing existing ones.
- If you add a new heuristic, make sure it can fail quietly and leave the previous behavior intact.
- Keep thresholds configurable when practical.
- When adding a new inferred element type, confirm the downstream converter and DRC logic already understand it.

Primary tests:

- `tests/test_fallback.py`

## `core/validation/models.py`

Purpose:

- Hold the small shared data structures used by DRC.

Current contents:

- `DRCMode`
- `DRCViolation`

Design note:

- Keep this file lightweight and dependency-poor so tests and helpers can import it without pulling in CadQuery-heavy logic unnecessarily.

## `core/validation/helpers.py`

Purpose:

- Provide small shared functions used by DRC checks and reporting.

Key helpers:

- `collect_assembly_solids(assembly)`
- `shape_distance(shape_a, shape_b)`
- `build_violation_report(violations, include_info=False)`

Important invariants:

- `collect_assembly_solids()` should prefer transformed world-space solids. That is why it first tries `assembly.toCompound().Solids()`.
- `shape_distance()` is the single distance seam for DRC spacing logic. If CadQuery or the underlying shape API changes, adapt it here first.
- `build_violation_report()` defines the report shape consumed by the app. If the UI depends on report keys, preserve that contract.

Safe extension guidance:

- Keep helpers narrow and reusable.
- Put shared data shaping here when both `pipeline.py` and `drc.py` need the same logic.
- Avoid moving actual rule decisions here; that belongs in `drc.py`.

Primary tests:

- `tests/test_validation_helpers.py`
- `tests/test_drc_regressions.py`

## `core/validation/drc.py`

Purpose:

- Implement rule evaluation for converted assemblies.

Main entry points:

- `DRCChecker.check_all()`
- `DRCChecker.run_and_report()`

Current rule families:

- wire spacing
- loop height
- pad size
- IGBT-only span checks
- IGBT-only current capacity checks
- IGBT-only voltage spacing checks

Important invariants:

- `check_all()` returns a flat list of `DRCViolation` instances.
- Report shaping should stay outside the rule methods unless it is shared through `build_violation_report()`.
- Rule methods should treat missing geometry defensively and fail in a controlled way.

Recent regression-sensitive behavior:

- Spacing checks now use transformed solids and a shared distance helper.
- Loop height uses `bbox.zmax`, not `bbox.zlen`, so elevated geometry is measured correctly.

Safe extension guidance:

- Add new rules as separate methods, then compose them from `check_all()`.
- Keep descriptions stable and readable because they appear in reports and tests.
- If a rule is domain-specific, consider gating it by `DRCMode` instead of branching deep inside generic rules.

Primary tests:

- `tests/test_drc.py`
- `tests/test_drc_regressions.py`

## Document Shape Returned By `prepare_document()`

The UI currently expects a dictionary with at least these keys:

- `raw_entities`
- `scene_rect`
- `raw_counts`
- `layer_info`
- `parser_elements`
- `elements`
- `converted_counts`
- `coordinates`
- `drc_report`
- `assembly`
- `used_fallback`
- `note`

If you change this shape:

- update the desktop UI
- update the relevant tests
- update any direct imports or report consumers that rely on these keys

## Testing Map

Current fast checks for the core path:

- `tests/test_raw_dxf.py`
- `tests/test_fallback.py`
- `tests/test_validation_helpers.py`
- `tests/test_drc.py`
- `tests/test_drc_regressions.py`
- `tests/test_converter.py`
- `tests/test_exporter.py`

Recommended smoke command after low-risk core changes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Safe Next Steps

The next low-risk improvements with good payoff are:

1. Add explicit layer-selection and layer-mapping UI on top of the existing `layer_info` payload.
2. Split more semantic parsing rules out of `core/parsing/dxf.py` into smaller helpers, mirroring the cleanup already done for `pipeline.py`.
3. Introduce a small fixture library of representative DXF samples so future regressions are easier to reproduce.

When in doubt, prefer:

- raw geometry handling in `raw_dxf.py`
- heuristic recovery in `fallback.py`
- rule evaluation in `validation/*`
- orchestration only in `pipeline.py`
