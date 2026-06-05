"""Pure fix operations — each function mutates one element and returns an AppliedFix.

All functions return ``None`` when the fix cannot be applied (e.g. no room to expand).
The caller (AutoFixer) is responsible for falling through to ``remaining_issues``.
"""
from __future__ import annotations

import logging
from typing import Any

from pptxforgekit.fixer.result import AppliedFix, SplitSuggestion
from pptxforgekit.models.review import ReviewIssue
from pptxforgekit.models.schema import (
    ChartElement,
    ImageElement,
    SlideSchema,
    TableElement,
    TextElement,
)

logger = logging.getLogger(__name__)

# Slide boundary constants (cm)
SLIDE_W = 33.87
SLIDE_H = 19.05
GAP     = 0.3    # minimum gap between elements after push-apart

# Typography replication (keeps fixer independent of reviewer internals)
_PT_TO_CM         = 0.0353
_CHAR_WIDTH_RATIO  = 0.55
_LINE_HEIGHT_RATIO = 1.25
_MIN_BOX_DIM       = 1.0   # elements must be at least 1 cm in each dimension


# ─────────────────────────── element lookup ───────────────────────────────────

def all_elements(slide: SlideSchema) -> list[Any]:
    return [
        *slide.text_elements,
        *slide.chart_elements,
        *slide.image_elements,
        *slide.table_elements,
    ]


def find_element(slide: SlideSchema, element_id: str) -> Any | None:
    for elem in all_elements(slide):
        if elem.element_id == element_id:
            return elem
    return None


# ─────────────────────────── fix: clipping ───────────────────────────────────

def fix_clipping(elem: Any, slide_w: float = SLIDE_W, slide_h: float = SLIDE_H) -> AppliedFix:
    """Clamp element position and size so it fits within the slide."""
    p = elem.position
    before = {"x": p.x, "y": p.y, "w": p.w, "h": p.h}

    new_x = max(0.0, p.x)
    new_y = max(0.0, p.y)
    new_w = max(_MIN_BOX_DIM, min(p.w, slide_w - new_x))
    new_h = max(_MIN_BOX_DIM, min(p.h, slide_h - new_y))

    p.x = new_x
    p.y = new_y
    p.w = new_w
    p.h = new_h

    after = {"x": p.x, "y": p.y, "w": p.w, "h": p.h}
    changes = _position_diff(before, after)

    return AppliedFix(
        issue_id="",   # filled in by AutoFixer
        issue_type="element_clipping",
        slide_id="",
        element_id=elem.element_id,
        description=f"Clamped to slide bounds: {changes}",
        before=before,
        after=after,
    )


# ─────────────────────────── fix: overlap ────────────────────────────────────

