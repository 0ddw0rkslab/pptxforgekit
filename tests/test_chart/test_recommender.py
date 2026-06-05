from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from presentation_tool.chart.recommender import ChartTypeRecommender

FIXTURES = Path(__file__).parents[1] / "fixtures" / "data"


@pytest.fixture
def recommender() -> ChartTypeRecommender:
    return ChartTypeRecommender()


class TestRecommendBar:
    def test_categorical_x_few_categories(self, recommender: ChartTypeRecommender) -> None:
        df = pd.DataFrame({
            "method": ["A", "B", "C", "D"],
            "accuracy": [0.8, 0.85, 0.9, 0.75],
        })
        rec = recommender.recommend(df, "method", ["accuracy"])
        assert rec.chart_type == "bar"
        assert rec.bar_direction == "vertical"
        assert rec.confidence > 0.7

    def test_many_categories_prefers_horizontal(self, recommender: ChartTypeRecommender) -> None:
        methods = [f"Method_{i}" for i in range(12)]
        df = pd.DataFrame({
            "method": methods,
            "accuracy": [0.8 + i * 0.01 for i in range(12)],
        })
        rec = recommender.recommend(df, "method", ["accuracy"])
        assert rec.chart_type == "bar"
        assert rec.bar_direction == "horizontal"

    def test_long_labels_prefers_horizontal(self, recommender: ChartTypeRecommender) -> None:
        df = pd.DataFrame({
            "method": ["Very Long Method Name A", "Very Long Method Name B"],
            "acc": [0.8, 0.9],
        })
        rec = recommender.recommend(df, "method", ["acc"])
        assert rec.bar_direction == "horizontal"

    def test_multiple_series_suggests_stacked(self, recommender: ChartTypeRecommender) -> None:
        df = pd.DataFrame({
            "cat": ["A", "B"],
            "s1": [1, 2], "s2": [3, 4], "s3": [5, 6], "s4": [7, 8],
        })
        rec = recommender.recommend(df, "cat", ["s1", "s2", "s3", "s4"])
        assert rec.chart_type == "bar"
        assert rec.stacked is True


class TestRecommendLine:
    def test_epoch_column_recommends_line(self, recommender: ChartTypeRecommender) -> None:
        df = pd.read_csv(FIXTURES / "timeseries.csv")
        rec = recommender.recommend(df, "epoch", ["train_loss", "val_loss"])
        assert rec.chart_type == "line"
        assert rec.confidence >= 0.9

    def test_datetime_column_recommends_line(self, recommender: ChartTypeRecommender) -> None:
        df = pd.DataFrame({
            "date": pd.date_range("2024-01", periods=5, freq="ME"),
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        rec = recommender.recommend(df, "date", ["value"])
        assert rec.chart_type == "line"


class TestRecommendScatter:
    def test_numeric_xy_recommends_scatter(self, recommender: ChartTypeRecommender) -> None:
        df = pd.read_csv(FIXTURES / "scatter.csv")
        rec = recommender.recommend(df, "model_params_M", ["accuracy_pct"])
        assert rec.chart_type == "scatter"
        assert rec.confidence > 0.7


class TestRecommendPie:
    def test_proportional_data_recommends_pie(self, recommender: ChartTypeRecommender) -> None:
        df = pd.read_csv(FIXTURES / "market_share.csv")
        rec = recommender.recommend(df, "framework", ["market_share_pct"])
        assert rec.chart_type == "pie"

    def test_non_proportional_data_not_pie(self, recommender: ChartTypeRecommender) -> None:
        df = pd.DataFrame({
            "method": ["A", "B", "C"],
            "accuracy": [82.0, 91.0, 93.0],   # sums to 266, not ~100
        })
        rec = recommender.recommend(df, "method", ["accuracy"])
        assert rec.chart_type != "pie"


class TestRecommendFallback:
    def test_missing_x_column_returns_default(self, recommender: ChartTypeRecommender) -> None:
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        rec = recommender.recommend(df, "nonexistent", ["b"])
        assert rec.chart_type == "bar"
        assert rec.confidence < 0.5
