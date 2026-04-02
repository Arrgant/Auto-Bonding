"""Template models for wire production export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from .wire_models import WireOrderingConfig

TemplateScalar: TypeAlias = int | float | str | bool
WB1RecordOverrideValue: TypeAlias = int | str


@dataclass(frozen=True)
class WireRecipeTemplate:
    """Persisted non-coordinate defaults for one machine recipe."""

    template_id: str
    name: str
    machine_type: str = "RX2000"
    wb1_template_path: str | None = None
    xlsm_template_path: str | None = None
    coord_scale: float = 1.0
    default_z: float = 0.0
    ordering: WireOrderingConfig = field(default_factory=WireOrderingConfig)
    header_defaults: dict[str, TemplateScalar] = field(default_factory=dict)
    pfile_field_map: dict[str, str] = field(default_factory=dict)
    pfile_named_defaults: dict[str, TemplateScalar] = field(default_factory=dict)
    pfile_cell_overrides: dict[str, TemplateScalar] = field(default_factory=dict)
    record_defaults: dict[str, TemplateScalar] = field(default_factory=dict)
    role_record_defaults: dict[str, dict[str, TemplateScalar]] = field(default_factory=dict)
    wb1_field_map: dict[str, int] = field(default_factory=dict)
    wb1_record_defaults: dict[int, WB1RecordOverrideValue] = field(default_factory=dict)
    wb1_role_codes: dict[str, WB1RecordOverrideValue] = field(
        default_factory=lambda: {"first": 0, "second": 2}
    )

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe payload for local persistence."""

        return {
            "template_id": self.template_id,
            "name": self.name,
            "machine_type": self.machine_type,
            "wb1_template_path": self.wb1_template_path,
            "xlsm_template_path": self.xlsm_template_path,
            "coord_scale": self.coord_scale,
            "default_z": self.default_z,
            "ordering": {
                "primary_axis": self.ordering.primary_axis,
                "primary_direction": self.ordering.primary_direction,
                "secondary_direction": self.ordering.secondary_direction,
                "start_role": self.ordering.start_role,
                "group_no": self.ordering.group_no,
            },
            "header_defaults": dict(self.header_defaults),
            "pfile_field_map": dict(self.pfile_field_map),
            "pfile_named_defaults": dict(self.pfile_named_defaults),
            "pfile_cell_overrides": dict(self.pfile_cell_overrides),
            "record_defaults": dict(self.record_defaults),
            "role_record_defaults": {
                role: dict(values) for role, values in sorted(self.role_record_defaults.items())
            },
            "wb1_field_map": dict(self.wb1_field_map),
            "wb1_record_defaults": {
                str(index): value for index, value in sorted(self.wb1_record_defaults.items())
            },
            "wb1_role_codes": dict(self.wb1_role_codes),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "WireRecipeTemplate":
        """Build a template from persisted JSON data."""

        ordering_payload = payload.get("ordering", {})
        ordering = WireOrderingConfig(
            primary_axis=str(ordering_payload.get("primary_axis", "x")),  # type: ignore[arg-type]
            primary_direction=str(ordering_payload.get("primary_direction", "asc")),  # type: ignore[arg-type]
            secondary_direction=str(ordering_payload.get("secondary_direction", "asc")),  # type: ignore[arg-type]
            start_role=str(ordering_payload.get("start_role", "first")),  # type: ignore[arg-type]
            group_no=int(ordering_payload.get("group_no", 1)),
        )

        return cls(
            template_id=str(payload["template_id"]),
            name=str(payload["name"]),
            machine_type=str(payload.get("machine_type", "RX2000")),
            wb1_template_path=_optional_str(payload.get("wb1_template_path")),
            xlsm_template_path=_optional_str(payload.get("xlsm_template_path")),
            coord_scale=float(payload.get("coord_scale", 1.0)),
            default_z=float(payload.get("default_z", 0.0)),
            ordering=ordering,
            header_defaults=_coerce_scalar_mapping(payload.get("header_defaults")),
            pfile_field_map=_coerce_pfile_field_map(payload.get("pfile_field_map")),
            pfile_named_defaults=_coerce_scalar_mapping(payload.get("pfile_named_defaults")),
            pfile_cell_overrides=_coerce_cell_override_mapping(payload.get("pfile_cell_overrides")),
            record_defaults=_coerce_scalar_mapping(payload.get("record_defaults")),
            role_record_defaults=_coerce_role_scalar_mapping(payload.get("role_record_defaults")),
            wb1_field_map=_coerce_int_mapping(payload.get("wb1_field_map")),
            wb1_record_defaults=_coerce_record_defaults(payload.get("wb1_record_defaults")),
            wb1_role_codes=_coerce_role_codes(payload.get("wb1_role_codes")),
        )

    def resolve_pfile_cell_overrides(self) -> dict[str, TemplateScalar]:
        """Return merged PFILE overrides with raw cell edits taking precedence."""

        resolved: dict[str, TemplateScalar] = {}
        for field_name, value in self.pfile_named_defaults.items():
            cell_ref = self.pfile_field_map.get(field_name)
            if cell_ref:
                resolved[cell_ref] = value
        resolved.update(self.pfile_cell_overrides)
        return resolved


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_scalar_mapping(value: object) -> dict[str, TemplateScalar]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, TemplateScalar] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(item, (bool, int, float, str)):
            coerced[key] = item
    return coerced


def _coerce_int_mapping(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, int] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        try:
            coerced[key] = int(item)
        except (TypeError, ValueError):
            continue
    return coerced


def _coerce_cell_override_mapping(value: object) -> dict[str, TemplateScalar]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, TemplateScalar] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        cell_ref = key.strip().upper()
        if not cell_ref:
            continue
        if isinstance(item, (bool, int, float, str)):
            coerced[cell_ref] = item
    return coerced


def _coerce_pfile_field_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        field_name = key.strip()
        if not field_name:
            continue
        cell_ref = _normalize_cell_ref(item)
        if cell_ref is not None:
            coerced[field_name] = cell_ref
    return coerced


def _coerce_role_scalar_mapping(value: object) -> dict[str, dict[str, TemplateScalar]]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, dict[str, TemplateScalar]] = {}
    for role, item in value.items():
        if not isinstance(role, str):
            continue
        nested = _coerce_scalar_mapping(item)
        if nested:
            coerced[role] = nested
    return coerced


def _coerce_record_defaults(value: object) -> dict[int, WB1RecordOverrideValue]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[int, WB1RecordOverrideValue] = {}
    for key, item in value.items():
        try:
            index = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(item, (int, str)):
            coerced[index] = item
    return coerced


def _coerce_role_codes(value: object) -> dict[str, WB1RecordOverrideValue]:
    if not isinstance(value, dict):
        return {"first": 0, "second": 2}
    coerced: dict[str, WB1RecordOverrideValue] = {}
    for key, item in value.items():
        if key not in {"first", "second"}:
            continue
        if isinstance(item, (int, str)):
            coerced[key] = item
    return coerced or {"first": 0, "second": 2}


def _normalize_cell_ref(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


__all__ = [
    "TemplateScalar",
    "WB1RecordOverrideValue",
    "WireRecipeTemplate",
]
