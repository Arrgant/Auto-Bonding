"""Layer-level semantic summaries derived from classified objects."""

from __future__ import annotations

from dataclasses import dataclass

from ..layer_semantics import format_layer_role, format_layer_role_ui
from .candidates import SemanticCandidate
from .entities import SemanticEntity


@dataclass(frozen=True)
class LayerSemanticSummary:
    """Stable per-layer semantic summary for UI and reporting."""

    layer_name: str
    recognized_role: str | None
    recognized_label: str
    display_label: str
    state: str
    badge_tone: str
    is_action_needed: bool
    entity_counts: dict[str, int]
    review_counts: dict[str, int]


def summarize_layers(
    entities: list[SemanticEntity],
    review: list[SemanticCandidate],
) -> list[LayerSemanticSummary]:
    """Aggregate semantic results into one summary per layer."""

    grouped: dict[str, dict[str, dict[str, int]]] = {}

    for entity in entities:
        bucket = grouped.setdefault(entity.layer_name, {"entities": {}, "review": {}})
        bucket["entities"][entity.kind] = bucket["entities"].get(entity.kind, 0) + 1

    for candidate in review:
        role_name = _candidate_role_name(candidate.kind)
        bucket = grouped.setdefault(candidate.layer_name, {"entities": {}, "review": {}})
        bucket["review"][role_name] = bucket["review"].get(role_name, 0) + 1

    summaries: list[LayerSemanticSummary] = []
    for layer_name in sorted(grouped):
        entity_counts = grouped[layer_name]["entities"]
        review_counts = grouped[layer_name]["review"]
        (
            recognized_role,
            recognized_label,
            display_label,
            state,
            badge_tone,
            is_action_needed,
        ) = _resolve_layer_summary(entity_counts, review_counts)
        summaries.append(
            LayerSemanticSummary(
                layer_name=layer_name,
                recognized_role=recognized_role,
                recognized_label=recognized_label,
                display_label=display_label,
                state=state,
                badge_tone=badge_tone,
                is_action_needed=is_action_needed,
                entity_counts=dict(entity_counts),
                review_counts=dict(review_counts),
            )
        )
    return summaries


def _candidate_role_name(candidate_kind: str) -> str:
    return str(candidate_kind).removesuffix("_candidate")


def _resolve_layer_summary(
    entity_counts: dict[str, int],
    review_counts: dict[str, int],
) -> tuple[str | None, str, str, str, str, bool]:
    entity_roles = set(entity_counts)
    review_roles = set(review_counts)
    combined_roles = entity_roles | review_roles

    if not combined_roles:
        return None, "-", "未识别", "unknown", "muted", False

    if len(entity_roles) == 1 and (not review_roles or review_roles <= entity_roles):
        role = next(iter(entity_roles))
        return role, format_layer_role(role), format_layer_role_ui(role), "resolved", "positive", False

    if not entity_roles and len(review_roles) == 1:
        role = next(iter(review_roles))
        return (
            role,
            f"{format_layer_role(role)} (Review)",
            f"{format_layer_role_ui(role)}（待确认）",
            "review",
            "warning",
            True,
        )

    if len(combined_roles) == 1:
        role = next(iter(combined_roles))
        label = format_layer_role(role)
        display_label = format_layer_role_ui(role)
        state = "resolved" if entity_roles else "review"
        badge_tone = "positive" if state == "resolved" else "warning"
        is_action_needed = state == "review"
        if state == "review":
            label = f"{label} (Review)"
            display_label = f"{display_label}（待确认）"
        return role, label, display_label, state, badge_tone, is_action_needed

    return None, "Mixed", "混合层", "mixed", "attention", True


__all__ = ["LayerSemanticSummary", "summarize_layers"]
