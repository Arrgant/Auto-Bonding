"""Local persistence for user-confirmed layer semantic roles."""

from __future__ import annotations

import json
import os
from pathlib import Path

from core.layer_semantics import normalize_layer_name


class LayerSemanticPresetStore:
    """Persist semantic layer-role presets across desktop sessions."""

    def __init__(self, path: Path | None = None):
        self.path = path or self._default_path()
        self._presets = self._load()

    def resolve_for_layers(self, layer_info: list[dict[str, object]]) -> dict[str, str]:
        """Resolve stored presets against the current DXF layer names."""

        resolved: dict[str, str] = {}
        for layer in layer_info:
            layer_name = str(layer["name"])
            role = self._presets.get(normalize_layer_name(layer_name))
            if role:
                resolved[layer_name] = role
        return resolved

    def list_presets(self) -> dict[str, str]:
        """Return all persisted presets keyed by normalized layer name."""

        return dict(sorted(self._presets.items()))

    def remember_layer_role(self, layer_name: str, role_name: str) -> None:
        """Store one user-confirmed semantic role for future imports."""

        normalized = normalize_layer_name(layer_name)
        if not normalized:
            return
        self._presets[normalized] = role_name
        self._save()

    def remove_preset(self, normalized_layer_name: str) -> None:
        """Delete one persisted preset by normalized layer name."""

        if normalized_layer_name in self._presets:
            self._presets.pop(normalized_layer_name, None)
            self._save()

    def replace_presets(self, presets: dict[str, str]) -> None:
        """Replace the entire persisted preset map."""

        self._presets = {
            str(key): str(value)
            for key, value in presets.items()
            if isinstance(key, str) and isinstance(value, str) and key
        }
        self._save()

    def clear_presets(self) -> None:
        """Remove all persisted presets."""

        if not self._presets:
            return
        self._presets.clear()
        self._save()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        presets = payload.get("layer_roles", {})
        if not isinstance(presets, dict):
            return {}
        return {
            str(key): str(value)
            for key, value in presets.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "layer_roles": dict(sorted(self._presets.items()))}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _default_path(self) -> Path:
        if os.name == "nt":
            base_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        else:
            base_dir = Path.home() / ".config"
        return base_dir / "Auto-Bonding" / "layer_semantic_presets.json"


__all__ = ["LayerSemanticPresetStore"]
