from __future__ import annotations

from pathlib import Path

import pandas as pd

from pptxforgekit.chart.validator import ChartDataValidator
from pptxforgekit.models.schema import ChartElement, Position

FIXTURES = Path(__file__).parents[1] / "fixtures" / "data"


def _elem(chart_type: str = "bar", y_columns: list | None = None, **kw) -> ChartElement:
    inline = [{"cat": "A", "val": 1.0}, {"cat": "B", "val": 2.0}]
    return ChartElement(
        element_id="test",
        chart_type=chart_type,
        data_inline=inline,
        x_column=kw.pop("x_column", "cat"),
        y_columns=y_columns or ["val"],
        position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
        **kw,
    )


class TestColumnExistence:
    def test_valid_columns_no_errors(self) -> None:
        df = pd.DataFrame({"method": ["A", "B"], "acc": [0.8, 0.9]})
        result = ChartDataValidator().validate(_elem(x_column="method", y_columns=["acc"]), df)
        assert result.is_valid
        assert not result.errors()

    def test_missing_x_column_is_error(self) -> None:
        df = pd.DataFrame({"method": ["A"], "acc": [0.8]})
        result = ChartDataValidator().validate(_elem(x_column="MISSING", y_columns=["acc"]), df)
        errors = result.errors()
        assert any("x_column" in e.field for e in errors)

    def test_missing_y_column_is_error(self) -> None:
        df = pd.DataFrame({"method": ["A"], "acc": [0.8]})
        result = ChartDataValidator().validate(_elem(x_column="method", y_columns=["MISSING"]), df)
        errors = result.errors()
        assert any("y_columns" in e.field for e in errors)


class TestNumericCheck:
    def test_non_numeric_y_is_error(self) -> None:
        df = pd.DataFrame({"cat": ["A", "B"], "label": ["good", "bad"]})
        result = ChartDataValidator().validate(_elem(x_column="cat", y_columns=["label"]), df)
        assert not result.is_valid
        assert any("not numeric" in e.message for e in result.errors())

    def test_numeric_y_passes(self) -> None:
        df = pd.DataFrame({"cat": ["A", "B"], "val": [1.0, 2.0]})
        result = ChartDataValidator().validate(_elem(x_column="cat", y_columns=["val"]), df)
        assert result.is_valid


class TestNullCheck:
    def test_null_values_warning(self) -> None:
        import numpy as np
        df = pd.DataFrame({"cat": ["A", "B"], "val": [1.0, np.nan]})
        result = ChartDataValidator().validate(_elem(x_column="cat", y_columns=["val"]), df)
        assert result.is_valid   # nulls are warnings, not errors
        assert any("null" in e.message.lower() for e in result.warnings())
        assert result.null_counts.get("val", 0) == 1

    def test_no_nulls_no_warning(self) -> None:
        df = pd.DataFrame({"cat": ["A", "B"], "val": [1.0, 2.0]})
        result = ChartDataValidator().validate(_elem(x_column="cat", y_columns=["val"]), df)
        null_warns = [e for e in result.warnings() if "null" in e.message.lower()]
        assert len(null_warns) == 0


class TestPieSpecific:
    def test_too_many_slices_warns(self) -> None:
        df = pd.DataFrame({
            "cat": [f"C{i}" for i in range(10)],
            "val": [10.0] * 10,
        })
        result = ChartDataValidator().validate(
            _elem(chart_type="pie", x_column="cat", y_columns=["val"]), df
        )
        assert any("slices" in e.message.lower() or "pie" in e.message.lower() for e in result.warnings())

    def test_negative_pie_values_error(self) -> None:
        df = pd.DataFrame({"cat": ["A", "B"], "val": [10.0, -5.0]})
        result = ChartDataValidator().validate(
            _elem(chart_type="pie", x_column="cat", y_columns=["val"]), df
        )
        assert not result.is_valid
        assert any("negative" in e.message.lower() for e in result.errors())

    def test_multiple_y_cols_for_pie_warns(self) -> None:
        df = pd.DataFrame({"cat": ["A"], "v1": [1.0], "v2": [2.0]})
        result = ChartDataValidator().validate(
            _elem(chart_type="pie", x_column="cat", y_columns=["v1", "v2"]), df
        )
        assert any("first" in e.message.lower() for e in result.warnings())


class TestScatterSpecific:
    def test_non_numeric_x_for_scatter_is_error(self) -> None:
        df = pd.DataFrame({"cat": ["A", "B", "C"], "val": [1.0, 2.0, 3.0]})
        result = ChartDataValidator().validate(
            _elem(chart_type="scatter", x_column="cat", y_columns=["val"]), df
        )
        assert not result.is_valid

    def test_few_points_warns(self) -> None:
        df = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
        result = ChartDataValidator().validate(
            _elem(chart_type="scatter", x_column="x", y_columns=["y"]), df
        )
        assert any("point" in e.message.lower() for e in result.warnings())


class TestDataConsistency:
    def test_only_inline_skips_check(self) -> None:
        element = ChartElement(
            element_id="e",
            chart_type="bar",
            data_inline=[{"x": "A", "y": 1}],
            position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
        )
        result = ChartDataValidator().validate_data_consistency(element)
        assert result.is_valid
        assert any("skipped" in i.message.lower() for i in result.issues)

    def test_file_and_inline_match(self, tmp_path: Path) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("x,y\nA,1.0\nB,2.0\n", encoding="utf-8")
        element = ChartElement(
            element_id="e",
            chart_type="bar",
            data_source=str(csv),
            data_inline=[{"x": "A", "y": 1.0}, {"x": "B", "y": 2.0}],
            position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
        )
        result = ChartDataValidator().validate_data_consistency(element)
        assert result.is_valid
        # No mismatch warnings
        mismatch = [i for i in result.issues if "differ" in i.message]
        assert not mismatch

    def test_file_and_inline_mismatch_warns(self, tmp_path: Path) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("x,y\nA,1.0\nB,2.0\n", encoding="utf-8")
        element = ChartElement(
            element_id="e",
            chart_type="bar",
            data_source=str(csv),
            data_inline=[{"x": "A", "y": 99.0}, {"x": "B", "y": 99.0}],  # stale
            position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
        )
        result = ChartDataValidator().validate_data_consistency(element)
        assert any("differ" in i.message.lower() or "stale" in i.message.lower() for i in result.issues)
