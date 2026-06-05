from __future__ import annotations

import logging
from pathlib import Path

from presentation_tool.models.review import ReviewIssue, Severity
from presentation_tool.models.schema import ChartElement, SlideSchema

logger = logging.getLogger(__name__)

_INLINE_DATA_STALE_THRESHOLD = 5   # number of row/column discrepancies that triggers "high"


def check_data_consistency(
    slide: SlideSchema,
    base_path: Path | None = None,
) -> list[ReviewIssue]:
    """Validate chart data sources for completeness and internal consistency."""
    issues: list[ReviewIssue] = []
    seq = 0

    for elem in slide.chart_elements:
        seq = _check_element(slide.slide_id, elem, base_path, issues, seq)

    return issues


def _check_element(
    slide_id: str,
    elem: ChartElement,
    base_path: Path | None,
    issues: list[ReviewIssue],
    seq: int,
) -> int:
    # ── inline data: column validation ───────────────────────────────────────
    if elem.data_inline is not None:
        seq = _check_inline_columns(slide_id, elem, issues, seq)

    # ── data_source file existence ────────────────────────────────────────────
    if elem.data_source:
        seq = _check_file_exists(slide_id, elem, base_path, issues, seq)

    # ── cross-source consistency ──────────────────────────────────────────────
    if elem.data_source and elem.data_inline is not None:
        seq = _check_cross_consistency(slide_id, elem, base_path, issues, seq)

    # ── inline: all same value (degenerate data) ──────────────────────────────
    if elem.data_inline and elem.y_columns:
        seq = _check_flat_data(slide_id, elem, issues, seq)

    return seq


def _check_inline_columns(
    slide_id: str,
    elem: ChartElement,
    issues: list[ReviewIssue],
    seq: int,
) -> int:
    if not elem.data_inline:
        return seq

    available_cols = set(elem.data_inline[0].keys()) if elem.data_inline else set()
    declared_y = set(elem.y_columns) if elem.y_columns else set()
    missing = declared_y - available_cols

    if missing:
        seq += 1
        issues.append(ReviewIssue(
            issue_id=f"{slide_id}_data_{seq:03d}",
            slide_id=slide_id,
            element_id=elem.element_id,
            issue_type="data_consistency",
            check_category="data",
            severity="high",
            message=(
                f"Chart '{elem.element_id}': y_columns "
                f"{sorted(missing)} are declared but not present in data_inline. "
                f"Available columns: {sorted(available_cols)}."
            ),
            suggested_fix=(
                "Fix the y_columns list or add the missing columns to data_inline."
            ),
            auto_fixable=False,
        ))

    if elem.x_column and elem.x_column not in available_cols:
        seq += 1
        issues.append(ReviewIssue(
            issue_id=f"{slide_id}_data_{seq:03d}",
            slide_id=slide_id,
            element_id=elem.element_id,
            issue_type="data_consistency",
            check_category="data",
            severity="high",
            message=(
                f"Chart '{elem.element_id}': x_column '{elem.x_column}' "
                f"is not present in data_inline. "
                f"Available columns: {sorted(available_cols)}."
            ),
            suggested_fix=(
                "Correct x_column to match a column in data_inline."
            ),
            auto_fixable=False,
        ))

    return seq


def _check_file_exists(
    slide_id: str,
    elem: ChartElement,
    base_path: Path | None,
    issues: list[ReviewIssue],
    seq: int,
) -> int:
    p = Path(elem.data_source)
    if not p.is_absolute() and base_path:
        candidate = base_path / p
        if candidate.exists():
            return seq
    if not p.exists():
        seq += 1
        issues.append(ReviewIssue(
            issue_id=f"{slide_id}_data_{seq:03d}",
            slide_id=slide_id,
            element_id=elem.element_id,
            issue_type="data_consistency",
            check_category="data",
            severity="high",
            message=(
                f"Chart '{elem.element_id}': data_source file "
                f"'{elem.data_source}' was not found. "
                f"The chart cannot be rendered from file."
            ),
            suggested_fix=(
                "Provide the correct file path or use data_inline instead."
            ),
            auto_fixable=False,
        ))
    return seq


def _check_cross_consistency(
    slide_id: str,
    elem: ChartElement,
    base_path: Path | None,
    issues: list[ReviewIssue],
    seq: int,
) -> int:
    """Compare data_inline values against the data_source file."""
    try:
        from presentation_tool.chart.validator import ChartDataValidator
        result = ChartDataValidator().validate_data_consistency(elem, base_path)
    except Exception as exc:
        logger.debug("Data consistency check failed for '%s': %s", elem.element_id, exc)
        return seq

    for issue in result.issues:
        if "differ" in issue.message.lower() or "stale" in issue.message.lower():
            seq += 1
            sev: Severity = "high" if "differ" in issue.message.lower() else "medium"
            issues.append(ReviewIssue(
                issue_id=f"{slide_id}_data_{seq:03d}",
                slide_id=slide_id,
                element_id=elem.element_id,
                issue_type="data_consistency",
                check_category="data",
                severity=sev,
                message=(
                    f"Chart '{elem.element_id}': {issue.message}"
                ),
                suggested_fix=(
                    "Re-generate data_inline from the source file, "
                    "or remove data_inline and rely solely on data_source."
                ),
                auto_fixable=False,
            ))
        elif "mismatch" in issue.message.lower():
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide_id}_data_{seq:03d}",
                slide_id=slide_id,
                element_id=elem.element_id,
                issue_type="data_consistency",
                check_category="data",
                severity="medium",
                message=f"Chart '{elem.element_id}': {issue.message}",
                suggested_fix="Synchronise data_inline with the source file.",
                auto_fixable=False,
            ))

    return seq


def _check_flat_data(
    slide_id: str,
    elem: ChartElement,
    issues: list[ReviewIssue],
    seq: int,
) -> int:
    """Warn when all values in a y_column are identical."""
    if not elem.data_inline or not elem.y_columns:
        return seq

    for col in elem.y_columns:
        values = [row.get(col) for row in elem.data_inline if col in row]
        numeric = [v for v in values if isinstance(v, (int, float))]
        if len(numeric) >= 2 and len(set(numeric)) == 1:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide_id}_data_{seq:03d}",
                slide_id=slide_id,
                element_id=elem.element_id,
                issue_type="data_consistency",
                check_category="data",
                severity="low",
                message=(
                    f"Chart '{elem.element_id}': column '{col}' has "
                    f"only one distinct value ({numeric[0]}). "
                    f"The chart will show a flat line or equal bars."
                ),
                suggested_fix=(
                    "Verify the data is correct. "
                    "Consider whether this chart adds value."
                ),
                auto_fixable=False,
            ))

    return seq
