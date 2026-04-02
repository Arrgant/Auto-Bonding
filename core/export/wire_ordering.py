"""Deterministic wire ordering helpers for production export."""

from __future__ import annotations

import math
import statistics

from .wire_models import OrderedWireRecord, WireGeometry, WireOrderingConfig


def order_wire_geometries(
    wires: list[WireGeometry],
    config: WireOrderingConfig | None = None,
) -> list[OrderedWireRecord]:
    """Return a reproducible wire order and paired point sequence numbers."""

    resolved = config or WireOrderingConfig()
    grouped_wires = _group_and_order_wires(wires, resolved)
    records: list[OrderedWireRecord] = []

    for index, (wire, group_no) in enumerate(grouped_wires, start=1):
        first_point_seq = (index * 2) - 1
        second_point_seq = index * 2
        if resolved.start_role == "second":
            first_point_seq, second_point_seq = second_point_seq, first_point_seq

        records.append(
            OrderedWireRecord(
                wire_id=wire.wire_id,
                wire_seq=index,
                group_no=group_no,
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


def _group_and_order_wires(
    wires: list[WireGeometry],
    config: WireOrderingConfig,
) -> list[tuple[WireGeometry, int]]:
    if not wires:
        return []
    if config.group_mode != "clustered" or len(wires) == 1:
        ordered_wires = sorted(wires, key=lambda wire: _order_key(wire, config))
        return [(wire, config.group_no) for wire in ordered_wires]

    components = _cluster_wire_components(wires)
    ordered_components = sorted(components, key=lambda component: _component_order_key(component, config))

    grouped: list[tuple[WireGeometry, int]] = []
    for group_offset, component in enumerate(ordered_components):
        group_no = config.group_no + group_offset
        for wire in sorted(component, key=lambda item: _order_key(item, config)):
            grouped.append((wire, group_no))
    return grouped


def _cluster_wire_components(wires: list[WireGeometry]) -> list[list[WireGeometry]]:
    epsilon_x, epsilon_y = _component_epsilons(wires)
    remaining = set(range(len(wires)))
    components: list[list[WireGeometry]] = []

    while remaining:
        seed_index = min(remaining)
        queue = [seed_index]
        component_indices: set[int] = set()
        remaining.remove(seed_index)

        while queue:
            current_index = queue.pop()
            if current_index in component_indices:
                continue
            component_indices.add(current_index)
            current_wire = wires[current_index]

            linked_indices = []
            for candidate_index in sorted(remaining):
                candidate_wire = wires[candidate_index]
                if _wires_are_cluster_neighbors(current_wire, candidate_wire, epsilon_x, epsilon_y):
                    linked_indices.append(candidate_index)

            for linked_index in linked_indices:
                remaining.remove(linked_index)
                queue.append(linked_index)

        components.append([wires[index] for index in sorted(component_indices)])

    return components


def _component_epsilons(wires: list[WireGeometry]) -> tuple[float, float]:
    x_values = sorted(wire.centroid[0] for wire in wires)
    y_values = sorted(wire.centroid[1] for wire in wires)
    wire_scale = max(statistics.median([wire.length for wire in wires]), 1.0)
    return (_axis_epsilon(x_values, wire_scale), _axis_epsilon(y_values, wire_scale))


def _axis_epsilon(values: list[float], wire_scale: float) -> float:
    positive_gaps = sorted(
        gap
        for gap in (right - left for left, right in zip(values, values[1:]))
        if gap > 0
    )
    if not positive_gaps:
        return max(wire_scale * 3.0, 1.0)
    baseline = positive_gaps[max(0, int(math.floor((len(positive_gaps) - 1) * 0.25)))]
    return max(min(baseline * 3.0, wire_scale * 3.0), 1.0)


def _wires_are_cluster_neighbors(
    first: WireGeometry,
    second: WireGeometry,
    epsilon_x: float,
    epsilon_y: float,
) -> bool:
    gap_x = _bbox_gap(first.bbox[0], first.bbox[2], second.bbox[0], second.bbox[2])
    gap_y = _bbox_gap(first.bbox[1], first.bbox[3], second.bbox[1], second.bbox[3])
    return gap_x <= epsilon_x and gap_y <= epsilon_y


def _bbox_gap(first_min: float, first_max: float, second_min: float, second_max: float) -> float:
    if first_max < second_min:
        return second_min - first_max
    if second_max < first_min:
        return first_min - second_max
    return 0.0


def _component_order_key(component: list[WireGeometry], config: WireOrderingConfig) -> tuple[float, float]:
    centroid_x = sum(wire.centroid[0] for wire in component) / len(component)
    centroid_y = sum(wire.centroid[1] for wire in component) / len(component)
    primary_value = centroid_x if config.primary_axis == "x" else centroid_y
    secondary_value = centroid_y if config.primary_axis == "x" else centroid_x
    if config.primary_direction == "desc":
        primary_value *= -1
    if config.secondary_direction == "desc":
        secondary_value *= -1
    return (primary_value, secondary_value)


__all__ = ["order_wire_geometries"]
