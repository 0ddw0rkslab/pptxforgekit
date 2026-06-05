from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

_MAX_PIE_SLICES = 7
_MAX_CATEGORY_LABEL_LEN = 12   # chars; longer labels suit horizontal bar better
_MANY_CATEGORIES = 9


@dataclass
class ChartRecommendation:
    """Result of automatic chart type inference."""

    chart_type: str                   # "bar" | "line" | "scatter" | "pie"
    bar_direction: str                # "vertical" | "horizontal"
    stacked: bool
    confidence: float                 # 0.0 – 1.0
    reason: str


class ChartTypeRecommender:
    """Rule-based chart type recommender.

    Decides the most appropriate chart type by inspecting the
    DataFrame columns rather than requiring the user to specify it.
    """

    def recommend(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_cols: list[str],
    ) -> ChartRecommendation:
        if x_col not in df.columns:
            return ChartRecommendation(
                chart_type="bar",
                bar_direction="vertical",
                stacked=False,
                confidence=0.3,
                reason=f"Column '{x_col}' not found; defaulting to bar chart.",
            )

        x_series = df[x_col]
        n_categories = x_series.nunique()
        x_dtype = x_series.dtype

        # ── datetime / time-series ────────────────────────────────────────────
        if pd.api.types.is_datetime64_any_dtype(x_series) or self._looks_like_epoch(x_series):
            return ChartRecommendation(
                chart_type="line",
                bar_direction="vertical",
                stacked=False,
                confidence=0.95,
                reason="X-axis is datetime; line chart shows trends over time.",
            )

        # ── numeric X + numeric Y → scatter ──────────────────────────────────
        if pd.api.types.is_numeric_dtype(x_series) and y_cols:
            y_numeric = all(
                pd.api.types.is_numeric_dtype(df[c]) for c in y_cols if c in df.columns
            )
            if y_numeric and n_categories > 5:
                return ChartRecommendation(
                    chart_type="scatter",
                    bar_direction="vertical",
                    stacked=False,
                    confidence=0.85,
                    reason=(
                        "Both axes are numeric with many distinct values; "
                        "scatter chart shows the relationship."
                    ),
                )

        # ── categorical X ─────────────────────────────────────────────────────
        if pd.api.types.is_object_dtype(x_series) or pd.api.types.is_categorical_dtype(x_series):
            # Pie: 1 y column, few slices, non-negative, looks like proportions
            if len(y_cols) == 1 and y_cols[0] in df.columns:
                y_series = df[y_cols[0]]
                if (
                    n_categories <= _MAX_PIE_SLICES
                    and pd.api.types.is_numeric_dtype(y_series)
                    and (y_series >= 0).all()
                    and self._looks_like_proportions(y_series)
                ):
                    return ChartRecommendation(
                        chart_type="pie",
                        bar_direction="vertical",
                        stacked=False,
                        confidence=0.75,
                        reason=(
                            f"1 numeric series with {n_categories} categories "
                            "that sum close to 100; pie chart shows part-to-whole."
                        ),
                    )

            # Horizontal bar: many categories or long labels
            max_label_len = x_series.astype(str).str.len().max()
            if n_categories >= _MANY_CATEGORIES or max_label_len > _MAX_CATEGORY_LABEL_LEN:
                return ChartRecommendation(
                    chart_type="bar",
                    bar_direction="horizontal",
                    stacked=False,
                    confidence=0.80,
                    reason=(
                        f"{n_categories} categories (or label length {max_label_len} chars); "
                        "horizontal bar gives more label space."
                    ),
                )

            # Multiple series → grouped column
            stacked = len(y_cols) > 3
            return ChartRecommendation(
                chart_type="bar",
                bar_direction="vertical",
                stacked=stacked,
                confidence=0.85,
                reason=(
                    f"Categorical X with {n_categories} categories; "
                    f"{'stacked ' if stacked else ''}column chart compares values."
                ),
            )

        # ── fallback: sequential numeric X, few points → line ────────────────
        return ChartRecommendation(
            chart_type="line",
            bar_direction="vertical",
            stacked=False,
            confidence=0.55,
            reason="Could not determine best type; defaulting to line chart.",
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _looks_like_epoch(self, series: pd.Series) -> bool:
        """True if the series is a sequential integer that looks like training epochs."""
        if not pd.api.types.is_integer_dtype(series):
            return False
        if series.is_monotonic_increasing and series.nunique() > 3:
            col_lower = str(series.name).lower()
            return any(kw in col_lower for kw in ("epoch", "step", "iter", "round"))
        return False

    def _looks_like_proportions(self, series: pd.Series) -> bool:
        """True if the numeric series looks like percentages summing ~100."""
        total = series.sum()
        return 90.0 <= total <= 110.0