def fix_overlap(
    elem_a: Any,
    elem_b: Any,
    slide_w: float = SLIDE_W,
    slide_h: float = SLIDE_H,
) -> AppliedFix | None:
    """Push elem_b away from elem_a to resolve their overlap.

    Strategy: pick the direction (down or right) that requires the smallest
    movement, then verify the new position fits within the slide.
    Returns ``None`` when no valid position can be found.
    """
    pa = elem_a.position
    pb = elem_b.position
    before = {"x": pb.x, "y": pb.y, "w": pb.w, "h": pb.h}

    # Movement needed to push B out in each direction
    push_down  = (pa.y + pa.h) - pb.y + GAP   # B's top must clear A's bottom
    push_right = (pa.x + pa.w) - pb.x + GAP   # B's left must clear A's right

    candidates: list[tuple[str, float]] = []
    if push_down > 0:
        candidates.append(("down", push_down))
    if push_right > 0:
        candidates.append(("right", push_right))

    if not candidates:
        return None   # elements don't actually overlap in a pushable direction

    direction, distance = min(candidates, key=lambda t: t[1])

    if direction == "down":
        new_y = pa.y + pa.h + GAP
        # Try to fit without resizing first
        if new_y + pb.h <= slide_h:
            pb.y = new_y
            after = {"x": pb.x, "y": pb.y, "w": pb.w, "h": pb.h}
            desc = (
                f"Pushed '{elem_b.element_id}' down {distance:.2f} cm "
                f"(y: {before['y']:.2f} -> {pb.y:.2f})"
            )
        else:
            # Shrink height to fit below A
            new_h = max(_MIN_BOX_DIM, slide_h - new_y - 0.1)
            if new_y + new_h > slide_h or new_h < _MIN_BOX_DIM:
                return None   # no room below
            pb.y = new_y
            pb.h = new_h
            after = {"x": pb.x, "y": pb.y, "w": pb.w, "h": pb.h}
            desc = (
                f"Pushed '{elem_b.element_id}' down and shrunk: "
                f"y {before['y']:.2f}->{pb.y:.2f}, h {before['h']:.2f}->{pb.h:.2f}"
            )
    else:   # direction == "right"
        new_x = pa.x + pa.w + GAP
        if new_x + pb.w <= slide_w:
            pb.x = new_x
            after = {"x": pb.x, "y": pb.y, "w": pb.w, "h": pb.h}
            desc = (
                f"Pushed '{elem_b.element_id}' right {distance:.2f} cm "
                f"(x: {before['x']:.2f} -> {pb.x:.2f})"
            )
        else:
            new_w = max(_MIN_BOX_DIM, slide_w - new_x - 0.1)
            if new_x + new_w > slide_w or new_w < _MIN_BOX_DIM:
                return None
            pb.x = new_x
            pb.w = new_w
            after = {"x": pb.x, "y": pb.y, "w": pb.w, "h": pb.h}
            desc = (
                f"Pushed '{elem_b.element_id}' right and shrunk: "
                f"x {before['x']:.2f}->{pb.x:.2f}, w {before['w']:.2f}->{pb.w:.2f}"
            )

    return AppliedFix(
        issue_id="",
        issue_type="element_overlap",
        slide_id="",
        element_id=elem_b.element_id,
        description=desc,
        before=before,
        after=after,
    )


# ─────────────────────────── fix: minimum font size ──────────────────────────

def fix_minimum_font_size(
    elem: TextElement,
    min_font_size: int,
) -> AppliedFix:
    """Raise font size to the theme minimum."""
    old = elem.style.font_size
    elem.style.font_size = min_font_size
    return AppliedFix(
        issue_id="",
        issue_type="minimum_font_size",
        slide_id="",
        element_id=elem.element_id,
        description=f"Raised font size: {old}pt -> {min_font_size}pt",
        before={"font_size": old},
        after={"font_size": min_font_size},
    )


# ─────────────────────────── fix: text overflow ───────────────────────────────

def fix_text_overflow(
    elem: TextElement,
    context: dict[str, Any],
    min_font_size: int,
    slide_h: float = SLIDE_H,
) -> AppliedFix | None:
    """Try to resolve text overflow via box expansion or font reduction.

    Priority:
    1. Expand the text box height (if there is room below)
    2. Reduce the font size (down to min_font_size)
    Returns ``None`` if neither strategy can make the text fit.
    """
    p = elem.position
    fs = elem.style.font_size
    content = elem.content
    before: dict[str, Any] = {"x": p.x, "y": p.y, "w": p.w, "h": p.h, "font_size": fs}

    estimated = context.get("estimated_lines", _estimate_lines(content, p.w, fs))

    # ── strategy 1: expand box height ─────────────────────────────────────────
    needed_h = _h_for_lines(estimated, fs, slack=0.5)
    if p.y + needed_h <= slide_h - 0.1:
        old_h = p.h
        p.h = needed_h
        return AppliedFix(
            issue_id="",
            issue_type="text_overflow",
            slide_id="",
            element_id=elem.element_id,
            description=(
                f"Expanded text box height: {old_h:.2f}cm -> {needed_h:.2f}cm "
                f"to fit ~{estimated} lines"
            ),
            before=before,
            after={"x": p.x, "y": p.y, "w": p.w, "h": p.h, "font_size": fs},
        )

    # ── strategy 2: reduce font size ──────────────────────────────────────────
    available_h = slide_h - p.y - 0.1
    for try_fs in range(fs - 1, min_font_size - 1, -1):
        avail = _lines_available(available_h, try_fs)
        est = _estimate_lines(content, p.w, try_fs)
        if est <= avail:
            old_fs = elem.style.font_size
            elem.style.font_size = try_fs
            return AppliedFix(
                issue_id="",
                issue_type="text_overflow",
                slide_id="",
                element_id=elem.element_id,
                description=(
                    f"Reduced font size: {old_fs}pt -> {try_fs}pt "
                    f"to fit ~{est} lines"
                ),
                before=before,
                after={"x": p.x, "y": p.y, "w": p.w, "h": p.h, "font_size": try_fs},
            )

    return None   # can't fix even at minimum font size


