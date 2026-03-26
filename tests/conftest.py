"""Shared pytest configuration."""

from __future__ import annotations

import os
import sys
import warnings

import pytest

try:
    from pyparsing.exceptions import PyparsingDeprecationWarning
except Exception:  # pragma: no cover
    PyparsingDeprecationWarning = None

if PyparsingDeprecationWarning is not None:
    warnings.filterwarnings(
        "ignore",
        category=PyparsingDeprecationWarning,
    )


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    """Configure shared markers and warning filters."""

    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session")
def test_config():
    """Common test configuration."""

    return {
        "min_wire_spacing": 0.1,
        "max_loop_height": 1.0,
        "min_pad_size": 0.2,
        "loop_height_coefficient": 1.5,
        "default_wire_diameter": 0.025,
    }
