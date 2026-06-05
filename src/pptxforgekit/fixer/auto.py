from __future__ import annotations

import logging

from pptxforgekit.fixer import ops
from pptxforgekit.fixer.result import AppliedFix, FixResult
from pptxforgekit.models.review import ReviewIssue, ReviewReport
from pptxforgekit.models.schema import PresentationSchema, SlideSchema

logger = logging.getLogger(__name__)


class AutoFixer:
    def fix(
        self,
        schema: PresentationSchema,
        report: ReviewReport,
        source_schema_file: str = "",
        source_report_file: str = "",
    ) -> FixResult:
        fixable = [i for i in report.issues if i.auto_fixable]
        unfixable = [i for i in report.issues if not i.auto_fixable]
        logger.info(
            "Auto-fixer: %d fixable / %d total issues",
            len(fixable),
            report.total_issues,
        )

        slides = [SlideSchema.model_validate(s.model_dump()) for s in schema.slides]
        slide_by_id = {s.slide_id: s for s in slides}

        applied: list[AppliedFix] = []
        still_remaining: list[ReviewIssue] = list(unfixable)
        from pptxforgekit.fixer.result import SplitSuggestion
        split_suggestions: list[SplitSuggestion] = []

        min_font_size = 12

        for issue in fixable:
            slide = slide_by_id.get(issue.slide_id)
            if slide is None:
                still_remaining.append(issue)
                continue

            fix = self._apply_fix(slide, issue, min_font_size, split_suggestions)
            if fix is not None:
                fix.issue_id = issue.issue_id
                fix.slide_id = issue.slide_id
                applied.append(fix)
            else:
                still_remaining.append(issue)

        fixed_schema = PresentationSchema(
            schema_version=schema.schema_version,
            presentation=schema.presentation,
            slides=slides,
        )

        return FixResult(
            source_schema_file=source_schema_file,
            source_report_file=source_report_file,
            fixed_schema=fixed_schema,
            applied_fixes=applied,
            remaining_issues=still_remaining,
            split_suggestions=split_suggestions,
        )

    # ── routing ───────────────────────────────────────────────────────────────

    def _apply_fix(
        self,
        slide: SlideSchema,
        issue: ReviewIssue,
        min_font_size: int,
        split_suggestions: list,
    ) -> AppliedFix | None:
        itype = issue.issue_type

        if itype == "element_clipping":
            elem = ops.find_element(slide, issue.element_id or "")
            if elem is None:
                return None
            return ops.fix_clipping(elem)

        if itype == "element_overlap":
            secondary_id = issue.context.get("secondary_element_id")
            if not issue.element_id or not secondary_id:
                return None
            elem_a = ops.find_element(slide, issue.element_id)
            elem_b = ops.find_element(slide, secondary_id)
            if elem_a is None or elem_b is None:
                return None
            return ops.fix_overlap(elem_a, elem_b)

        if itype == "minimum_font_size":
            if not issue.element_id:
                return None
            for elem in slide.text_elements:
                if elem.element_id == issue.element_id:
                    return ops.fix_minimum_font_size(elem, min_font_size)
            return None

        if itype == "text_overflow":
            if not issue.element_id:
                return None
            for elem in slide.text_elements:
                if elem.element_id == issue.element_id:
                    return ops.fix_text_overflow(
                        elem, issue.context, min_font_size
                    )
            return None

        if itype == "excessive_text_density":
            if not issue.element_id:
                return None
            for elem in slide.text_elements:
                if elem.element_id == issue.element_id:
                    suggestion = ops.generate_split_suggestion(issue, elem)
                    split_suggestions.append(suggestion)
            return None

        logger.debug("No auto-fix handler for issue_type '%s'", itype)
        return None
