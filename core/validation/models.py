"""Shared DRC data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DRCMode(Enum):
    """DRC check mode."""

    STANDARD = "standard"
    IGBT = "igbt"
    AUTOMOTIVE = "automotive"


@dataclass
class DRCViolation:
    """One DRC violation record."""

    violation_type: str
    severity: str
    description: str
    actual_value: float
    required_value: float
    location: Optional[dict[str, float]] = None
    rule_category: str = "general"
