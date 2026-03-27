"""Layer semantic preset persistence tests."""

from __future__ import annotations

from services import LayerSemanticPresetStore


def test_layer_semantic_preset_store_round_trips_and_resolves(tmp_path):
    store_path = tmp_path / "layer_semantics.json"
    store = LayerSemanticPresetStore(store_path)
    store.remember_layer_role("06_misc", "wire")

    reloaded = LayerSemanticPresetStore(store_path)
    resolved = reloaded.resolve_for_layers(
        [
            {"name": "06_misc"},
            {"name": "04_pad"},
        ]
    )

    assert resolved == {"06_misc": "wire"}


def test_layer_semantic_preset_store_uses_normalized_layer_names(tmp_path):
    store = LayerSemanticPresetStore(tmp_path / "layer_semantics.json")
    store.remember_layer_role("06 Misc", "wire")

    resolved = store.resolve_for_layers([{"name": "06_MISC"}])

    assert resolved == {"06_MISC": "wire"}


def test_layer_semantic_preset_store_can_replace_and_clear(tmp_path):
    store = LayerSemanticPresetStore(tmp_path / "layer_semantics.json")
    store.remember_layer_role("06_misc", "wire")
    store.replace_presets({"04_PAD": "pad"})

    assert store.list_presets() == {"04_PAD": "pad"}

    store.clear_presets()

    assert store.list_presets() == {}
