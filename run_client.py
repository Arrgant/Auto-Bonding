#!/usr/bin/env python3
"""Desktop launcher for the PySide6 desktop application."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REQUIRED_MODULES = ("PySide6", "cadquery", "ezdxf", "numpy")


def ensure_dependencies() -> None:
    missing = []

    for module_name in REQUIRED_MODULES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)

    if not missing:
        return

    print(f"Installing missing dependencies: {', '.join(missing)}")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(Path(__file__).with_name("requirements.txt"))]
    )


def main() -> None:
    print("Launching Auto-Bonding desktop app...")
    ensure_dependencies()

    from main import main as launch_app

    raise SystemExit(launch_app())


if __name__ == "__main__":
    main()
