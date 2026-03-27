"""Semantic candidate models for staged DXF recognition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticCandidate:
    """Intermediate semantic object proposed by rule-based recognition."""

    id: str
    kind: str
    layer_name: str
    confidence: float
    source_indices: tuple[int, ...]
    geometry: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)


__all__ = ["SemanticCandidate"]
