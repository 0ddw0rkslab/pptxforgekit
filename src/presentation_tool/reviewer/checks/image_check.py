from __future__ import annotations

import logging
from pathlib import Path

from presentation_tool.models.review import ReviewIssue, Severity
from presentation_tool.models.schema import ImageElement, SlideSchema

logger = logging.getLogger(__name__)

# Effective DPI thresholds (pixels per inch at the displayed size)
_DPI_CRITICAL = 72    # below this: barely usable
_DPI_HIGH     = 96    # below this: visible pixellation on screen
_DPI_MEDIUM   = 150   # below this: poor quality when printed / PDF-exported

_CM_PER_INCH = 2.54


def _effective_dpi(px_width: int, display_width_cm: float) -> float:
    if display_width_cm <= 0:
        return 0.0
    display_width_in = display_width_cm / _CM_PER_INCH
    return px_width / display_width_in


def _severity_for_dpi(dpi: float) -> Severity | None:
    if dpi < _DPI_CRITICAL:
        return "critical"
    if dpi < _DPI_HIGH:
        return "high"
    if dpi < _DPI_MEDIUM:
        return "medium"
    return None   # acceptable


def check_image_resolution(
    slide: SlideSchema,
    base_path: Path | None = None,
) -> list[ReviewIssue]:
    """Check image file existence and effective display resolution."""
    issues: list[ReviewIssue] = []
    seq = 0

    for elem in slide.image_elements:
        img_path = _resolve(elem.file_path, base_path)

        # ── file existence ────────────────────────────────────────────────────
        if not img_path.exists():
            seq += 1
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_imgres_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="image_not_found",
                check_category="image",
                severity="critical",
                message=(
                    f"Image file not found: '{elem.file_path}'. "
                    f"The slide will show a broken placeholder."
                ),
                suggested_fix=(
                    "Verify the file path relative to the schema file, "
                    "or provide an absolute path."
                ),
                auto_fixable=False,
            ))
            continue

        # ── pixel dimensions ──────────────────────────────────────────────────
        try:
            from PIL import Image as PILImage
            with PILImage.open(img_path) as img:
                px_w, px_h = img.size
        except Exception as exc:
            seq += 1
            logger.debug("Cannot open image '%s': %s", img_path, exc)
            issues.append(ReviewIssue(
                issue_id=f"{slide.slide_id}_imgres_{seq:03d}",
                slide_id=slide.slide_id,
                element_id=elem.element_id,
                issue_type="image_resolution",
                check_category="image",
                severity="high",
                message=(
                    f"Cannot read image '{elem.file_path}': {exc}. "
                    f"Verify the file is a valid image."
                ),
                suggested_fix="Replace with a valid PNG, JPEG, or GIF file.",
                auto_fixable=False,
            ))
            continue

        # ── DPI check ─────────────────────────────────────────────────────────
        dpi = _effective_dpi(px_w, elem.position.w)
        severity = _severity_for_dpi(dpi)
        if severity is None:
            continue   # resolution is acceptable

        seq += 1
        needed_px = int((elem.position.w / _CM_PER_INCH) * _DPI_MEDIUM)
        issues.append(ReviewIssue(
            issue_id=f"{slide.slide_id}_imgres_{seq:03d}",
            slide_id=slide.slide_id,
            element_id=elem.element_id,
            issue_type="image_resolution",
            check_category="image",
            severity=severity,
            message=(
                f"'{elem.element_id}' has low effective resolution: "
                f"{dpi:.0f} DPI ({px_w}×{px_h}px displayed at "
                f"{elem.position.w:.1f}×{elem.position.h:.1f} cm). "
                f"Minimum recommended: {_DPI_MEDIUM} DPI."
            ),
            suggested_fix=(
                f"Replace with a higher-resolution image "
                f"(at least {needed_px}px wide for this display size)."
            ),
            auto_fixable=False,
        ))

    return issues


def _resolve(file_path: str, base_path: Path | None) -> Path:
    p = Path(file_path)
    if p.is_absolute():
        return p
    if base_path:
        candidate = base_path / p
        if candidate.exists():
            return candidate
    return p