# ─────────────────────────── fix: resize graphic ─────────────────────────────

def fix_graphic_clipping(
    elem: ChartElement | ImageElement | TableElement,
    slide_w: float = SLIDE_W,
    slide_h: float = SLIDE_H,
) -> AppliedFix:
    """Same clamp logic as fix_clipping, specialised for graphic elements."""
    return fix_clipping(elem, slide_w, slide_h)


# ─────────────────────────── suggestion: split ───────────────────────────────

def generate_split_suggestion(
    issue: ReviewIssue,
    elem: TextElement,
) -> SplitSuggestion:
    """Compute where to split dense text content and return a suggestion."""
    ctx = issue.context
    content = elem.content
    lines = content.splitlines()
    max_bullets = ctx.get("max_bullets", 6)
    bullet_count = ctx.get("bullet_count", 0)
    word_count = ctx.get("word_count", len(content.split()))

    if bullet_count > max_bullets:
        split_idx = _split_at_bullet(lines, max_bullets)
        reason = (
            f"{bullet_count} bullet points exceed the theme limit of {max_bullets}. "
            f"Move bullets {max_bullets + 1}–{bullet_count} to a new slide."
        )
    else:
        # Word-count-based: split near the middle sentence boundary
        split_idx = _split_at_words(lines, word_count // 2)
        reason = (
            f"{word_count} words exceed the recommended limit of 80. "
            f"Split content roughly in half."
        )

    part_a = "\n".join(lines[:split_idx]).strip()
    part_b = "\n".join(lines[split_idx:]).strip()

    return SplitSuggestion(
        issue_id=issue.issue_id,
        slide_id=issue.slide_id,
        element_id=elem.element_id,
        content_part_a=part_a,
        content_part_b=part_b,
        split_at_line=split_idx,
        reason=reason,
    )


# ─────────────────────────── private helpers ─────────────────────────────────

def _lines_available(height_cm: float, font_size_pt: int) -> float:
    line_h = font_size_pt * _LINE_HEIGHT_RATIO * _PT_TO_CM
    return height_cm / line_h if line_h > 0 else 0.0


def _h_for_lines(n_lines: int, font_size_pt: int, slack: float = 0.3) -> float:
    """Return the height (cm) needed to fit n_lines at font_size_pt."""
    line_h = font_size_pt * _LINE_HEIGHT_RATIO * _PT_TO_CM
    return n_lines * line_h + slack


def _estimate_lines(content: str, width_cm: float, font_size_pt: int) -> int:
    char_w = font_size_pt * _CHAR_WIDTH_RATIO * _PT_TO_CM
    cpl = width_cm / char_w if char_w > 0 else 1
    total = 0
    for raw in content.splitlines():
        text = raw.strip()
        total += 1 if not text else max(1, -(-len(text) // int(cpl)))
    return total


def _split_at_bullet(lines: list[str], max_bullets: int) -> int:
    """Return the index of the line after the max_bullets-th bullet."""
    bullet_seen = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(("•", "-", "*", "–")):
            bullet_seen += 1
            if bullet_seen >= max_bullets:
                return i + 1
    return len(lines) // 2


def _split_at_words(lines: list[str], target_words: int) -> int:
    """Return the line index closest to target_words cumulative words."""
    cumulative = 0
    for i, line in enumerate(lines):
        cumulative += len(line.split())
        if cumulative >= target_words:
            return i + 1
    return max(1, len(lines) // 2)


def _position_diff(before: dict[str, Any], after: dict[str, Any]) -> str:
    changes = []
    for key in ("x", "y", "w", "h"):
        b, a = before.get(key, "?"), after.get(key, "?")
        if isinstance(b, float) and isinstance(a, float) and abs(b - a) > 0.001:
            changes.append(f"{key}: {b:.2f}->{a:.2f}")
    return ", ".join(changes) or "no change"
