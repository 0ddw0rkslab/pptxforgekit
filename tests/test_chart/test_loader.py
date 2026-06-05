from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pptxforgekit.chart.loader import ChartDataLoader
from pptxforgekit.exceptions import ChartBuildError
from pptxforgekit.models.schema import ChartElement, Position

FIXTURES = Path(__file__).parents[1] / "fixtures" / "data"


def _make_element(
    data_source: str = "",
    data_inline: list | None = None,
    x_column: str | None = None,
) -> ChartElement:
    return ChartElement(
        element_id="test",
        chart_type="bar",
        data_source=data_source,
        data_inline=data_inline or ([{"x": "A", "y": 1}] if not data_source else None),
        x_column=x_column,
        position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
    )


class TestChartDataLoaderFile:
    def test_load_csv(self) -> None:
        loader = ChartDataLoader()
        df = loader.load_from_file(FIXTURES / "comparison.csv")
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["method", "accuracy_pct", "f1_score_pct", "inference_ms"]
        assert len(df) == 5

    def test_load_timeseries_csv(self) -> None:
        loader = ChartDataLoader()
        df = loader.load_from_file(FIXTURES / "timeseries.csv")
        assert "epoch" in df.columns
        assert "train_loss" in df.columns
        assert len(df) == 7

    def test_load_json_records(self, tmp_path: Path) -> None:
        records = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps(records), encoding="utf-8")
        loader = ChartDataLoader()
        df = loader.load_from_file(json_file)
        assert list(df.columns) == ["a", "b"]
        assert len(df) == 2

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        loader = ChartDataLoader()
        with pytest.raises(ChartBuildError, match="not found"):
            loader.load_from_file(tmp_path / "nonexistent.csv")

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "data.parquet"
        f.write_bytes(b"dummy")
        loader = ChartDataLoader()
        with pytest.raises(ChartBuildError, match="Unsupported"):
            loader.load_from_file(f)


class TestChartDataLoaderInline:
    def test_load_inline(self) -> None:
        records = [{"cat": "A", "val": 1.0}, {"cat": "B", "val": 2.0}]
        loader = ChartDataLoader()
        df = loader.load_from_inline(records)
        assert list(df.columns) == ["cat", "val"]
        assert len(df) == 2

    def test_empty_inline_raises(self) -> None:
        loader = ChartDataLoader()
        with pytest.raises(ChartBuildError, match="empty"):
            loader.load_from_inline([])


class TestChartDataLoaderDispatch:
    def test_inline_takes_precedence_over_file(self, tmp_path: Path) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("x,y\nA,1\nB,2\n", encoding="utf-8")
        # Both data_source and data_inline present → inline wins
        element = ChartElement(
            element_id="e",
            chart_type="bar",
            data_source=str(csv),
            data_inline=[{"x": "INLINE", "y": 99}],
            position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
        )
        loader = ChartDataLoader()
        df = loader.load(element)
        assert df.iloc[0]["x"] == "INLINE"

    def test_resolves_relative_path_from_base(self) -> None:
        fixtures = FIXTURES
        element = _make_element(
            data_source="comparison.csv",
            data_inline=None,
        )
        loader = ChartDataLoader()
        df = loader.load(element, base_path=fixtures)
        assert len(df) == 5

    def test_no_data_raises(self) -> None:
        # Can't create a ChartElement without any data — validator catches it
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="data_source.*data_inline"):
            ChartElement(
                element_id="e",
                chart_type="bar",
                data_source="",
                data_inline=None,
                position=Position(x=2.0, y=3.0, w=20.0, h=12.0),
            )
