from __future__ import annotations

from presentation_tool.models.review import ReviewIssue, Severity
from presentation_tool.models.schema import SlideSchema, TextElement
from presentation_tool.models.theme import ThemeConfig

# Tolerance for "significantly different" font size (in points)
_FONT_SIZE_TOLERANCE = 4

# Roles that should use the title font and title-sized text
_TITLE_ROLES = {"title", "subtitle"}
_BODY_ROLES = {"body", "caption", "label", "footer"}


def _theme_palette(theme: ThemeConfig) -> set[str]:
    return {
        theme.colors.primary.upper(),
        theme.colors.secondary.upper(),
        theme.colors.accent.upper(),
        theme.colors.background.upper(),
        theme.colors.text.upper(),
        theme.colors.text_light.upper(),
    }


def _expected_size(elem: TextElement, theme: ThemeConfig) -> int | None:
    """Return the theme-expected font size for an element role, or None if unconstrained."""
    role = elem.role
    if role == "title":
        return theme.fonts.heading_size   # title_size is for cover; heading for content
    if role == "subtitle":
        return theme.fonts.heading_size
    if role in ("body",):
        return theme.fonts.body_size
    if role == "caption":
        return theme.fonts.caption_size
    return None


def check_theme_consistency(
    slide: SlideSchema,
    theme: ThemeConfig,
) -> list[ReviewIssue]:
    """Detect text elements that deviate from the theme's font and colour rules."""
    issues: list[ReviewIssue] = []
    seq = 0
    palette = _theme_palette(theme)

    for elem in slide.text_elements:
        style = elem.style
        role = elem.role

        # ── colour not in theme palette ───────────────────────────────────────
        if style.color and style.color.upper() not in palette:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_theme_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="theme_consistency",
                check_category="theme",
                severity="low",
                message=(
                    f"'{elem.element_id}' uses color {style.color} which is not in "
                    f"the theme palette "
                    f"({', '.join(sorted(palette))})."
                ),
                suggested_fix=(
                    "Use one of the theme colors or set 'color' to null "
                    "to inherit the theme default."
                ),
                auto_fixable=False,
            ))

        # ── font size significantly different from theme expectation ──────────
        expected = _expected_size(elem, theme)
        if expected is not None:
            diff = abs(style.font_size - expected)
            if diff > _FONT_SIZE_TOLERANCE:
                seq += 1
                sev: Severity = "medium" if diff > 10 else "low"
                issues.append(ReviewIssue(
                    issue_id=f"{slide.slide_id}_theme_{seq:03d}",
                    slide_id=slide.slide_id,
                    element_id=elem.element_id,
                    issue_type="theme_consistency",
                    check_category="theme",
                    severity=sev,
                    message=(
                        f"'{elem.element_id}' (role: {role}) uses {style.font_size}pt; "
                        f"theme expects ~{expected}pt "
                        f"(difference: {diff}pt)."
                    ),
                    suggested_fix=(
                        f"Change font_size to {expected}pt, "
                        f"or update the theme if this is intentional."
                    ),
                    auto_fixable=True,
                ))

        # ── font hierarchy inversion (body larger than title on same slide) ───
        # This is checked at slide level below

    # ── per-slide hierarchy check ─────────────────────────────────────────────
    title_elems = [e for e in slide.text_elements if e.role == "title"]
    body_elems = [e for e in slide.text_elements if e.role == "body"]
    if title_elems and body_elems:
        title_fs = min(e.style.font_size for e in title_elems)
        body_fs = max(e.style.font_size for e in body_elems)
        if body_fs >= title_fs:
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_theme_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=None,
                issue_type="theme_consistency",
                check_category="theme",
                severity="medium",
                message=(
                    f"Font hierarchy inverted on slide '{slide.slide_id}': "
                    f"body text ({body_fs}pt) ≥ title text ({title_fs}pt). "
                    f"Titles should always be larger than body text."
                ),
                suggested_fix=(
                    "Increase the title font size or decrease the body font size."
                ),
                auto_fixable=False,
            ))

    return issues
