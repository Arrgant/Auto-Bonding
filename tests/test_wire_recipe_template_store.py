from __future__ import annotations

from core.export import build_rx2000_default_template
from core.export.wire_recipe_models import WireRecipeTemplate
from core.export.wire_models import WireOrderingConfig
from services import WireRecipeTemplateStore


def test_wire_recipe_template_store_round_trips_templates(tmp_path):
    store_path = tmp_path / "wire_templates.json"
    store = WireRecipeTemplateStore(store_path)
    template = WireRecipeTemplate(
        template_id="rx2000-default",
        name="RX2000 Default",
        machine_type="RX2000",
        wb1_template_path="C:/fixtures/sample.WB1",
        xlsm_template_path="C:/fixtures/sample.xlsm",
        coord_scale=5.0,
        default_z=320.0,
        ordering=WireOrderingConfig(primary_axis="y", group_no=3),
        header_defaults={"wire_size_code": 3},
        record_defaults={"search_speed": 9900},
        wb1_field_map={"wire_seq": 1, "bond_x": 2},
        wb1_record_defaults={5: 100, 6: "00F0"},
        wb1_role_codes={"first": 0, "second": 2},
    )

    store.save_template(template)

    reloaded = WireRecipeTemplateStore(store_path)
    templates = reloaded.list_templates()

    assert len(templates) == 1
    loaded = templates[0]
    assert loaded.template_id == "rx2000-default"
    assert loaded.wb1_template_path == "C:/fixtures/sample.WB1"
    assert loaded.ordering.primary_axis == "y"
    assert loaded.ordering.group_no == 3
    assert loaded.wb1_field_map["bond_x"] == 2
    assert loaded.wb1_record_defaults[5] == 100
    assert loaded.wb1_record_defaults[6] == "00F0"


def test_wire_recipe_template_store_deletes_templates(tmp_path):
    store_path = tmp_path / "wire_templates.json"
    store = WireRecipeTemplateStore(store_path)
    template = WireRecipeTemplate(template_id="demo", name="Demo")
    store.save_template(template)

    store.delete_template("demo")

    assert store.get_template("demo") is None
    assert any(item.template_id == "rx2000-default" for item in store.list_templates())


def test_wire_recipe_template_store_includes_builtin_rx2000_default(tmp_path):
    store_path = tmp_path / "wire_templates.json"
    store = WireRecipeTemplateStore(store_path)

    templates = store.list_templates()

    assert any(template.template_id == "rx2000-default" for template in templates)
    builtin = store.get_template("rx2000-default")
    expected = build_rx2000_default_template()
    assert builtin is not None
    assert builtin.name == expected.name
    assert builtin.wb1_field_map == expected.wb1_field_map
