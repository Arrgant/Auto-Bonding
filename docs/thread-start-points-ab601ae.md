## Thread Start Points (`ab601ae`)

This note captures the recommended starting point for the three active worktrees after all of them were fast-forwarded to the same baseline commit:

- Base commit: `ab601ae`
- Date synced: `2026-04-03`
- Main worktree: `C:\Users\Arrgant\Desktop\Auto-Bonding`
- Semantic worktree: `C:\Users\Arrgant\Desktop\Auto-Bonding-semantic`
- Wire export worktree: `C:\Users\Arrgant\Desktop\Auto-Bonding-wire`
- UI adjust worktree: `C:\Users\Arrgant\Desktop\Auto-Bonding-ui`

All four worktrees are aligned to the same code version before new work continues.

## Shared Rules

- Prefer small batches and validate after each batch.
- Do not touch unrelated files just because they are nearby.
- Treat these as shared integration files and avoid changing them unless the branch task truly requires it:
  - `ui/main_window.py`
  - `ui/import_worker.py`
  - `core/pipeline.py`
  - `services/project_store.py`
- If one of the shared files must change, keep the edit narrow and add or update the closest relevant tests.

## `codex/semantic-opt`

Goal:
- Improve semantic classification accuracy, manual override flow, and semantic review stability.

Primary ownership:
- `core/semantic/classifier.py`
- `core/semantic/manual.py`
- `core/semantic/candidates.py`
- `core/semantic/relations.py`
- `core/semantic/confidence.py`
- `core/layer_semantics.py`
- `ui/widgets/semantic_panel.py`
- `services/layer_semantic_preset_store.py`

Prefer not to touch first:
- `ui/main_window.py`
- `ui/layer_config_dialog.py`
- `ui/layer_thickness_dialog.py`
- `ui/widgets/dxf_preview.py`
- `ui/widgets/assembly_preview.py`

First tests to keep green:
- `tests/test_semantic_classifier.py`
- `tests/test_semantic_manual.py`
- `tests/test_layer_semantics.py`
- `tests/test_semantic_panel.py`
- `tests/test_layer_semantic_preset_store.py`

Safe starting ideas:
- tighten classifier heuristics without changing UI flow
- improve manual override edge cases
- improve preset application or fallback confidence handling

## `codex/wire-export`

Goal:
- Improve wire extraction, wire production export, WB1/XLSM generation, and export dialog stability.

Primary ownership:
- `core/export/wire_extraction.py`
- `core/export/wire_production_exporter.py`
- `core/export/wb1_writer.py`
- `core/export/wb1_parser.py`
- `core/export/wb1_compare.py`
- `core/export/xlsm_writer.py`
- `core/export/wire_recipe_defaults.py`
- `core/export/wire_recipe_models.py`
- `services/wire_recipe_template_store.py`
- `ui/wire_export_dialog.py`
- `docs/rx2000-wb1-field-sourcing.md`
- `docs/rx2000-wb1-j-record-map.md`

Prefer not to touch first:
- `ui/main_window.py`
- `ui/layer_config_dialog.py`
- `ui/widgets/layer_manager.py`
- `ui/widgets/dxf_preview.py`
- `core/semantic/*`

First tests to keep green:
- `tests/test_wire_export_dialog.py`
- `tests/test_wire_extraction.py`
- `tests/test_wire_production_exporter.py`
- `tests/test_wb1_writer.py`
- `tests/test_wb1_parser.py`
- `tests/test_xlsm_writer.py`

Safe starting ideas:
- improve export validation and defaults
- harden WB1 field generation around missing inputs
- improve recipe template handling and naming consistency

## `codex/ui-adjust`

Goal:
- Refine desktop interaction flow, preview clarity, layer setup ergonomics, and status messaging.

Primary ownership:
- `ui/layer_config_dialog.py`
- `ui/layer_thickness_dialog.py`
- `ui/widgets/dxf_preview.py`
- `ui/widgets/assembly_preview.py`
- `ui/widgets/layer_manager.py`
- `ui/widgets/viewer_placeholder.py`

Secondary ownership:
- `ui/main_window.py`

Prefer not to touch first:
- `core/export/*`
- `core/semantic/*`
- `services/project_store.py`
- `core/pipeline.py`

First tests to keep green:
- `tests/test_layer_config_dialog.py`
- `tests/test_dxf_preview_widget.py`
- `tests/test_semantic_panel.py`

Safe starting ideas:
- improve button wording, walkthrough pacing, and preview hints
- reduce duplicate UI state updates
- add focused widget-level tests before touching `ui/main_window.py`

## Branch-Specific Advice

For `codex/semantic-opt`:
- If a change only affects semantic logic, keep it out of `ui/main_window.py`.
- Prefer returning richer semantic results from semantic modules rather than bolting UI-only state into the main window.

For `codex/wire-export`:
- Keep export formatting and field mapping logic inside `core/export/`.
- If the dialog needs new options, add tests around request payload shaping before wiring the UI.

For `codex/ui-adjust`:
- Prefer local widget improvements first.
- Use `ui/main_window.py` only for final connection, status text, or workflow sequencing that cannot live in the widget itself.

## Recommended Smoke Test Commands

Use:

```powershell
C:\Users\Arrgant\Desktop\Auto-Bonding\.venv\Scripts\python.exe -m compileall ui core services
```

For semantic work:

```powershell
C:\Users\Arrgant\Desktop\Auto-Bonding\.venv\Scripts\python.exe -m pytest tests/test_semantic_classifier.py tests/test_semantic_manual.py tests/test_layer_semantics.py tests/test_semantic_panel.py -q
```

For wire export work:

```powershell
C:\Users\Arrgant\Desktop\Auto-Bonding\.venv\Scripts\python.exe -m pytest tests/test_wire_export_dialog.py tests/test_wire_extraction.py tests/test_wire_production_exporter.py tests/test_wb1_writer.py tests/test_wb1_parser.py tests/test_xlsm_writer.py -q
```

For UI work:

```powershell
C:\Users\Arrgant\Desktop\Auto-Bonding\.venv\Scripts\python.exe -m pytest tests/test_layer_config_dialog.py tests/test_dxf_preview_widget.py tests/test_semantic_panel.py -q
```

If a branch edits one of the shared integration files, also run the most relevant targeted tests before handing off for merge.
