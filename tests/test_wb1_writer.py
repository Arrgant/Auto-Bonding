from __future__ import annotations

from core.export.wb1_writer import WB1Writer
from core.export.wire_models import OrderedWireRecord, WireGeometry, WireOrderingConfig, WirePoint
from core.export.wire_recipe_models import WireRecipeTemplate


def test_wb1_writer_replaces_j_records_from_ordered_wires(tmp_path):
    template_path = tmp_path / "template.WB1"
    template_path.write_text(
        "\n".join(
            [
                "0000,544553542E5742310000,",
                "H,",
                "0000,",
                "J,",
                "0000,0000,0000,0000,0000,0000,",
                "0002,0000,0000,0000,0000,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_template_path=str(template_path),
        coord_scale=10.0,
        default_z=7.0,
        ordering=WireOrderingConfig(group_no=4),
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "bond_x": 2,
            "bond_y": 3,
            "bond_z": 4,
            "group_no": 5,
            "search_speed": 6,
        },
        wb1_record_defaults={5: 4},
        record_defaults={"search_speed": 240},
    )

    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0001",
            wire_seq=1,
            group_no=4,
            first_point_seq=1,
            second_point_seq=2,
            geometry=_wire_geometry("W0001", (1.0, 2.0), (3.5, 4.5)),
        )
    ]

    content = WB1Writer().render(ordered_wires, template, output_name="DEMO.WB1")
    lines = content.splitlines()

    assert lines[0] == "0000,44454D4F2E5742310000,"
    assert lines[3] == "J,"
    assert lines[4] == "0000,0001,000A,0014,0046,0004,00F0,"
    assert lines[5] == "0002,0001,0023,002D,0046,0004,00F0,"
    assert lines[6] == "Q"


def test_wb1_writer_creates_records_when_template_j_section_is_empty(tmp_path):
    template_path = tmp_path / "empty-template.WB1"
    template_path.write_text(
        "\n".join(
            [
                "0000,454D5054592E5742310000,",
                "J,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="empty",
        name="Empty",
        wb1_template_path=str(template_path),
        wb1_field_map={"role_code": 0, "bond_x": 1, "bond_y": 2},
    )

    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0002",
            wire_seq=3,
            group_no=1,
            first_point_seq=5,
            second_point_seq=6,
            geometry=_wire_geometry("W0002", (1.0, 0.0), (2.0, 1.0)),
        )
    ]

    content = WB1Writer().render(ordered_wires, template, output_name="EMPTY.WB1")
    lines = content.splitlines()

    assert lines[1] == "J,"
    assert lines[2].startswith("0000,0001,0000")
    assert lines[3].startswith("0002,0002,0001")
    assert lines[4] == "Q"


def _wire_geometry(wire_id: str, first_xy: tuple[float, float], second_xy: tuple[float, float]) -> WireGeometry:
    first_point = WirePoint(point_id=f"{wire_id}-P1", wire_id=wire_id, role="first", x=first_xy[0], y=first_xy[1])
    second_point = WirePoint(
        point_id=f"{wire_id}-P2",
        wire_id=wire_id,
        role="second",
        x=second_xy[0],
        y=second_xy[1],
    )
    return WireGeometry(
        wire_id=wire_id,
        layer_name="06_wire",
        source_type="LINE",
        source_entity_indices=(0,),
        route_points=(first_xy, second_xy),
        first_point=first_point,
        second_point=second_point,
        length=1.0,
        angle_deg=0.0,
        bbox=(min(first_xy[0], second_xy[0]), min(first_xy[1], second_xy[1]), max(first_xy[0], second_xy[0]), max(first_xy[1], second_xy[1])),
    )
