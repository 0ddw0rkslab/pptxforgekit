from __future__ import annotations

from pathlib import Path

import pytest

from pptxforgekit.models.schema import ChartElement, Position
from pptxforgekit.reviewer.checks.data_check import check_data_consistency
from .conftest import _chart, _pos, _slide


class TestInlineColumnValidation:
    def test_valid_inline_no_issues(self) -> None:
        slide = _slide(chart_elements=[
            _chart("c1", y_columns=["val"])
        ])
        assert check_data_consistency(slide) == []

    def test_missing_y_column_in_inline(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"cat": "A", "val": 1.0}],
            x_column="cat",
            y_columns=["val", "MISSING_COL"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_data_consistency(slide)
        assert any(i.severity == "high" for i in issues)
        assert any("y_columns" in i.message.lower() or "missing" in i.message.lower() for i in issues)

    def test_missing_x_column_in_inline(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"wrong_col": "A", "val": 1.0}],
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_data_consistency(slide)
        assert any("x_column" in i.message.lower() for i in issues)

    def test_valid_columns_no_issue(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"cat": "A", "val": 1.0}],
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        col_issues = [
            i for i in check_data_consistency(slide)
            if "column" in i.message.lower()
        ]
        assert not col_issues


class TestFileExistence:
    def test_missing_file_is_high(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_source="/nonexistent/path/data.csv",
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_data_consistency(slide)
        assert any(i.severity == "high" for i in issues)
        assert any("not found" in i.message.lower() for i in issues)

    def test_existing_file_no_issue(self, tmp_path: Path) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("cat,val\nA,1\nB,2\n", encoding="utf-8")
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_source=str(csv),
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        file_issues = [
            i for i in check_data_consistency(slide)
            if "not found" in i.message.lower()
        ]
        assert not file_issues


class TestFlatData:
    def test_all_same_value_warns(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[
                {"cat": "A", "val": 5.0},
                {"cat": "B", "val": 5.0},
                {"cat": "C", "val": 5.0},
            ],
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_data_consistency(slide)
        flat_issues = [i for i in issues if "distinct value" in i.message.lower()]
        assert flat_issues
        assert flat_issues[0].severity == "low"

    def test_varying_values_no_flat_warning(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[
                {"cat": "A", "val": 1.0},
                {"cat": "B", "val": 3.0},
                {"cat": "C", "val": 5.0},
            ],
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        flat_issues = [i for i in check_data_consistency(slide) if "distinct value" in i.message.lower()]
        assert not flat_issues


class TestCrossConsistency:
    def test_matching_data_no_issues(self, tmp_path: Path) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("cat,val\nA,1.0\nB,2.0\n", encoding="utf-8")
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_source=str(csv),
            data_inline=[{"cat": "A", "val": 1.0}, {"cat": "B", "val": 2.0}],
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        stale_issues = [
            i for i in check_data_consistency(slide)
            if "stale" in i.message.lower() or "differ" in i.message.lower()
        ]
        assert not stale_issues

    def test_all_issues_have_correct_type(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"cat": "A", "WRONG": 1.0}],
            x_column="cat",
            y_columns=["val"],
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_data_consistency(slide)
        assert all(i.issue_type == "data_consistency" for i in issues)
        assert all(i.check_category == "data" for i in issues)
