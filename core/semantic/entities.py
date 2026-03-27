"""Semantic entity models for accepted DXF recognition results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticEntity:
    """Final semantic object promoted from one or more candidates."""

    id: str
    kind: str
    layer_name: str
    confidence: float
    source_indices: tuple[int, ...]
    geometry: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)


__all__ = ["SemanticEntity"]
