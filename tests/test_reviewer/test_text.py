from __future__ import annotations

import pytest

from presentation_tool.models.schema import Position, TextStyle
from presentation_tool.models.theme import ThemeConfig
from presentation_tool.reviewer.checks.text_check import (
    check_font_size,
    check_text_density,
    check_text_overflow,
)
from .conftest import _pos, _slide, _text


# ────────────────────────── minimum font size ─────────────────────────────────

class TestFontSize:
    def test_above_minimum_no_issues(self, default_theme: ThemeConfig) -> None:
        slide = _slide(text_elements=[_text("t1", font_size=20)])
        assert check_font_size(slide, default_theme) == []

    def test_below_minimum_raises_issue(self, default_theme: ThemeConfig) -> None:
        slide = _slide(text_elements=[_text("t1", font_size=8)])
        issues = check_font_size(slide, default_theme)
        assert len(issues) == 1
        assert issues[0].issue_type == "minimum_font_size"

    def test_slightly_below_is_medium(self, default_theme: ThemeConfig) -> None:
        # min_size=12, font=10 → diff=2 → low
        slide = _slide(text_elements=[_text("t1", font_size=10)])
        issues = check_font_size(slide, default_theme)
        assert issues[0].severity == "low"

    def test_far_below_is_high(self, default_theme: ThemeConfig) -> None:
        # font=6 → diff=6 → high
        slide = _slide(text_elements=[_text("t1", font_size=6)])
        issues = check_font_size(slide, default_theme)
        assert issues[0].severity == "high"

    def test_auto_fixable(self, default_theme: ThemeConfig) -> None:
        slide = _slide(text_elements=[_text("t1", font_size=8)])
        issues = check_font_size(slide, default_theme)
        assert issues[0].auto_fixable

    def test_exactly_at_minimum_no_issue(self, default_theme: ThemeConfig) -> None:
        min_size = default_theme.fonts.min_size
        slide = _slide(text_elements=[_text("t1", font_size=min_size)])
        assert check_font_size(slide, default_theme) == []


# ────────────────────────── text overflow ─────────────────────────────────────

class TestTextOverflow:
    def test_short_text_no_overflow(self) -> None:
        content = "Short text."
        slide = _slide(text_elements=[_text("t1", content=content, font_size=20)])
        assert check_text_overflow(slide) == []

    def test_very_long_text_overflows(self) -> None:
        # 2000 chars in a 10×3cm box at 20pt → definitely overflows
        content = "word " * 400
        slide = _slide(
            text_elements=[_text(
                "t1",
                content=content,
                font_size=20,
                pos=Position(x=2.0, y=0.5, w=10.0, h=3.0),
            )]
        )
        issues = check_text_overflow(slide)
        assert len(issues) == 1
        assert issues[0].issue_type == "text_overflow"
        assert issues[0].severity in ("high", "critical")

    def test_large_font_in_small_box_overflows(self) -> None:
        lines = "\n".join(f"Bullet point {i}" for i in range(15))
        slide = _slide(
            text_elements=[_text(
                "t1",
                content=lines,
                font_size=28,
                pos=Position(x=2.0, y=0.5, w=15.0, h=4.0),
            )]
        )
        issues = check_text_overflow(slide)
        assert len(issues) >= 1

    def test_issue_has_ratio_in_message(self) -> None:
        content = "word " * 300
        slide = _slide(
            text_elements=[_text(
                "t1",
                content=content,
                font_size=20,
                pos=Position(x=2.0, y=0.5, w=10.0, h=3.0),
            )]
        )
        issues = check_text_overflow(slide)
        if issues:
            assert "ratio" in issues[0].message.lower() or "lines" in issues[0].message.lower()


# ────────────────────────── text density ─────────────────────────────────────

class TestTextDensity:
    def test_few_bullets_no_issue(self, default_theme: ThemeConfig) -> None:
        content = "• A\n• B\n• C"
        slide = _slide(text_elements=[_text("t1", content=content, role="body")])
        assert check_text_density(slide, default_theme) == []

    def test_too_many_bullets(self, default_theme: ThemeConfig) -> None:
        bullets = "\n".join(f"• Bullet {i}" for i in range(10))
        slide = _slide(text_elements=[_text("t1", content=bullets, role="body")])
        issues = check_text_density(slide, default_theme)
        assert any(i.issue_type == "excessive_text_density" for i in issues)

    def test_high_word_count(self, default_theme: ThemeConfig) -> None:
        content = " ".join(f"word{i}" for i in range(140))
        slide = _slide(text_elements=[_text("t1", content=content, role="body")])
        issues = check_text_density(slide, default_theme)
        assert any(i.severity == "high" for i in issues)

    def test_moderate_word_count_is_medium(self, default_theme: ThemeConfig) -> None:
        content = " ".join(f"word{i}" for i in range(90))
        slide = _slide(text_elements=[_text("t1", content=content, role="body")])
        issues = check_text_density(slide, default_theme)
        assert any(i.severity == "medium" for i in issues)

    def test_title_role_not_density_checked(self, default_theme: ThemeConfig) -> None:
        # Title role should not be checked for density
        content = " ".join(f"word{i}" for i in range(100))
        slide = _slide(text_elements=[_text("t1", content=content, role="title")])
        assert check_text_density(slide, default_theme) == []
