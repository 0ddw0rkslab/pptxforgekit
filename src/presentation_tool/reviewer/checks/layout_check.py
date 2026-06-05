from __future__ import annotations

from presentation_tool.models.review import ReviewIssue, Severity
from presentation_tool.models.schema import Position, SlideSchema

# Overlap fraction thresholds (area of overlap / area of smaller element)
_OVERLAP_SKIP   = 0.02   # < 2%  → ignore (rounding artefacts / intentional adjacency)
_OVERLAP_LOW    = 0.10   # 2–10% → low
_OVERLAP_MEDIUM = 0.30   # 10–30%→ medium
# ≥ 30%             → high

_SLIDE_W = 33.87
_SLIDE_H = 19.05


# ── geometry helpers ──────────────────────────────────────────────────────────

def _overlap_area(a: Position, b: Position) -> float:
    dx = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    dy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    return max(0.0, dx) * max(0.0, dy)


def _overlap_fraction(a: Position, b: Position) -> float:
    area = _overlap_area(a, b)
    if area == 0.0:
        return 0.0
    smaller = min(a.w * a.h, b.w * b.h)
    return area / smaller if smaller > 0 else 0.0


def _clipping_excesses(p: Position) -> dict[str, float]:
    return {
        "excess_left_cm":   round(max(0.0, -p.x), 3),
        "excess_top_cm":    round(max(0.0, -p.y), 3),
        "excess_right_cm":  round(max(0.0, p.x + p.w - _SLIDE_W), 3),
        "excess_bottom_cm": round(max(0.0, p.y + p.h - _SLIDE_H), 3),
    }


# ── public check functions ────────────────────────────────────────────────────

def check_overlap(slide: SlideSchema) -> list[ReviewIssue]:
    """Detect elements that significantly overlap each other."""
    issues: list[ReviewIssue] = []
    seq = 0

    elements: list[tuple[str, Position]] = [
        (e.element_id, e.position)
        for lst in (
            slide.text_elements,
            slide.chart_elements,
            slide.image_elements,
            slide.table_elements,
        )
        for e in lst
    ]

    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            id_a, pos_a = elements[i]
            id_b, pos_b = elements[j]
            frac = _overlap_fraction(pos_a, pos_b)
            if frac < _OVERLAP_SKIP:
                continue

            severity: Severity = (
                "high"   if frac >= _OVERLAP_MEDIUM
                else "medium" if frac >= _OVERLAP_LOW
                else "low"
            )
            area_cm2 = round(_overlap_area(pos_a, pos_b), 2)
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_overlap_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=id_a,
                issue_type="element_overlap",
                check_category="layout",
                severity=severity,
                message=(
                    f"'{id_a}' and '{id_b}' overlap by {frac * 100:.0f}% of "
                    f"the smaller element's area ({area_cm2} cm²)."
                ),
                suggested_fix="Reposition or resize one of the elements to eliminate overlap.",
                auto_fixable=True,
                context={
                    "secondary_element_id": id_b,
                    "overlap_fraction": round(frac, 4),
                    "overlap_area_cm2": area_cm2,
                },
            ))

    return issues


def check_clipping(slide: SlideSchema) -> list[ReviewIssue]:
    """Detect elements that extend outside the slide boundary."""
    issues: list[ReviewIssue] = []
    seq = 0

    elements: list[tuple[str, Position]] = [
        (e.element_id, e.position)
        for lst in (
            slide.text_elements,
            slide.chart_elements,
            slide.image_elements,
            slide.table_elements,
        )
        for e in lst
    ]

    for elem_id, pos in elements:
        excesses = _clipping_excesses(pos)
        if not any(v > 0 for v in excesses.values()):
            continue

        max_excess = max(excesses.values())
        severity: Severity = (
            "critical" if max_excess > 2.0
            else "high" if max_excess > 0.5
            else "medium"
        )
        detail_parts = []
        if excesses["excess_left_cm"]:
            detail_parts.append(f"left {excesses['excess_left_cm']:.2f} cm")
        if excesses["excess_top_cm"]:
            detail_parts.append(f"top {excesses['excess_top_cm']:.2f} cm")
        if excesses["excess_right_cm"]:
            detail_parts.append(f"right {excesses['excess_right_cm']:.2f} cm")
        if excesses["excess_bottom_cm"]:
            detail_parts.append(f"bottom {excesses['excess_bottom_cm']:.2f} cm")

        seq += 1
        issues.append(ReviewIssue(
            issue_id=f"{slide.slide_id}_clipping_{seq:03d}",
            slide_id=slide.slide_id,
            element_id=elem_id,
            issue_type="element_clipping",
            check_category="layout",
            severity=severity,
            message=(
                f"Element '{elem_id}' is clipped: "
                + ", ".join(detail_parts)
                + f". Worst excess: {max_excess:.2f} cm."
            ),
            suggested_fix="Reduce the element's size or move it inside the slide boundary.",
            auto_fixable=True,
            context=excesses,
        ))

    return issues
