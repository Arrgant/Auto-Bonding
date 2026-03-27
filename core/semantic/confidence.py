"""Confidence helpers for semantic recognition."""

from __future__ import annotations

from typing import Literal


ConfidenceBand = Literal["auto", "review", "fallback"]


def clamp_confidence(value: float) -> float:
    """Clamp one confidence score into the [0, 1] range."""

    return max(0.0, min(1.0, float(value)))


def bump_confidence(value: float, *bonuses: float) -> float:
    """Apply one or more bonuses and clamp the final score."""

    total = float(value)
    for bonus in bonuses:
        total += float(bonus)
    return clamp_confidence(total)


def confidence_band(value: float) -> ConfidenceBand:
    """Map one confidence score into the rule-table review bands."""

    score = clamp_confidence(value)
    if score >= 0.85:
        return "auto"
    if score >= 0.60:
        return "review"
    return "fallback"


__all__ = ["ConfidenceBand", "bump_confidence", "clamp_confidence", "confidence_band"]
