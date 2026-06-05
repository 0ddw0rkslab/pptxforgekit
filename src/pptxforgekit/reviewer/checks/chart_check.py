from __future__ import annotations

from pptxforgekit.models.review import ReviewIssue, Severity
from pptxforgekit.models.schema import ChartElement, SlideSchema

# Thresholds
_MAX_SERIES_BAR  = 5
_MAX_SERIES_LINE = 4
_MAX_PIE_SLICES  = 7
_MAX_SERIES_NAME_LEN = 20   # chars
_MIN_CHART_WIDTH_CM  = 5.0
_MIN_CHART_HEIGHT_CM = 3.0

# Scientific chart types that should have axis labels
_AXIS_LABEL_TYPES = {"bar", "line", "scatter"}


def check_chart_labels(slide: SlideSchema) -> list[ReviewIssue]:
    """Check chart elements for readability and labelling completeness."""
    issues: list[ReviewIssue] = []
    seq = 0

    for elem in slide.chart_elements:
        seq_start = seq

        # ── chart title ───────────────────────────────────────────────────────
        if not elem.title.strip():
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="chart_label_readability",
                check_category="chart",
                severity="low",
                message=(
                    f"Chart '{elem.element_id}' has no title. "
                    f"Audience cannot tell what the chart shows at a glance."
                ),
                suggested_fix="Add a concise title that describes the chart's key finding.",
                auto_fixable=False,
            ))

        # ── axis labels ───────────────────────────────────────────────────────
        if elem.chart_type in _AXIS_LABEL_TYPES:
            if not elem.y_label and not elem.y_unit:
                seq += 1
                issues.append(ReviewIssue(
                    issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                    slide_id=slide.slide_id,
                    element_id=elem.element_id,
                    issue_type="chart_label_readability",
                    check_category="chart",
                    severity="low",
                    message=(
                        f"Chart '{elem.element_id}' ({elem.chart_type}) "
                        f"has no Y-axis label or unit."
                    ),
                    suggested_fix=(
                        "Set 'y_label' and/or 'y_unit' so readers know "
                        "what the Y axis represents."
                    ),
                    auto_fixable=False,
                ))

        # ── too many series ───────────────────────────────────────────────────
        n_series = len(elem.y_columns) if elem.y_columns else 0
        if n_series > 0:
            limit = (
                _MAX_SERIES_LINE if elem.chart_type == "line"
                else _MAX_SERIES_BAR
            )
            if n_series > limit:
                seq += 1
                sev: Severity = "high" if n_series > limit + 3 else "medium"
                issues.append(ReviewIssue(
                    issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                    slide_id=slide.slide_id,
                    element_id=elem.element_id,
                    issue_type="chart_label_readability",
                    check_category="chart",
                    severity=sev,
                    message=(
                        f"Chart '{elem.element_id}' has {n_series} series "
                        f"(recommended ≤ {limit} for {elem.chart_type} charts). "
                        f"Legend and colors become hard to distinguish."
                    ),
                    suggested_fix=(
                        "Group similar series or split into multiple charts."
                    ),
                    auto_fixable=False,
                ))

        # ── long series names ─────────────────────────────────────────────────
        display_names = elem.series_names or elem.y_columns
        long_names = [n for n in display_names if len(n) > _MAX_SERIES_NAME_LEN]
        if long_names:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="chart_label_readability",
                check_category="chart",
                severity="low",
                message=(
                    f"Chart '{elem.element_id}' has series names longer than "
                    f"{_MAX_SERIES_NAME_LEN} chars: "
                    + ", ".join(f"'{n}'" for n in long_names[:3])
                    + (f" (and {len(long_names)-3} more)" if len(long_names) > 3 else "")
                    + ". Long names crowd the legend."
                ),
                suggested_fix=(
                    "Use shorter names in 'series_names' (abbreviate or use acronyms)."
                ),
                auto_fixable=False,
            ))

        # ── pie: too many slices (from inline data) ───────────────────────────
        if elem.chart_type == "pie" and elem.data_inline:
            n_slices = len(elem.data_inline)
            if n_slices > _MAX_PIE_SLICES:
                seq += 1
                issues.append(ReviewIssue(
                    issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                    slide_id=slide.slide_id,
                    element_id=elem.element_id,
                    issue_type="chart_label_readability",
                    check_category="chart",
                    severity="medium",
                    message=(
                        f"Pie chart '{elem.element_id}' has {n_slices} slices "
                        f"(recommended ≤ {_MAX_PIE_SLICES}). "
                        f"Small slices become unreadable."
                    ),
                    suggested_fix=(
                        "Group small slices into an 'Other' category."
                    ),
                    auto_fixable=False,
                ))

        # ── legend hidden with multiple series ────────────────────────────────
        if (
            elem.legend_position == "none"
            and n_series > 1
            and elem.chart_type != "pie"
        ):
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="chart_label_readability",
                check_category="chart",
                severity="medium",
                message=(
                    f"Chart '{elem.element_id}' has {n_series} series "
                    f"but the legend is hidden ('legend_position': 'none'). "
                    f"Series cannot be distinguished."
                ),
                suggested_fix=(
                    "Set 'legend_position' to 'right' or 'bottom', "
                    "or add data labels to differentiate series."
                ),
                auto_fixable=False,
            ))

        # ── data labels clutter ───────────────────────────────────────────────
        if elem.show_data_labels and n_series > 2 and elem.chart_type == "bar":
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="chart_label_readability",
                check_category="chart",
                severity="low",
                message=(
                    f"Chart '{elem.element_id}' shows data labels on "
                    f"{n_series} series simultaneously, which may clutter the chart."
                ),
                suggested_fix=(
                    "Disable data labels or limit to the most important series."
                ),
                auto_fixable=False,
            ))

        # ── chart area too small ──────────────────────────────────────────────
        p = elem.position
        if p.w < _MIN_CHART_WIDTH_CM or p.h < _MIN_CHART_HEIGHT_CM:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_chartlbl_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="chart_label_readability",
                check_category="chart",
                severity="medium",
                message=(
                    f"Chart '{elem.element_id}' area is very small "
                    f"({p.w:.1f}×{p.h:.1f} cm). "
                    f"Axis labels and data points will be unreadable."
                ),
                suggested_fix=(
                    f"Increase chart to at least "
                    f"{_MIN_CHART_WIDTH_CM}×{_MIN_CHART_HEIGHT_CM} cm."
                ),
                auto_fixable=False,
            ))

    return issues
