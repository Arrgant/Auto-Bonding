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
        role_record_defaults={
            "first": {"search_speed": 50},
            "second": {"search_speed": 99},
        },
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
    assert lines[4] == "0000,0001,000A,0014,0046,0004,0032,"
    assert lines[5] == "0002,0001,0023,002D,0046,0004,0063,"
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


def test_wb1_writer_applies_rx2000_role_defaults_after_shared_defaults(tmp_path):
    template_path = tmp_path / "rx-template.WB1"
    template_path.write_text(
        "\n".join(
            [
                "0000,52582E5742310000,",
                "J,",
                "0000,0000,0000,0000,0000,0000,0000,0000,0000,0000,0000,0000,",
                "0002,0000,0000,0000,0000,0000,0000,0000,0000,0000,0000,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="rx",
        name="RX",
        wb1_template_path=str(template_path),
        coord_scale=5.0,
        default_z=1455.2,
        wb1_field_map={
            "role_code": 0,
            "loop_setting": 2,
            "us_power_p": 9,
            "us_power_l": 10,
            "us_time_p": 11,
            "search_speed": 13,
            "bond_x": 38,
            "bond_y": 40,
            "bond_z": 42,
        },
        record_defaults={"us_power_l": 135},
        role_record_defaults={
            "first": {"loop_setting": 55, "us_power_p": 40, "us_time_p": 10, "search_speed": 50},
            "second": {"loop_setting": 50, "us_power_p": 0, "us_time_p": 0, "search_speed": 99},
        },
        wb1_role_codes={"first": 0, "second": 2},
    )

    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0003",
            wire_seq=7,
            group_no=1,
            first_point_seq=13,
            second_point_seq=14,
            geometry=_wire_geometry("W0003", (1.0, 2.0), (3.0, 4.0)),
        )
    ]

    lines = WB1Writer().render(ordered_wires, template, output_name="RX.WB1").splitlines()
    first_record = [token for token in lines[2].split(",") if token]
    second_record = [token for token in lines[3].split(",") if token]

    assert first_record[2] == "0037"
    assert first_record[9] == "0028"
    assert first_record[10] == "0087"
    assert first_record[11] == "000A"
    assert first_record[13] == "0032"
    assert second_record[2] == "0032"
    assert second_record[9] == "0000"
    assert second_record[10] == "0087"
    assert second_record[11] == "0000"
    assert second_record[13] == "0063"


def test_wb1_writer_applies_role_specific_named_defaults(tmp_path):
    template_path = tmp_path / "role-template.WB1"
    template_path.write_text(
        "\n".join(
            [
                "0000,524F4C452E5742310000,",
                "J,",
                "0000,0000,0000,0000,0000,0000,0000,",
                "0002,0000,0000,0000,0000,0000,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="role",
        name="Role",
        wb1_template_path=str(template_path),
        coord_scale=5.0,
        default_z=100.0,
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "search_speed": 2,
            "pull_height": 3,
            "bond_z": 4,
            "contact_surface_position": 5,
            "group_no": 6,
        },
        record_defaults={"pull_height": 20},
        role_record_defaults={
            "first": {"search_speed": 50, "contact_surface_position": 7316},
            "second": {"search_speed": 99, "pull_height": 250, "contact_surface_position": 7331},
        },
    )

    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0100",
            wire_seq=7,
            group_no=3,
            first_point_seq=13,
            second_point_seq=14,
            geometry=_wire_geometry("W0100", (1.0, 2.0), (3.0, 4.0)),
        )
    ]

    content = WB1Writer().render(ordered_wires, template, output_name="ROLE.WB1")
    lines = content.splitlines()

    assert lines[2] == "0000,0007,0032,0014,01F4,1C94,0003,"
    assert lines[3] == "0002,0007,0063,00FA,01F4,1CA3,0003,"


def test_wb1_writer_applies_header_defaults_to_preamble_and_sections(tmp_path):
    template_path = tmp_path / "header-template.WB1"
    template_path.write_text(
        "\n".join(
            [
                "0000,4845414445522E5742310000,",
                "0004,0001,0000,0016,",
                "0000,0000,",
                "G,",
                "0000,0000,",
                "H,",
                "0000,0000,0000,",
                "J,",
                "0000,0000,",
                "0002,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="header",
        name="Header",
        wb1_template_path=str(template_path),
        header_defaults={
            "PRE:1:2": 45,
            "G:0:1": 50,
            "H:0:2": "00FF",
        },
        wb1_field_map={"role_code": 0},
    )

    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0200",
            wire_seq=1,
            group_no=1,
            first_point_seq=1,
            second_point_seq=2,
            geometry=_wire_geometry("W0200", (1.0, 2.0), (3.0, 4.0)),
        )
    ]

    lines = WB1Writer().render(ordered_wires, template, output_name="NEW.WB1").splitlines()

    assert lines[0] == "0000,4E45572E5742310000,"
    assert lines[1] == "0004,0001,002D,0016,"
    assert lines[4] == "0000,0032,"
    assert lines[6] == "0000,0000,00FF,"


def test_wb1_writer_can_optionally_derive_bond_angle_from_wire_vector_plus_90(tmp_path):
    template_path = tmp_path / "angle-template.WB1"
    template_path.write_text(
        "\n".join(
            [
                "0000,414E474C452E5742310000,",
                "J,",
                "0000,0000,0000,",
                "0002,0000,0000,",
                "Q",
            ]
        ),
        encoding="utf-8",
    )

    template = WireRecipeTemplate(
        template_id="angle",
        name="Angle",
        wb1_template_path=str(template_path),
        bond_angle_mode="wire_vector",
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "bond_angle": 2,
        },
    )

    ordered_wires = [
        OrderedWireRecord(
            wire_id="W0300",
            wire_seq=1,
            group_no=1,
            first_point_seq=1,
            second_point_seq=2,
            geometry=_wire_geometry("W0300", (0.0, 0.0), (10.0, 10.0), angle_deg=45.0),
        )
    ]

    lines = WB1Writer().render(ordered_wires, template, output_name="ANGLE.WB1").splitlines()

    assert lines[2] == "0000,0001,0087,"
    assert lines[3] == "0002,0001,0087,"


def _wire_geometry(
    wire_id: str,
    first_xy: tuple[float, float],
    second_xy: tuple[float, float],
    *,
    angle_deg: float = 0.0,
) -> WireGeometry:
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
        angle_deg=angle_deg,
        bbox=(min(first_xy[0], second_xy[0]), min(first_xy[1], second_xy[1]), max(first_xy[0], second_xy[0]), max(first_xy[1], second_xy[1])),
    )
