# Weekly Release Note - 2026-04-03

## Scope

This week focused on integrating three active workstreams on top of the desktop DXF workflow:

- semantic recognition improvements
- wire export and audit improvements
- UI and workflow adjustments

Integration branch state at the end of the week:

- branch: `codex/clone-arrgantautobonding-repo`
- head: `afd820f`

## What Landed

### 1. Semantic workflow

Integrated from `codex/semantic-opt`.

Highlights:

- added per-layer semantic summaries for UI and reporting
- improved hole and round-feature heuristics
- allowed semantic fallback from import `mapped_type`
- supported manual confirmation for `round_feature`
- expanded semantic regression coverage

Key files:

- `core/semantic/layer_summary.py`
- `core/semantic/classifier.py`
- `core/semantic/manual.py`
- `core/layer_semantics.py`

### 2. Wire export workflow

Integrated from `codex/wire-export`.

Highlights:

- added wire extraction audit objects and report output
- added split-wire merge suggestions
- added WB1 J-segment write-plan and required-field checks
- hardened WB1 filename and export validation
- surfaced extraction and template health in the export dialog

Key files:

- `core/export/wire_extraction.py`
- `core/export/wb1_field_sources.py`
- `core/export/wb1_writer.py`
- `core/export/wire_production_exporter.py`
- `ui/wire_export_dialog.py`

### 3. UI and workflow adjustments

Integrated from `codex/ui-adjust`.

Highlights:

- improved import-layer dialog with filtering and empty-layer hiding
- refreshed semantic review panel into overview/detail flow
- refined layer panel presentation and interaction
- improved 2D viewer navigation hints and canvas behavior

Key files:

- `ui/layer_config_dialog.py`
- `ui/widgets/semantic_panel.py`
- `ui/widgets/layer_manager.py`
- `ui/widgets/dxf_preview.py`

### 4. Mainline DXF preview and parsing improvements

Also preserved and integrated from the main worktree before branch merge:

- expanded raw DXF support for ellipse, text, mtext, hatch, solid, insert, and attrib entities
- extended preview rendering to show those entities correctly
- expanded raw DXF and preview tests

Key files:

- `core/raw_dxf_helpers.py`
- `core/raw_dxf_types.py`
- `ui/widgets/dxf_preview.py`

## Conflict Notes

### `tests/test_dxf_preview_widget.py`

This was the only explicit text conflict during merge.

Final decision:

- kept UI-adjust navigation and zoom/pan behavior coverage
- kept DXF parsing/rendering coverage for text, hatch, solid, insert, and linetype rendering
- resolved by combining both test sets instead of choosing one side

### `ui/main_window.py`

This file did not raise a textual merge conflict, but the automatic result dropped required UI wiring.

Observed regression after merge:

- `semantic_panel` creation and signal hookups were missing
- `layers_button` creation and refresh hookups were missing
- later code still referenced both objects

Final decision:

- kept `ui-adjust` improvements such as `auto_continue` preview flow and top-bar sizing
- restored `semantic_panel` and `layers_button` setup from the previously working mainline flow
- limited the fix to the existing shared integration file rather than spreading changes outward

## Validation

Used:

```powershell
C:\Users\Arrgant\Desktop\Auto-Bonding\.venv\Scripts\python.exe
```

Executed:

```powershell
python -m compileall ui core services
python -m pytest tests/test_layer_config_dialog.py tests/test_dxf_preview_widget.py tests/test_semantic_panel.py -q
python -m pytest tests/test_wire_export_dialog.py tests/test_wire_extraction.py tests/test_wire_production_exporter.py tests/test_wb1_writer.py -q
python -m pytest tests/test_semantic_classifier.py tests/test_semantic_manual.py tests/test_layer_semantics.py -q
python -m pytest tests/test_raw_dxf.py -q
```

Results:

- compileall: passed
- UI-focused tests: `18 passed`
- wire export tests: `37 passed`
- semantic tests: `24 passed`
- raw DXF tests: `9 passed`

Targeted total:

- `88 passed`

Additional smoke check:

- `MainWindow()` offscreen construction passed

## Risks Still Open

- `ui/main_window.py` is still a dense integration point and has limited direct test coverage
- the new semantic overview/review flow is structurally tested, but still worth manual UX review
- wire extraction audit output is covered by tests, but should still be checked with one or two production DXF files
- the project has not yet run a full end-to-end manual pass across import, thickness walkthrough, 3D preview, and both export routes after this final integrated state

## Recommended Manual Review

- import one representative DXF and complete the full layer-thickness walkthrough
- verify 2D viewer zoom, pan, and new entity rendering on a richer drawing
- confirm semantic overview, review queue, and manual classification flow
- export WB1 and XLSM from a known-good template and inspect the audit report

## Suggested Next Week Tasks

1. Add focused tests around `ui/main_window.py` workflow transitions.
2. Run one documented end-to-end manual validation using a representative production DXF.
3. Decide whether the semantic panel and layer panel layout should remain stacked in the sidebar or be split by resize behavior.
4. Review the new wire audit wording with real users and simplify any noisy output.
5. Consider a small integration test around import preview -> auto-continue -> final build.
