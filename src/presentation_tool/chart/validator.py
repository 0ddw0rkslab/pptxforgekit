from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd

from presentation_tool.models.schema import ChartElement

logger = logging.getLogger(__name__)

Severity = Literal["info", "warning", "error"]


@dataclass
class ChartIssue:
    severity: Severity
    field: str       # which column or attribute the issue concerns
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


@dataclass
class ChartValidationResult:
    """Summary of validation issues found in a chart element + its data."""

    element_id: str
    is_valid: bool           # False when any "error"-severity issues exist
    issues: list[ChartIssue] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)

    def errors(self) -> list[ChartIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[ChartIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def log_summary(self) -> None:
        for issue in self.issues:
            lvl = logging.ERROR if issue.severity == "error" else logging.WARNING
            logger.log(lvl, "Chart '%s' — %s", self.element_id, issue)


class ChartDataValidator:
    """Validates a ChartElement and its resolved DataFrame for common issues."""

    def validate(
        self,
        element: ChartElement,
        df: pd.DataFrame,
    ) -> ChartValidationResult:
        issues: list[ChartIssue] = []
        null_counts: dict[str, int] = {}

        all_cols = list(df.columns)
        x_col = element.x_column or (all_cols[0] if all_cols else "")
        y_cols = element.y_columns or [
            c for c in all_cols if c != x_col and pd.api.types.is_numeric_dtype(df[c])
        ]

        # ── Column existence ─────────────────────────────────────────────────
        if x_col and x_col not in df.columns:
            issues.append(ChartIssue(
                severity="error",
                field="x_column",
                message=(
                    f"Column '{x_col}' not found in data. "
                    f"Available columns: {all_cols}"
                ),
            ))

        for col in y_cols:
            if col not in df.columns:
                issues.append(ChartIssue(
                    severity="error",
                    field="y_columns",
                    message=(
                        f"Y column '{col}' not found in data. "
                        f"Available columns: {all_cols}"
                    ),
                ))

        # ── Numeric Y check ──────────────────────────────────────────────────
        for col in y_cols:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(ChartIssue(
                    severity="error",
                    field=col,
                    message=(
                        f"Column '{col}' has dtype '{df[col].dtype}' which is not numeric. "
                        f"Y columns must be numeric for chart rendering."
                    ),
                ))

        # ── Null / NaN counts ────────────────────────────────────────────────
        for col in y_cols:
            if col in df.columns:
                n_null = int(df[col].isna().sum())
                null_counts[col] = n_null
                if n_null > 0:
                    issues.append(ChartIssue(
                        severity="warning",
                        field=col,
                        message=(
                            f"Column '{col}' has {n_null} null/NaN value(s). "
                            f"These will be rendered as gaps in the chart."
                        ),
                    ))

        # ── Minimum data points ──────────────────────────────────────────────
        if len(df) < 2:
            issues.append(ChartIssue(
                severity="warning" if len(df) == 1 else "error",
                field="data",
                message=(
                    f"Only {len(df)} row(s) found. "
                    f"Charts are most meaningful with at least 2 data points."
                ),
            ))

        # ── Chart-type-specific checks ───────────────────────────────────────
        if element.chart_type == "pie":
            self._check_pie(df, y_cols, issues)

        if element.chart_type == "scatter":
            self._check_scatter(df, x_col, issues)
            # Scatter requires numeric x
            if x_col in df.columns and not pd.api.types.is_numeric_dtype(df[x_col]):
                issues.append(ChartIssue(
                    severity="error",
                    field="x_column",
                    message=(
                        f"Scatter chart requires a numeric X column, "
                        f"but '{x_col}' has dtype '{df[x_col].dtype}'."
                    ),
                ))

        # ── Duplicate X values ───────────────────────────────────────────────
        if x_col in df.columns:
            n_dupes = int(df[x_col].duplicated().sum())
            if n_dupes > 0 and element.chart_type in ("scatter", "line"):
                issues.append(ChartIssue(
                    severity="warning",
                    field="x_column",
                    message=(
                        f"X column '{x_col}' has {n_dupes} duplicate value(s). "
                        f"This may cause unexpected chart appearance."
                    ),
                ))

        # ── Flat data (all Y values identical) ───────────────────────────────
        for col in y_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                if df[col].dropna().nunique() == 1:
                    issues.append(ChartIssue(
                        severity="info",
                        field=col,
                        message=(
                            f"Column '{col}' has only one distinct value "
                            f"({df[col].dropna().iloc[0]}). "
                            f"The chart will show a flat line/equal bars."
                        ),
                    ))

        # ── series_names length ──────────────────────────────────────────────
        if element.series_names and len(element.series_names) != len(y_cols):
            issues.append(ChartIssue(
                severity="warning",
                field="series_names",
                message=(
                    f"series_names has {len(element.series_names)} entries "
                    f"but {len(y_cols)} Y column(s) were resolved. "
                    f"Extra names will be ignored; missing names use column names."
                ),
            ))

        is_valid = not any(i.severity == "error" for i in issues)
        return ChartValidationResult(
            element_id=element.element_id,
            is_valid=is_valid,
            issues=issues,
            row_count=len(df),
            column_count=len(df.columns),
            null_counts=null_counts,
        )

    def validate_data_consistency(
        self,
        element: ChartElement,
        base_path: Path | None = None,
    ) -> ChartValidationResult:
        """Check that data_inline and the data_source file contain matching data.

        This is only meaningful when both ``data_source`` and ``data_inline``
        are provided.  It verifies that the inline snapshot matches the file.
        """
        from presentation_tool.chart.loader import ChartDataLoader

        issues: list[ChartIssue] = []

        if not element.data_source or element.data_inline is None:
            issues.append(ChartIssue(
                severity="info",
                field="consistency",
                message="Only one data source present; consistency check skipped.",
            ))
            return ChartValidationResult(
                element_id=element.element_id,
                is_valid=True,
                issues=issues,
            )

        loader = ChartDataLoader()
        try:
            df_file = loader.load_from_file(
                loader._resolve_path(element.data_source, base_path, element.element_id)
            )
        except Exception as exc:
            issues.append(ChartIssue(
                severity="warning",
                field="data_source",
                message=f"Could not load file for consistency check: {exc}",
            ))
            return ChartValidationResult(
                element_id=element.element_id,
                is_valid=True,
                issues=issues,
            )

        df_inline = loader.load_from_inline(element.data_inline)

        # Row / column count comparison
        if len(df_file) != len(df_inline):
            issues.append(ChartIssue(
                severity="warning",
                field="consistency",
                message=(
                    f"Row count mismatch: file has {len(df_file)} rows, "
                    f"data_inline has {len(df_inline)} rows."
                ),
            ))

        # Column name comparison
        file_cols = set(df_file.columns)
        inline_cols = set(df_inline.columns)
        only_in_file = file_cols - inline_cols
        only_in_inline = inline_cols - file_cols
        if only_in_file:
            issues.append(ChartIssue(
                severity="warning",
                field="consistency",
                message=f"Columns in file but not in data_inline: {sorted(only_in_file)}",
            ))
        if only_in_inline:
            issues.append(ChartIssue(
                severity="warning",
                field="consistency",
                message=f"Columns in data_inline but not in file: {sorted(only_in_inline)}",
            ))

        # Numeric value comparison on shared columns (within tolerance)
        shared_cols = file_cols & inline_cols
        for col in shared_cols:
            if (
                pd.api.types.is_numeric_dtype(df_file[col])
                and pd.api.types.is_numeric_dtype(df_inline[col])
                and len(df_file) == len(df_inline)
            ):
                try:
                    if not df_file[col].round(6).equals(df_inline[col].round(6)):
                        issues.append(ChartIssue(
                            severity="warning",
                            field=f"consistency.{col}",
                            message=(
                                f"Numeric values in column '{col}' differ between "
                                f"file and data_inline. data_inline may be stale."
                            ),
                        ))
                except Exception:
                    pass  # mixed types — skip

        is_valid = not any(i.severity == "error" for i in issues)
        return ChartValidationResult(
            element_id=element.element_id,
            is_valid=is_valid,
            issues=issues,
            row_count=len(df_inline),
            column_count=len(df_inline.columns),
        )

    # ── private chart-type checks ─────────────────────────────────────────────

    def _check_pie(
        self, df: pd.DataFrame, y_cols: list[str], issues: list[ChartIssue]
    ) -> None:
        if len(y_cols) > 1:
            issues.append(ChartIssue(
                severity="warning",
                field="y_columns",
                message=(
                    f"Pie chart uses only the first Y column; "
                    f"extra columns ({y_cols[1:]}) are ignored."
                ),
            ))
        if len(df) > 8:
            issues.append(ChartIssue(
                severity="warning",
                field="data",
                message=(
                    f"Pie chart has {len(df)} slices. "
                    f"Consider grouping small slices into 'Other' (recommended ≤ 7)."
                ),
            ))
        if y_cols and y_cols[0] in df.columns:
            col = y_cols[0]
            if pd.api.types.is_numeric_dtype(df[col]) and (df[col] < 0).any():
                issues.append(ChartIssue(
                    severity="error",
                    field=col,
                    message=f"Pie chart column '{col}' contains negative values, which are invalid for pie slices.",
                ))

    def _check_scatter(
        self, df: pd.DataFrame, x_col: str, issues: list[ChartIssue]
    ) -> None:
        if len(df) < 3:
            issues.append(ChartIssue(
                severity="warning",
                field="data",
                message=(
                    f"Scatter chart has only {len(df)} point(s). "
                    f"Trends are not visible with fewer than 3 data points."
                ),
            ))
