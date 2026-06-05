from __future__ import annotations

import pytest

from presentation_tool.models.schema import ChartElement, Position
from presentation_tool.reviewer.checks.chart_check import check_chart_labels
from .conftest import _chart, _pos, _slide


class TestMissingTitle:
    def test_no_title_low_severity(self) -> None:
        slide = _slide(chart_elements=[_chart("c1", title="")])
        issues = check_chart_labels(slide)
        title_issues = [i for i in issues if "no title" in i.message.lower()]
        assert title_issues
        assert title_issues[0].severity == "low"

    def test_with_title_no_title_issue(self) -> None:
        slide = _slide(chart_elements=[_chart("c1", title="Accuracy Results")])
        issues = check_chart_labels(slide)
        assert not any("no title" in i.message.lower() for i in issues)


class TestTooManySeries:
    def test_within_limit_no_issue(self) -> None:
        slide = _slide(chart_elements=[_chart("c1", y_columns=["a", "b", "c"])])
        issues = check_chart_labels(slide)
        series_issues = [i for i in issues if "series" in i.message.lower()]
        assert not any("5" in i.message or "limit" in i.message.lower() for i in series_issues)

    def test_too_many_bar_series(self) -> None:
        cols = [f"s{i}" for i in range(7)]
        inline = [{"cat": "A", **{c: float(i) for i, c in enumerate(cols)}}]
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=inline,
            x_column="cat",
            y_columns=cols,
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        series_issues = [i for i in issues if "series" in i.message.lower()]
        assert series_issues
        assert series_issues[0].severity in ("medium", "high")

    def test_too_many_line_series(self) -> None:
        cols = [f"s{i}" for i in range(6)]
        inline = [{"x": 1.0, **{c: float(i) for i, c in enumerate(cols)}}]
        elem = ChartElement(
            element_id="c1",
            chart_type="line",
            data_inline=inline,
            x_column="x",
            y_columns=cols,
            title="T",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        assert any("series" in i.message.lower() for i in issues)


class TestPieSlices:
    def test_too_many_pie_slices(self) -> None:
        inline = [{"cat": f"C{i}", "val": 10.0} for i in range(10)]
        elem = ChartElement(
            element_id="pie1",
            chart_type="pie",
            data_inline=inline,
            x_column="cat",
            y_columns=["val"],
            title="Market Share",
            position=_pos(w=15.0, h=12.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        pie_issues = [i for i in issues if "slice" in i.message.lower()]
        assert pie_issues
        assert pie_issues[0].severity == "medium"


class TestMissingAxisLabel:
    def test_missing_y_label_bar(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"cat": "A", "val": 1.0}],
            x_column="cat",
            y_columns=["val"],
            title="T",
            y_label="",
            y_unit="",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        assert any("y-axis" in i.message.lower() for i in issues)

    def test_with_y_unit_no_axis_issue(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"cat": "A", "val": 1.0}],
            x_column="cat",
            y_columns=["val"],
            title="T",
            y_label="",
            y_unit="(%)",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        axis_issues = [i for i in issues if "y-axis" in i.message.lower()]
        assert not axis_issues


class TestLegendHidden:
    def test_hidden_legend_with_multiple_series(self) -> None:
        elem = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_inline=[{"cat": "A", "v1": 1.0, "v2": 2.0}],
            x_column="cat",
            y_columns=["v1", "v2"],
            title="T",
            legend_position="none",
            position=_pos(w=20.0, h=10.0),
        )
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        assert any("legend" in i.message.lower() for i in issues)


class TestSmallChartArea:
    def test_tiny_chart_is_medium(self) -> None:
        elem = _chart("c1", pos=Position(x=2.0, y=0.5, w=3.0, h=2.0))
        slide = _slide(chart_elements=[elem])
        issues = check_chart_labels(slide)
        size_issues = [i for i in issues if "small" in i.message.lower()]
        assert size_issues
        assert size_issues[0].severity == "medium"

    def test_all_issues_have_correct_type(self) -> None:
        slide = _slide(chart_elements=[_chart("c1", title="")])
        issues = check_chart_labels(slide)
        assert all(i.issue_type == "chart_label_readability" for i in issues)
        assert all(i.check_category == "chart" for i in issues)
