from __future__ import annotations

import pytest

from presentation_tool.fixer.auto import AutoFixer
from presentation_tool.fixer.result import FixResult
from presentation_tool.models.review import ReviewIssue, ReviewReport
from presentation_tool.models.schema import (
    Position,
    PresentationMeta,
    PresentationSchema,
    SlideSchema,
    TextElement,
    TextStyle,
)


def _make_schema(*slides: SlideSchema) -> PresentationSchema:
    return PresentationSchema(
        presentation=PresentationMeta(title="Test", total_slides=len(slides)),
        slides=list(slides),
    )


def _make_slide(
    slide_id: str = "s001",
    *,
    text_elements: list[TextElement] | None = None,
) -> SlideSchema:
    return SlideSchema(
        slide_id=slide_id,
        title="Test Slide",
        layout_type="title_content",
        text_elements=text_elements or [],
    )


def _make_report(*issues: ReviewIssue) -> ReviewReport:
    return ReviewReport(
        pptx_file="test.pptx",
        schema_file="test.json",
        reviewed_at="2026-01-01T00:00:00Z",
        issues=list(issues),
    )


def _make_text(element_id: str, *, font_size: int = 18, x: float = 2.0, y: float = 3.0, w: float = 20.0, h: float = 10.0) -> TextElement:
    return TextElement(
        element_id=element_id,
        role="body",
        content="Sample text content",
        position=Position(x=x, y=y, w=w, h=h),
        style=TextStyle(font_size=font_size),
    )


@pytest.fixture
def fixer() -> AutoFixer:
    return AutoFixer()


class TestAutoFixerNoIssues:
    def test_returns_fix_result(self, fixer: AutoFixer) -> None:
        schema = _make_schema(_make_slide())
        report = _make_report()
        result = fixer.fix(schema, report)
        assert isinstance(result, FixResult)

    def test_no_issues_means_empty_applied(self, fixer: AutoFixer) -> None:
        schema = _make_schema(_make_slide())
        report = _make_report()
        result = fixer.fix(schema, report)
        assert result.n_fixed == 0
        assert result.n_remaining == 0

    def test_schema_is_preserved(self, fixer: AutoFixer) -> None:
        slide = _make_slide()
        schema = _make_schema(slide)
        report = _make_report()
        result = fixer.fix(schema, report)
        assert len(result.fixed_schema.slides) == 1


class TestAutoFixerMinimumFontSize:
    def test_raises_font_size(self, fixer: AutoFixer) -> None:
        elem = _make_text("t001", font_size=8)
        slide = _make_slide(text_elements=[elem])
        schema = _make_schema(slide)
        issue = ReviewIssue(
            issue_id="i001",
            slide_id="s001",
            element_id="t001",
            issue_type="minimum_font_size",
            check_category="text",
            severity="medium",
            message="Font too small",
            auto_fixable=True,
        )
        report = _make_report(issue)
        result = fixer.fix(schema, report)
        assert result.n_fixed == 1
        fixed_elem = result.fixed_schema.slides[0].text_elements[0]
        assert fixed_elem.style.font_size == 12

    def test_fix_recorded_in_applied(self, fixer: AutoFixer) -> None:
        elem = _make_text("t001", font_size=6)
        slide = _make_slide(text_elements=[elem])
        schema = _make_schema(slide)
        issue = ReviewIssue(
            issue_id="i001",
            slide_id="s001",
            element_id="t001",
            issue_type="minimum_font_size",
            check_category="text",
            severity="medium",
            message="Font too small",
            auto_fixable=True,
        )
        result = fixer.fix(schema, _make_report(issue))
        fix = result.applied_fixes[0]
        assert fix.issue_id == "i001"
        assert fix.slide_id == "s001"
        assert fix.element_id == "t001"


class TestAutoFixerClipping:
    def test_clipping_clamped(self, fixer: AutoFixer) -> None:
        # Element starts within bounds but width/height extend past the slide edge
        elem = _make_text("t001", x=2.0, y=2.0, w=40.0, h=25.0)
        slide = _make_slide(text_elements=[elem])
        schema = _make_schema(slide)
        issue = ReviewIssue(
            issue_id="i001",
            slide_id="s001",
            element_id="t001",
            issue_type="element_clipping",
            check_category="layout",
            severity="high",
            message="Element clips outside slide",
            auto_fixable=True,
        )
        result = fixer.fix(schema, _make_report(issue))
        assert result.n_fixed == 1
        p = result.fixed_schema.slides[0].text_elements[0].position
        assert p.x + p.w <= 33.87 + 0.01
        assert p.y + p.h <= 19.05 + 0.01


class TestAutoFixerUnfixable:
    def test_unfixable_goes_to_remaining(self, fixer: AutoFixer) -> None:
        slide = _make_slide()
        schema = _make_schema(slide)
        issue = ReviewIssue(
            issue_id="i001",
            slide_id="s001",
            element_id=None,
            issue_type="theme_consistency",
            check_category="theme",
            severity="low",
            message="Color mismatch",
            auto_fixable=False,
        )
        result = fixer.fix(schema, _make_report(issue))
        assert result.n_fixed == 0
        assert result.n_remaining == 1

    def test_unknown_slide_id_goes_to_remaining(self, fixer: AutoFixer) -> None:
        slide = _make_slide("s001")
        schema = _make_schema(slide)
        issue = ReviewIssue(
            issue_id="i001",
            slide_id="s999",
            element_id="t001",
            issue_type="minimum_font_size",
            check_category="text",
            severity="medium",
            message="Font too small",
            auto_fixable=True,
        )
        result = fixer.fix(schema, _make_report(issue))
        assert result.n_fixed == 0
        assert result.n_remaining == 1


class TestAutoFixerMixed:
    def test_mixed_fixable_and_unfixable(self, fixer: AutoFixer) -> None:
        elem = _make_text("t001", font_size=8)
        slide = _make_slide(text_elements=[elem])
        schema = _make_schema(slide)
        fixable = ReviewIssue(
            issue_id="i001",
            slide_id="s001",
            element_id="t001",
            issue_type="minimum_font_size",
            check_category="text",
            severity="medium",
            message="Font too small",
            auto_fixable=True,
        )
        unfixable = ReviewIssue(
            issue_id="i002",
            slide_id="s001",
            element_id=None,
            issue_type="theme_consistency",
            check_category="theme",
            severity="low",
            message="Color mismatch",
            auto_fixable=False,
        )
        result = fixer.fix(schema, _make_report(fixable, unfixable))
        assert result.n_fixed == 1
        assert result.n_remaining == 1

    def test_source_paths_preserved(self, fixer: AutoFixer) -> None:
        schema = _make_schema(_make_slide())
        report = _make_report()
        result = fixer.fix(schema, report, source_schema_file="s.json", source_report_file="r.json")
        assert result.source_schema_file == "s.json"
        assert result.source_report_file == "r.json"
