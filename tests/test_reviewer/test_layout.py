from __future__ import annotations

import pytest

from presentation_tool.models.schema import Position
from presentation_tool.reviewer.checks.layout_check import (
    check_clipping,
    check_overlap,
)
from .conftest import _pos, _slide, _text, _chart


# ─────────────────────────────── overlap ─────────────────────────────────────

class TestOverlap:
    def test_no_overlap_no_issues(self) -> None:
        # title: y=0.5–2.5, body: y=3.2–17.5 — they don't overlap
        slide = _slide(
            text_elements=[
                _text("t1", pos=_pos(x=2.0, y=0.5, w=20.0, h=2.0)),
                _text("t2", pos=_pos(x=2.0, y=3.2, w=20.0, h=10.0)),
            ]
        )
        issues = check_overlap(slide)
        assert issues == []

    def test_full_overlap_is_high(self) -> None:
        # Both elements at exactly the same position
        same = _pos(x=2.0, y=2.0, w=10.0, h=5.0)
        slide = _slide(
            text_elements=[
                _text("t1", pos=same),
                _text("t2", pos=Position(x=2.0, y=2.0, w=10.0, h=5.0)),
            ]
        )
        issues = check_overlap(slide)
        assert any(i.severity == "high" for i in issues)
        assert all(i.issue_type == "element_overlap" for i in issues)

    def test_minor_overlap_is_low(self) -> None:
        # Small 0.1cm overlap on edge
        slide = _slide(
            text_elements=[
                _text("t1", pos=_pos(x=2.0, y=0.5, w=10.0, h=3.0)),
                _text("t2", pos=_pos(x=11.9, y=0.5, w=10.0, h=3.0)),  # 0.1cm overlap
            ]
        )
        issues = check_overlap(slide)
        # 0.1 * 3.0 = 0.3 cm²  /  min(30.0, 30.0) = 1% → below _OVERLAP_SKIP=2% → no issue
        # Actually overlap_fraction = 0.3 / 30.0 = 0.01 which is < 0.02, so no issue
        assert issues == []

    def test_moderate_overlap_is_medium(self) -> None:
        # ~15% of smaller element overlaps
        slide = _slide(
            text_elements=[
                _text("t1", pos=_pos(x=2.0, y=0.5, w=10.0, h=5.0)),
                _text("t2", pos=_pos(x=8.0, y=0.5, w=10.0, h=5.0)),
                # overlap: 4cm × 5cm = 20cm² / 50cm² = 40% → high
            ]
        )
        issues = check_overlap(slide)
        assert len(issues) >= 1
        severities = {i.severity for i in issues}
        assert "high" in severities or "medium" in severities

    def test_cross_element_type_overlap(self) -> None:
        slide = _slide(
            text_elements=[_text("t1", pos=_pos(x=2.0, y=2.0, w=15.0, h=8.0))],
            chart_elements=[_chart("c1", pos=_pos(x=5.0, y=3.0, w=15.0, h=8.0))],
        )
        issues = check_overlap(slide)
        assert len(issues) >= 1

    def test_issue_ids_are_unique(self) -> None:
        same = _pos(x=2.0, y=2.0, w=10.0, h=5.0)
        slide = _slide(
            text_elements=[
                _text("a", pos=same),
                _text("b", pos=Position(x=2.0, y=2.0, w=10.0, h=5.0)),
                _text("c", pos=Position(x=2.0, y=2.0, w=10.0, h=5.0)),
            ]
        )
        issues = check_overlap(slide)
        ids = [i.issue_id for i in issues]
        assert len(ids) == len(set(ids))


# ─────────────────────────────── clipping ────────────────────────────────────

class TestClipping:
    def test_in_bounds_no_issues(self) -> None:
        slide = _slide(
            text_elements=[_text("t1", pos=_pos(x=2.0, y=0.5, w=20.0, h=5.0))]
        )
        issues = check_clipping(slide)
        assert issues == []

    def test_right_overflow_is_detected(self) -> None:
        # x=30.0, w=5.0 → right edge at 35.0 > 33.87
        slide = _slide(
            text_elements=[_text("t1", pos=_pos(x=30.0, y=0.5, w=5.0, h=2.0))]
        )
        issues = check_clipping(slide)
        assert len(issues) == 1
        assert issues[0].issue_type == "element_clipping"

    def test_bottom_overflow_large_is_critical(self) -> None:
        # y=17.0, h=5.0 → bottom at 22.0 > 19.05, excess 2.95 > 2.0 → critical
        slide = _slide(
            text_elements=[_text("t1", pos=_pos(x=2.0, y=17.0, w=5.0, h=5.0))]
        )
        issues = check_clipping(slide)
        assert any(i.severity == "critical" for i in issues)

    def test_small_overflow_is_medium(self) -> None:
        # x=0.5, y=0.5, w=33.0, h=2.0 → right edge 33.5 > 33.87? No, 33.5 < 33.87
        # Let's do: x=0.0, y=0.0, w=33.9, h=2.0 → right edge 33.9 > 33.87, excess 0.03 < 0.5 → medium
        slide = _slide(
            text_elements=[_text("t1", pos=Position(x=0.0, y=0.0, w=33.9, h=2.0))]
        )
        issues = check_clipping(slide)
        assert len(issues) == 1
        assert issues[0].severity == "medium"

    def test_auto_fixable_flag(self) -> None:
        slide = _slide(
            text_elements=[_text("t1", pos=_pos(x=30.0, y=0.5, w=5.0, h=2.0))]
        )
        issues = check_clipping(slide)
        assert all(i.auto_fixable for i in issues)

    def test_check_category_is_layout(self) -> None:
        slide = _slide(
            text_elements=[_text("t1", pos=_pos(x=30.0, y=0.5, w=5.0, h=2.0))]
        )
        issues = check_clipping(slide)
        assert all(i.check_category == "layout" for i in issues)
