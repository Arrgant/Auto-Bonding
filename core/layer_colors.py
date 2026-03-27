"""Stable per-layer color helpers shared by 2D and 3D previews."""

from __future__ import annotations

from .layer_stack import build_layer_order_map
from .raw_dxf_types import LayerInfo, RawEntity


LAYER_COLOR_PALETTE = [
    "#FF8A65",
    "#4DD0E1",
    "#81C784",
    "#BA68C8",
    "#FFD54F",
    "#64B5F6",
    "#F06292",
    "#AED581",
    "#FFB74D",
    "#7986CB",
]


def build_layer_color_map(layer_info: list[LayerInfo], raw_entities: list[RawEntity]) -> dict[str, str]:
    """Assign one stable preview color to every layer name."""

    order_map = build_layer_order_map(layer_info, raw_entities)
    ordered_layers = sorted(order_map, key=order_map.get)
    return {
        layer_name: LAYER_COLOR_PALETTE[index % len(LAYER_COLOR_PALETTE)]
        for index, layer_name in enumerate(ordered_layers)
    }


def hex_to_rgb(color_hex: str) -> tuple[int, int, int]:
    """Convert a #RRGGBB string into an RGB tuple."""

    normalized = color_hex.lstrip("#")
    if len(normalized) != 6:
        return 232, 232, 232
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))


def tint_color(color_hex: str, *, ratio: float, towards: str = "white") -> str:
    """Blend one hex color toward white or black for fills and highlights."""

    red, green, blue = hex_to_rgb(color_hex)
    target = 255 if towards == "white" else 0

    def blend(channel: int) -> int:
        return max(0, min(255, round(channel + ((target - channel) * ratio))))

    return "#{:02X}{:02X}{:02X}".format(blend(red), blend(green), blend(blue))


__all__ = ["LAYER_COLOR_PALETTE", "build_layer_color_map", "hex_to_rgb", "tint_color"]
