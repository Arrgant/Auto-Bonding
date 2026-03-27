"""Fallback promotion helpers for semantic recognition."""

from __future__ import annotations

from .candidates import SemanticCandidate
from .confidence import confidence_band
from .entities import SemanticEntity


def finalize_candidates(
    candidates: list[SemanticCandidate],
) -> tuple[list[SemanticEntity], list[SemanticCandidate]]:
    """Split candidates into accepted semantic entities and review objects."""

    entities: list[SemanticEntity] = []
    review: list[SemanticCandidate] = []

    for candidate in candidates:
        band = confidence_band(candidate.confidence)
        if band == "auto":
            entities.append(
                SemanticEntity(
                    id=candidate.id.replace("_candidate", ""),
                    kind=candidate.kind.removesuffix("_candidate"),
                    layer_name=candidate.layer_name,
                    confidence=candidate.confidence,
                    source_indices=candidate.source_indices,
                    geometry=dict(candidate.geometry),
                    properties=dict(candidate.properties),
                )
            )
        else:
            review.append(candidate)

    return entities, review


__all__ = ["finalize_candidates"]
