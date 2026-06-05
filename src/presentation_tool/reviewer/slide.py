from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from presentation_tool.models.review import ReviewIssue, ReviewReport, SEVERITY_ORDER
from presentation_tool.models.schema import PresentationSchema, SlideSchema
from presentation_tool.models.theme import ThemeConfig

from .checks.chart_check import check_chart_labels
from .checks.data_check import check_data_consistency
from .checks.image_check import check_image_resolution
from .checks.layout_check import check_clipping, check_overlap
from .checks.text_check import check_font_size, check_text_density, check_text_overflow
from .checks.theme_check import check_theme_consistency

logger = logging.getLogger(__name__)


class SlideReviewer:
    """Run all review checks on a PresentationSchema and return a ReviewReport.

    Checks are applied in this order (most structural → most stylistic):
    1. element_clipping
    2. element_overlap
    3. minimum_font_size
    4. text_overflow
    5. excessive_text_density
    6. image_resolution / image_not_found
    7. chart_label_readability
    8. theme_consistency
    9. data_consistency
    """

    def review(
        self,
        schema: PresentationSchema,
        pptx_path: Path,
        schema_path: Path,
        theme: ThemeConfig,
        base_path: Path | None = None,
    ) -> ReviewReport:
        """Review every slide in ``schema`` and return a ``ReviewReport``.

        Args:
            schema:      The parsed PresentationSchema.
            pptx_path:   Path to the rendered .pptx (used as metadata in the report).
            schema_path: Path to the slides.json file (used as metadata).
            theme:       Theme configuration for consistency checks.
            base_path:   Directory used to resolve relative image / data file paths.
                         Defaults to ``schema_path.parent``.
        """
        resolved_base = base_path or schema_path.parent
        logger.info(
            "Reviewing %d slides | base_path=%s",
            len(schema.slides), resolved_base,
        )

        all_issues: list[ReviewIssue] = []

        for slide in schema.slides:
            slide_issues = self._review_slide(slide, theme, resolved_base)
            all_issues.extend(slide_issues)
            if slide_issues:
                worst = max(slide_issues, key=lambda i: SEVERITY_ORDER[i.severity])
                logger.debug(
                    "Slide '%s': %d issue(s) (worst: %s)",
                    slide.slide_id, len(slide_issues), worst.severity,
                )

        report = ReviewReport(
            pptx_file=str(pptx_path),
            schema_file=str(schema_path),
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            issues=all_issues,
        )

        logger.info(
            "Review complete: %d issue(s) | critical=%d high=%d medium=%d low=%d",
            report.total_issues,
            report.summary.get("critical", 0),
            report.summary.get("high", 0),
            report.summary.get("medium", 0),
            report.summary.get("low", 0),
        )
        return report

    # ── per-slide dispatch ────────────────────────────────────────────────────

    def _review_slide(
        self,
        slide: SlideSchema,
        theme: ThemeConfig,
        base_path: Path,
    ) -> list[ReviewIssue]:
        """Run all checks on a single slide and collect issues."""
        issues: list[ReviewIssue] = []

        # ── 1. layout ────────────────────────────────────────────────────────
        issues.extend(check_clipping(slide))
        issues.extend(check_overlap(slide))

        # ── 2. text ──────────────────────────────────────────────────────────
        issues.extend(check_font_size(slide, theme))
        issues.extend(check_text_overflow(slide))
        issues.extend(check_text_density(slide, theme))

        # ── 3. image ─────────────────────────────────────────────────────────
        issues.extend(check_image_resolution(slide, base_path))

        # ── 4. chart ─────────────────────────────────────────────────────────
        issues.extend(check_chart_labels(slide))

        # ── 5. theme ─────────────────────────────────────────────────────────
        issues.extend(check_theme_consistency(slide, theme))

        # ── 6. data ──────────────────────────────────────────────────────────
        issues.extend(check_data_consistency(slide, base_path))

        return issues
