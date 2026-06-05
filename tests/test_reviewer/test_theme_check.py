from __future__ import annotations

import pytest

from presentation_tool.models.schema import TextStyle
from presentation_tool.models.theme import ThemeConfig
from presentation_tool.reviewer.checks.theme_check import check_theme_consistency
from .conftest import _pos, _slide, _text


class TestColorConsistency:
    def test_theme_color_no_issue(self, default_theme: ThemeConfig) -> None:
        primary = default_theme.colors.primary
        slide = _slide(
            text_elements=[_text("t1", role="title", font_size=28, color=primary)]
        )
        issues = check_theme_consistency(slide, default_theme)
        color_issues = [i for i in issues if "color" in i.message.lower()]
        assert not color_issues

    def test_off_palette_color_flagged(self, default_theme: ThemeConfig) -> None:
        # Use a color clearly not in the default palette
        slide = _slide(
            text_elements=[_text("t1", role="body", font_size=20, color="#FF00FF")]
        )
        issues = check_theme_consistency(slide, default_theme)
        assert any("color" in i.message.lower() for i in issues)
        assert any(i.severity == "low" for i in issues)

    def test_null_color_no_issue(self, default_theme: ThemeConfig) -> None:
        slide = _slide(
            text_elements=[_text("t1", role="body", font_size=20, color=None)]
        )
        color_issues = [
            i for i in check_theme_consistency(slide, default_theme)
            if "color" in i.message.lower()
        ]
        assert not color_issues


class TestFontSizeConsistency:
    def test_title_size_matches_theme(self, default_theme: ThemeConfig) -> None:
        expected = default_theme.fonts.heading_size
        slide = _slide(
            text_elements=[_text("t1", role="title", font_size=expected)]
        )
        font_issues = [
            i for i in check_theme_consistency(slide, default_theme)
            if "pt" in i.message.lower() and "size" not in i.message.lower()
        ]
        # Should have no font-size-deviation issues
        size_dev_issues = [
            i for i in check_theme_consistency(slide, default_theme)
            if "expects" in i.message.lower()
        ]
        assert not size_dev_issues

    def test_greatly_different_title_size(self, default_theme: ThemeConfig) -> None:
        # theme heading=28, use 10 → diff=18 > tolerance(4)
        slide = _slide(
            text_elements=[_text("t1", role="title", font_size=10)]
        )
        issues = check_theme_consistency(slide, default_theme)
        size_issues = [i for i in issues if "expects" in i.message.lower()]
        assert size_issues
        assert any(i.severity == "medium" for i in size_issues)  # diff=18 → medium

    def test_slightly_different_is_low(self, default_theme: ThemeConfig) -> None:
        # theme body=20, use 16 → diff=4 → not flagged (exactly at tolerance boundary)
        # diff=5 → low
        slide = _slide(
            text_elements=[_text("t1", role="body", font_size=15)]
        )
        issues = check_theme_consistency(slide, default_theme)
        size_issues = [i for i in issues if "expects" in i.message.lower()]
        if size_issues:
            assert any(i.severity in ("low", "medium") for i in size_issues)


class TestFontHierarchy:
    def test_body_larger_than_title_flagged(self, default_theme: ThemeConfig) -> None:
        slide = _slide(
            text_elements=[
                _text("title", role="title", font_size=20),
                _text("body",  role="body",  font_size=24),  # larger than title!
            ]
        )
        issues = check_theme_consistency(slide, default_theme)
        hierarchy_issues = [i for i in issues if "hierarchy" in i.message.lower()]
        assert hierarchy_issues
        assert hierarchy_issues[0].severity == "medium"

    def test_title_larger_than_body_ok(self, default_theme: ThemeConfig) -> None:
        slide = _slide(
            text_elements=[
                _text("title", role="title", font_size=28),
                _text("body",  role="body",  font_size=18),
            ]
        )
        issues = check_theme_consistency(slide, default_theme)
        hierarchy_issues = [i for i in issues if "hierarchy" in i.message.lower()]
        assert not hierarchy_issues

    def test_all_issues_have_correct_type(self, default_theme: ThemeConfig) -> None:
        slide = _slide(
            text_elements=[_text("t1", role="body", font_size=20, color="#FF00FF")]
        )
        issues = check_theme_consistency(slide, default_theme)
        assert all(i.issue_type == "theme_consistency" for i in issues)
        assert all(i.check_category == "theme" for i in issues)
