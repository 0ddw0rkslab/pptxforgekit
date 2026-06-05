from __future__ import annotations

import logging
from pathlib import Path

from presentation_tool.exceptions import AssetError

logger = logging.getLogger(__name__)

_MIN_RESOLUTION = 72   # dpi equivalent (px per inch)
_MIN_SHORT_SIDE = 200  # pixels


class AssetManager:
    def validate_image(self, path: Path) -> dict[str, object]:
        """Return metadata dict; raises AssetError if the image is unusable."""
        if not path.exists():
            raise AssetError(f"Image not found: {path}")

        try:
            from PIL import Image
            with Image.open(path) as img:
                width, height = img.size
                fmt = img.format or "UNKNOWN"
                mode = img.mode
        except Exception as exc:
            raise AssetError(f"Cannot open image {path}: {exc}") from exc

        issues: list[str] = []
        if min(width, height) < _MIN_SHORT_SIDE:
            issues.append(
                f"Image resolution too low ({width}x{height}px). "
                f"Minimum short side: {_MIN_SHORT_SIDE}px"
            )

        if issues:
            logger.warning("Image validation issues for %s: %s", path, "; ".join(issues))

        return {
            "path": str(path),
            "width": width,
            "height": height,
            "format": fmt,
            "mode": mode,
            "issues": issues,
        }

    def compute_fit_dimensions(
        self,
        img_w: int,
        img_h: int,
        box_w: float,
        box_h: float,
        mode: str = "fit",
    ) -> tuple[float, float]:
        """Return (w, h) in cm that fits img into box while respecting mode."""
        if img_w == 0 or img_h == 0:
            return box_w, box_h

        img_ratio = img_w / img_h
        box_ratio = box_w / box_h

        if mode == "fit":
            if img_ratio > box_ratio:
                return box_w, box_w / img_ratio
            return box_h * img_ratio, box_h
        if mode == "fill":
            if img_ratio > box_ratio:
                return box_h * img_ratio, box_h
            return box_w, box_w / img_ratio
        # "crop" — same as fill, cropping is handled by the renderer
        return box_w, box_h
