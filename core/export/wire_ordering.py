"""Deterministic wire ordering helpers for production export."""

from __future__ import annotations

from .wire_models import OrderedWireRecord, WireGeometry, WireOrderingConfig


def order_wire_geometries(
    wires: list[WireGeometry],
    config: WireOrderingConfig | None = None,
) -> list[OrderedWireRecord]:
    """Return a reproducible wire order and paired point sequence numbers."""

    resolved = config or WireOrderingConfig()
    ordered_wires = sorted(wires, key=lambda wire: _order_key(wire, resolved))
    records: list[OrderedWireRecord] = []

    for index, wire in enumerate(ordered_wires, start=1):
        first_point_seq = (index * 2) - 1
        second_point_seq = index * 2
        if resolved.start_role == "second":
            first_point_seq, second_point_seq = second_point_seq, first_point_seq

        records.append(
            OrderedWireRecord(
                wire_id=wire.wire_id,
                wire_seq=index,
                group_no=resolved.group_no,
                first_point_seq=first_point_seq,
                second_point_seq=second_point_seq,
                geometry=wire,
            )
        )

    return records


def _order_key(wire: WireGeometry, config: WireOrderingConfig) -> tuple[float, float, str]:
    centroid_x, centroid_y = wire.centroid
    primary_value = centroid_x if config.primary_axis == "x" else centroid_y
    secondary_value = centroid_y if config.primary_axis == "x" else centroid_x
    if config.primary_direction == "desc":
        primary_value *= -1
    if config.secondary_direction == "desc":
        secondary_value *= -1
    return (primary_value, secondary_value, wire.wire_id)


__all__ = ["order_wire_geometries"]
