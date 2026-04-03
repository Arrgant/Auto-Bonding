"""Manual semantic override tests."""

from __future__ import annotations

from core.semantic import (
    RelationNote,
    SemanticCandidate,
    SemanticClassificationResult,
    apply_manual_semantic_overrides,
    classify_semantic_layers,
    manual_override_entity_key,
)
from core.layer_semantics import apply_layer_role_overrides, format_layer_role_ui


def test_apply_manual_semantic_overrides_promotes_review_candidate():
    result = SemanticClassificationResult(
        candidates=[],
        entities=[],
        review=[
            SemanticCandidate(
                id="substrate_candidate_7",
                kind="substrate_candidate",
                layer_name="01_substrate",
                confidence=0.73,
                source_indices=(7,),
            )
        ],
        relation_notes=[RelationNote("a", "b", "hint", 0.1)],
    )

    updated = apply_manual_semantic_overrides(result, {"substrate_candidate_7": "pad"})

    assert len(updated.review) == 0
    assert len(updated.entities) == 1
    assert updated.entities[0].kind == "pad"
    assert updated.entities[0].properties["manual_override"] is True
    assert updated.entities[0].properties["manual_source_id"] == "substrate_candidate_7"
    assert manual_override_entity_key("substrate_candidate_7", "pad") == "entity:manual_pad_substrate_candidate_7"


def test_apply_manual_semantic_overrides_supports_hole_kind():
    result = SemanticClassificationResult(
        candidates=[],
        entities=[],
        review=[
            SemanticCandidate(
                id="hole_candidate_3",
                kind="hole_candidate",
                layer_name="01_substrate",
                confidence=0.73,
                source_indices=(3,),
            )
        ],
        relation_notes=[],
    )

    updated = apply_manual_semantic_overrides(result, {"hole_candidate_3": "hole"})

    assert len(updated.review) == 0
    assert len(updated.entities) == 1
    assert updated.entities[0].kind == "hole"


def test_apply_manual_semantic_overrides_supports_round_feature_kind():
    result = SemanticClassificationResult(
        candidates=[],
        entities=[],
        review=[
            SemanticCandidate(
                id="round_feature_candidate_9",
                kind="round_feature_candidate",
                layer_name="01_substrate",
                confidence=0.74,
                source_indices=(9,),
                properties={"rule_source": "substrate_concentric_round"},
            )
        ],
        relation_notes=[],
    )

    updated = apply_manual_semantic_overrides(result, {"round_feature_candidate_9": "round_feature"})

    assert len(updated.review) == 0
    assert len(updated.entities) == 1
    assert updated.entities[0].kind == "round_feature"
    assert updated.entities[0].properties["manual_source_id"] == "round_feature_candidate_9"
    assert updated.entities[0].properties["rule_source"] == "substrate_concentric_round"


def test_apply_layer_role_overrides_replaces_suggested_role():
    layer_info = [
        {
            "name": "06_misc",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": None,
            "enabled": True,
            "entity_count": 1,
            "entity_types": {"LINE": 1},
        }
    ]

    updated = apply_layer_role_overrides(layer_info, {"06_misc": "wire"})

    assert updated[0]["suggested_role"] == "wire"
    assert layer_info[0]["suggested_role"] is None


def test_layer_role_override_changes_semantic_classification():
    raw_entities = [{"type": "LINE", "start": (0.0, 0.0), "end": (8.0, 0.0), "layer": "06_misc"}]
    layer_info = [
        {
            "name": "06_misc",
            "color": 7,
            "linetype": "CONTINUOUS",
            "is_off": False,
            "is_frozen": False,
            "is_locked": False,
            "is_visible": True,
            "plot": True,
            "mapped_type": None,
            "suggested_role": None,
            "enabled": True,
            "entity_count": 1,
            "entity_types": {"LINE": 1},
        }
    ]

    base_result = classify_semantic_layers(raw_entities, layer_info)
    overridden_result = classify_semantic_layers(
        raw_entities,
        apply_layer_role_overrides(layer_info, {"06_misc": "wire"}),
    )

    assert len(base_result.entities) == 0
    assert len(base_result.review) == 0
    assert {candidate.kind for candidate in overridden_result.review} == {"wire_candidate"}


def test_manual_override_updates_layer_summary_for_round_feature():
    result = SemanticClassificationResult(
        candidates=[],
        entities=[],
        review=[
            SemanticCandidate(
                id="round_feature_candidate_9",
                kind="round_feature_candidate",
                layer_name="01_substrate",
                confidence=0.74,
                source_indices=(9,),
                properties={"rule_source": "substrate_concentric_round"},
            )
        ],
        relation_notes=[],
    )

    updated = apply_manual_semantic_overrides(result, {"round_feature_candidate_9": "round_feature"})
    summaries = {summary.layer_name: summary for summary in updated.layer_summaries}

    assert summaries["01_substrate"].recognized_role == "round_feature"
    assert summaries["01_substrate"].recognized_label == "Round Feature"
    assert summaries["01_substrate"].display_label == format_layer_role_ui("round_feature")
    assert summaries["01_substrate"].state == "resolved"
    assert summaries["01_substrate"].badge_tone == "positive"
    assert summaries["01_substrate"].is_action_needed is False
