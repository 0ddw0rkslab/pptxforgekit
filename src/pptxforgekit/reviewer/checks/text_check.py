from __future__ import annotations

from pptxforgekit.models.review import ReviewIssue, Severity
from pptxforgekit.models.schema import SlideSchema
from pptxforgekit.models.theme import ThemeConfig

# Typography constants (shared with fixer/ops.py)
PT_TO_CM        = 0.0353
CHAR_WIDTH_RATIO = 0.55   # avg char width ≈ font_size × 0.55 pt
LINE_HEIGHT_RATIO = 1.25  # line height ≈ font_size × 1.25 pt

# Density limits
_WORD_COUNT_MEDIUM = 80
_WORD_COUNT_HIGH   = 130
_LINE_COUNT_MEDIUM = 8
_LINE_COUNT_HIGH   = 14

# Overflow thresholds
_OVERFLOW_MEDIUM   = 1.05
_OVERFLOW_HIGH     = 1.25
_OVERFLOW_CRITICAL = 1.60


# ── typography helpers ────────────────────────────────────────────────────────

def chars_per_line(width_cm: float, font_size_pt: int) -> float:
    char_w = font_size_pt * CHAR_WIDTH_RATIO * PT_TO_CM
    return (width_cm / char_w) if char_w > 0 else 0.0


def lines_available(height_cm: float, font_size_pt: int) -> float:
    line_h = font_size_pt * LINE_HEIGHT_RATIO * PT_TO_CM
    return (height_cm / line_h) if line_h > 0 else 0.0


def estimate_rendered_lines(content: str, width_cm: float, font_size_pt: int) -> int:
    """Estimate rendered line count accounting for word-wrap."""
    cpl = chars_per_line(width_cm, font_size_pt)
    if cpl <= 0:
        return len(content.splitlines())
    total = 0
    for raw in content.splitlines():
        text = raw.strip()
        if not text:
            total += 1
        else:
            total += max(1, -(-len(text) // int(cpl)))
    return total


# ── public check functions ────────────────────────────────────────────────────

def check_font_size(slide: SlideSchema, theme: ThemeConfig) -> list[ReviewIssue]:
    """Report text elements whose font size is below the theme minimum."""
    issues: list[ReviewIssue] = []
    min_font = int(theme.get_rule_value("min_font_size", theme.fonts.min_size))
    seq = 0

    for elem in slide.text_elements:
        fs = elem.style.font_size
        if fs >= min_font:
            continue
        seq += 1
        diff = min_font - fs
        severity: Severity = "high" if diff >= 6 else "medium" if diff >= 3 else "low"
        issues.append(ReviewIssue(
            issue_id=f"{slide.slide_id}_fontsize_{seq:03d}",
            slide_id=slide.slide_id,
            element_id=elem.element_id,
            issue_type="minimum_font_size",
            check_category="text",
            severity=severity,
            message=(
                f"'{elem.element_id}' uses {fs}pt, "
                f"below the theme minimum of {min_font}pt."
            ),
            suggested_fix=f"Increase font size to at least {min_font}pt.",
            auto_fixable=True,
            context={"current_font_size": fs, "minimum_font_size": min_font},
        ))

    return issues


def check_text_overflow(slide: SlideSchema) -> list[ReviewIssue]:
    """Estimate whether text content overflows its bounding box."""
    issues: list[ReviewIssue] = []
    seq = 0

    for elem in slide.text_elements:
        if not elem.content.strip():
            continue
        fs = elem.style.font_size
        estimated = estimate_rendered_lines(elem.content, elem.position.w, fs)
        avail = lines_available(elem.position.h, fs)
        if avail <= 0:
            continue
        ratio = estimated / avail
        if ratio < _OVERFLOW_MEDIUM:
            continue

        seq += 1
        severity: Severity = (
            "critical" if ratio >= _OVERFLOW_CRITICAL
            else "high" if ratio >= _OVERFLOW_HIGH
            else "medium"
        )
        issues.append(ReviewIssue(
            issue_id=f"{slide.slide_id}_overflow_{seq:03d}",
            slide_id=slide.slide_id,
            element_id=elem.element_id,
            issue_type="text_overflow",
            check_category="text",
            severity=severity,
            message=(
                f"'{elem.element_id}' likely overflows its box: "
                f"~{estimated} rendered lines vs ~{avail:.0f} available "
                f"(ratio {ratio:.2f} at {fs}pt)."
            ),
            suggested_fix=(
                "Reduce text, increase box height, or decrease font size."
            ),
            auto_fixable=True,
            context={
                "estimated_lines": estimated,
                "lines_available": round(avail, 1),
                "overflow_ratio": round(ratio, 3),
                "font_size": fs,
            },
        ))

    return issues


def check_text_density(slide: SlideSchema, theme: ThemeConfig) -> list[ReviewIssue]:
    """Flag text elements with too many bullets or too many words."""
    issues: list[ReviewIssue] = []
    max_bullets = int(theme.get_rule_value("max_bullets", 6))
    seq = 0

    for elem in slide.text_elements:
        if elem.role not in ("body", "subtitle"):
            continue

        lines = elem.content.splitlines()
        bullet_lines = [ln for ln in lines if ln.strip().startswith(("•", "-", "*", "–"))]
        word_count = len(elem.content.split())

        if len(bullet_lines) > max_bullets:
            seq += 1
            over = len(bullet_lines) - max_bullets
            sev: Severity = "high" if over >= 4 else "medium" if over >= 2 else "low"
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_density_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="excessive_text_density",
                check_category="text",
                severity=sev,
                message=(
                    f"'{elem.element_id}' has {len(bullet_lines)} bullet points "
                    f"(theme limit: {max_bullets})."
                ),
                suggested_fix="Remove bullets or split content across slides.",
                auto_fixable=False,
                context={
                    "bullet_count": len(bullet_lines),
                    "max_bullets": max_bullets,
                    "word_count": word_count,
                },
            ))
        elif word_count > _WORD_COUNT_HIGH:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_density_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="excessive_text_density",
                check_category="text",
                severity="high",
                message=(
                    f"'{elem.element_id}' contains {word_count} words — "
                    f"too dense for a presentation slide."
                ),
                suggested_fix="Summarise or split across slides. Aim for < 80 words.",
                auto_fixable=False,
                context={"word_count": word_count, "bullet_count": len(bullet_lines), "max_bullets": max_bullets},
            ))
        elif word_count > _WORD_COUNT_MEDIUM:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_density_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="excessive_text_density",
                check_category="text",
                severity="medium",
                message=(
                    f"'{elem.element_id}' contains {word_count} words "
                    f"(recommended < {_WORD_COUNT_MEDIUM})."
                ),
                suggested_fix="Consider trimming or splitting the text.",
                auto_fixable=False,
                context={"word_count": word_count, "bullet_count": len(bullet_lines), "max_bullets": max_bullets},
            ))

    return issues
