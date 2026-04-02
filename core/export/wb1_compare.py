"""Structured comparison helpers for WB1 documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .wb1_parser import ParsedWB1Document, ParsedWB1Record, WB1Parser
from .wire_recipe_models import WireRecipeTemplate


@dataclass(frozen=True)
class WB1Difference:
    """One specific mismatch between two parsed WB1 documents."""

    scope: str
    location: str
    field_name: str
    expected: str
    actual: str


@dataclass(frozen=True)
class WB1CompareResult:
    """Structured summary for one WB1 comparison run."""

    expected_source: str
    actual_source: str
    differences: tuple[WB1Difference, ...]

    @property
    def has_differences(self) -> bool:
        return bool(self.differences)

    @property
    def difference_count(self) -> int:
        return len(self.differences)


class WB1Comparer:
    """Compare raw WB1 files or parsed workbook inputs field by field."""

    def __init__(self):
        self._parser = WB1Parser()

    def compare_files(
        self,
        expected_path: str | Path,
        actual_path: str | Path,
        template: WireRecipeTemplate,
    ) -> WB1CompareResult:
        """Parse and compare two raw WB1 files."""

        expected = self._parser.parse_file(expected_path, template)
        actual = self._parser.parse_file(actual_path, template)
        return self.compare_documents(expected, actual, template)

    def compare_texts(
        self,
        expected_wb1: str,
        actual_wb1: str,
        template: WireRecipeTemplate,
    ) -> WB1CompareResult:
        """Parse and compare two WB1 strings."""

        expected = self._parser.parse_text(expected_wb1, template)
        actual = self._parser.parse_text(actual_wb1, template)
        return self.compare_documents(expected, actual, template)

    def compare_documents(
        self,
        expected: ParsedWB1Document,
        actual: ParsedWB1Document,
        template: WireRecipeTemplate,
    ) -> WB1CompareResult:
        """Compare two already-parsed WB1 documents."""

        differences: list[WB1Difference] = []
        differences.extend(_compare_header_rows("PRE", expected.preamble_rows, actual.preamble_rows))
        for section_name in ("G", "H", "I", "Q"):
            differences.extend(
                _compare_header_rows(
                    section_name,
                    expected.sections.get(section_name, ()),
                    actual.sections.get(section_name, ()),
                )
            )
        differences.extend(_compare_j_records(expected.j_records, actual.j_records, template))
        return WB1CompareResult(
            expected_source=expected.source,
            actual_source=actual.source,
            differences=tuple(differences),
        )


def _compare_header_rows(
    section_name: str,
    expected_rows: tuple[tuple[str, ...], ...],
    actual_rows: tuple[tuple[str, ...], ...],
) -> list[WB1Difference]:
    differences: list[WB1Difference] = []
    max_rows = max(len(expected_rows), len(actual_rows))
    for row_index in range(max_rows):
        expected_tokens = expected_rows[row_index] if row_index < len(expected_rows) else ()
        actual_tokens = actual_rows[row_index] if row_index < len(actual_rows) else ()
        max_tokens = max(len(expected_tokens), len(actual_tokens))
        for token_index in range(max_tokens):
            expected_token = expected_tokens[token_index] if token_index < len(expected_tokens) else ""
            actual_token = actual_tokens[token_index] if token_index < len(actual_tokens) else ""
            if expected_token == actual_token:
                continue
            differences.append(
                WB1Difference(
                    scope="header",
                    location=f"{section_name}:{row_index}:{token_index}",
                    field_name=f"word_{token_index}",
                    expected=expected_token,
                    actual=actual_token,
                )
            )
    return differences


def _compare_j_records(
    expected_records: tuple[ParsedWB1Record, ...],
    actual_records: tuple[ParsedWB1Record, ...],
    template: WireRecipeTemplate,
) -> list[WB1Difference]:
    differences: list[WB1Difference] = []
    reverse_field_map = {index: field_name for field_name, index in template.wb1_field_map.items()}
    max_records = max(len(expected_records), len(actual_records))

    for record_index in range(max_records):
        expected_record = expected_records[record_index] if record_index < len(expected_records) else None
        actual_record = actual_records[record_index] if record_index < len(actual_records) else None
        location = f"J:{record_index + 1}"

        if expected_record is None:
            differences.append(
                WB1Difference(
                    scope="j_record",
                    location=location,
                    field_name="record_presence",
                    expected="",
                    actual="present",
                )
            )
            continue
        if actual_record is None:
            differences.append(
                WB1Difference(
                    scope="j_record",
                    location=location,
                    field_name="record_presence",
                    expected="present",
                    actual="",
                )
            )
            continue

        if expected_record.role != actual_record.role:
            differences.append(
                WB1Difference(
                    scope="j_record",
                    location=location,
                    field_name="role",
                    expected=expected_record.role or "",
                    actual=actual_record.role or "",
                )
            )

        max_tokens = max(len(expected_record.tokens), len(actual_record.tokens))
        for token_index in range(max_tokens):
            expected_token = expected_record.tokens[token_index] if token_index < len(expected_record.tokens) else ""
            actual_token = actual_record.tokens[token_index] if token_index < len(actual_record.tokens) else ""
            if expected_token == actual_token:
                continue
            field_name = reverse_field_map.get(token_index, f"word_{token_index}")
            differences.append(
                WB1Difference(
                    scope="j_record",
                    location=f"{location}:{token_index}",
                    field_name=field_name,
                    expected=expected_token,
                    actual=actual_token,
                )
            )
    return differences


__all__ = ["WB1Comparer", "WB1CompareResult", "WB1Difference"]
