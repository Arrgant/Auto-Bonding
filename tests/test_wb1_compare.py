from __future__ import annotations

from core.export.wb1_compare import WB1Comparer
from core.export.wire_recipe_models import WireRecipeTemplate


def test_wb1_comparer_reports_header_and_named_j_field_differences():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={
            "role_code": 0,
            "wire_seq": 1,
            "group_no": 2,
            "bond_x": 3,
            "bond_y": 4,
        },
        wb1_role_codes={"first": 0, "second": 2},
    )
    expected_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "0004,0001,002D,0016,",
            "G,",
            "0002,0032,",
            "J,",
            "0000,0001,0002,000A,000F,",
            "Q",
        ]
    )
    actual_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "0004,0001,002E,0016,",
            "G,",
            "0002,0032,",
            "J,",
            "0000,0001,0003,000C,000F,",
            "Q",
        ]
    )

    result = WB1Comparer().compare_texts(expected_wb1, actual_wb1, template)

    assert result.has_differences is True
    assert result.expected_source == "wb1"
    assert result.actual_source == "wb1"
    assert _difference_signature(result.differences) == {
        ("header", "PRE:1:2", "word_2", "002D", "002E"),
        ("j_record", "J:1:2", "group_no", "0002", "0003"),
        ("j_record", "J:1:3", "bond_x", "000A", "000C"),
    }


def test_wb1_comparer_reports_missing_or_extra_j_records():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={"role_code": 0, "wire_seq": 1},
        wb1_role_codes={"first": 0, "second": 2},
    )
    expected_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "J,",
            "0000,0001,",
            "0002,0001,",
            "Q",
        ]
    )
    actual_wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "J,",
            "0000,0001,",
            "Q",
        ]
    )

    result = WB1Comparer().compare_texts(expected_wb1, actual_wb1, template)

    assert result.has_differences is True
    assert _difference_signature(result.differences) == {
        ("j_record", "J:2", "record_presence", "present", ""),
    }


def test_wb1_comparer_returns_clean_result_for_identical_documents():
    template = WireRecipeTemplate(
        template_id="demo",
        name="Demo",
        wb1_field_map={"role_code": 0, "wire_seq": 1, "bond_x": 2},
        wb1_role_codes={"first": 0, "second": 2},
    )
    wb1 = "\n".join(
        [
            "0000,44454D4F2E5742310000,",
            "J,",
            "0000,0001,000A,",
            "Q",
        ]
    )

    result = WB1Comparer().compare_texts(wb1, wb1, template)

    assert result.has_differences is False
    assert result.difference_count == 0
    assert result.differences == ()


def _difference_signature(differences):
    return {
        (difference.scope, difference.location, difference.field_name, difference.expected, difference.actual)
        for difference in differences
    }
