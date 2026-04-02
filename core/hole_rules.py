"""Shared heuristics for distinguishing holes from round features."""

from __future__ import annotations


def substrate_edge_contacts(
    feature_bbox: tuple[float, float, float, float],
    substrate_bbox: tuple[float, float, float, float],
) -> tuple[str, ...]:
    """Return which substrate edges a round feature sits near."""

    substrate_width = max(substrate_bbox[2] - substrate_bbox[0], 1e-6)
    substrate_height = max(substrate_bbox[3] - substrate_bbox[1], 1e-6)
    margin_x = max(substrate_width * 0.16, 0.5)
    margin_y = max(substrate_height * 0.16, 0.5)

    contacts: list[str] = []
    if feature_bbox[0] - substrate_bbox[0] <= margin_x:
        contacts.append("left")
    if substrate_bbox[2] - feature_bbox[2] <= margin_x:
        contacts.append("right")
    if feature_bbox[1] - substrate_bbox[1] <= margin_y:
        contacts.append("bottom")
    if substrate_bbox[3] - feature_bbox[3] <= margin_y:
        contacts.append("top")
    return tuple(contacts)


def classify_substrate_round_feature(
    feature_bbox: tuple[float, float, float, float],
    substrate_bbox: tuple[float, float, float, float],
    *,
    repeated_count: int = 1,
    concentric_count: int = 1,
) -> tuple[str, tuple[str, ...]]:
    """Classify a substrate-local round feature as mounting hole, tooling hole, or plain round feature."""

    contacts = substrate_edge_contacts(feature_bbox, substrate_bbox)
    feature_diameter = max(feature_bbox[2] - feature_bbox[0], feature_bbox[3] - feature_bbox[1], 0.0)
    substrate_span = max(substrate_bbox[2] - substrate_bbox[0], substrate_bbox[3] - substrate_bbox[1], 1.0)
    relative_diameter = feature_diameter / substrate_span

    if concentric_count >= 2:
        return "round_feature", contacts
    if len(contacts) >= 2:
        return "mounting", contacts
    if len(contacts) == 1:
        return "tooling", contacts
    if repeated_count >= 2 and relative_diameter <= 0.20:
        return "tooling", contacts
    if relative_diameter <= 0.06:
        return "tooling", contacts
    return "round_feature", contacts


__all__ = ["classify_substrate_round_feature", "substrate_edge_contacts"]
