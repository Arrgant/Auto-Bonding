"""Local persistence for wire production recipe templates."""

from __future__ import annotations

import json
import os
from pathlib import Path

from core.export.wire_recipe_models import WireRecipeTemplate


class WireRecipeTemplateStore:
    """Persist export templates across desktop sessions."""

    def __init__(self, path: Path | None = None):
        self.path = path or self._default_path()
        self._templates = self._load()

    def list_templates(self) -> list[WireRecipeTemplate]:
        """Return all templates in stable display order."""

        return sorted(self._templates.values(), key=lambda item: (item.name.lower(), item.template_id))

    def get_template(self, template_id: str) -> WireRecipeTemplate | None:
        """Return one template by id when available."""

        return self._templates.get(template_id)

    def save_template(self, template: WireRecipeTemplate) -> None:
        """Create or replace one template."""

        self._templates[template.template_id] = template
        self._save()

    def delete_template(self, template_id: str) -> None:
        """Delete one persisted template by id."""

        if template_id in self._templates:
            self._templates.pop(template_id, None)
            self._save()

    def replace_templates(self, templates: list[WireRecipeTemplate]) -> None:
        """Replace the entire persisted template set."""

        self._templates = {template.template_id: template for template in templates}
        self._save()

    def _load(self) -> dict[str, WireRecipeTemplate]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        items = payload.get("templates", [])
        if not isinstance(items, list):
            return {}

        templates: dict[str, WireRecipeTemplate] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                template = WireRecipeTemplate.from_payload(item)
            except Exception:
                continue
            templates[template.template_id] = template
        return templates

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "templates": [template.to_payload() for template in self.list_templates()],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _default_path(self) -> Path:
        if os.name == "nt":
            base_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        else:
            base_dir = Path.home() / ".config"
        return base_dir / "Auto-Bonding" / "wire_export_templates.json"


__all__ = ["WireRecipeTemplateStore"]
