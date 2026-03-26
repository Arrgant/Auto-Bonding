# Auto-Bonding

Auto-Bonding is a Windows desktop application for wire-bonding DXF workflows.

The project is now fully aligned around a single desktop route:

- `PySide6` for the native Windows UI
- `ezdxf` for DXF parsing
- `CadQuery` for 3D modeling and `STEP` export
- `core/` for parsing, fallback inference, coordinate extraction, and DRC

There is no Web frontend, PWA, browser client, or separate backend deployment path in this repository anymore.

## What It Does

- Import `DXF` wire-bonding drawings
- Render a 2D preview inside the desktop app
- Build a 3D assembly preview from parsed or fallback geometry
- Export `STEP`
- Export wire-bond coordinates for downstream machine workflows
- Run DRC checks on converted assemblies
- Read DXF layer metadata for future layer mapping and import filtering

## Current Stack

- Python `3.11+`
- Windows 11 recommended
- `PySide6`
- `ezdxf`
- `CadQuery`
- `pytest`

Install dependencies from [requirements.txt](requirements.txt).

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python run_client.py
```

You can also launch the application directly:

```powershell
python main.py
```

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Packaging

```powershell
pyinstaller --name "Auto-Bonding" --windowed --onefile main.py
```

## Repository Layout

```text
Auto-Bonding/
|-- assets/           Application icons and bundled assets
|-- core/             Parsing, fallback inference, geometry, export, and DRC
|-- docs/             Developer notes
|-- services/         App state and lightweight service objects
|-- tests/            Unit and regression tests
|-- ui/               PySide6 desktop UI
|-- main.py           Application entry point
|-- run_client.py     Desktop launcher
`-- requirements.txt  Python dependencies
```

## Core Notes

- [Core development notes](docs/core-development.md)

## Project Status

The repository has already been cleaned up and aligned around the current desktop application route:

- old Web/frontend/backend remnants removed
- legacy compatibility package removed
- core parsing and validation modules split into smaller units
- DXF fallback logic and DRC logic covered by regression tests

At the time of the latest cleanup, the local test suite passes with:

```text
50 passed
```

## Roadmap Direction

Current development is focused on:

- improving DXF recognition accuracy
- refining layer-aware import workflows
- improving 3D preview quality and conversion fidelity
- stabilizing export pipelines for production use
