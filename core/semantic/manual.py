"""Manual override helpers for semantic review items."""

from __future__ import annotations

from dataclasses import replace

from .classifier import SemanticClassificationResult
from .entities import SemanticEntity

MANUAL_REVIEW_KIND_OPTIONS = (
    "substrate",
    "hole",
    "round_feature",
    "module_region",
    "lead_frame",
    "pad",
    "die_region",
    "wire",
)


def apply_manual_semantic_overrides(
    result: SemanticClassificationResult,
    overrides: dict[str, str],
) -> SemanticClassificationResult:
    """Promote selected review candidates into final entities."""

    if not overrides:
        return result

    entities = list(result.entities)
    review = []

    for candidate in result.review:
        target_kind = overrides.get(candidate.id)
        if target_kind in MANUAL_REVIEW_KIND_OPTIONS:
            entities.append(
                SemanticEntity(
                    id=_manual_entity_id(candidate.id, target_kind),
                    kind=target_kind,
                    layer_name=candidate.layer_name,
                    confidence=candidate.confidence,
                    source_indices=candidate.source_indices,
                    geometry=dict(candidate.geometry),
                    properties=dict(candidate.properties)
                    | {
                        "manual_override": True,
                        "manual_source_id": candidate.id,
                    },
                )
            )
        else:
            review.append(candidate)

    return replace(result, entities=entities, review=review)


def manual_override_entity_key(candidate_id: str, target_kind: str) -> str:
    """Return the UI selection key for a manually promoted review item."""

    return f"entity:{_manual_entity_id(candidate_id, target_kind)}"


def _manual_entity_id(candidate_id: str, target_kind: str) -> str:
    sanitized = candidate_id.replace(" ", "_")
    return f"manual_{target_kind}_{sanitized}"


__all__ = [
    "MANUAL_REVIEW_KIND_OPTIONS",
    "apply_manual_semantic_overrides",
    "manual_override_entity_key",
]
