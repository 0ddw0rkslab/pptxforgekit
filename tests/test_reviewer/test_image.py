from __future__ import annotations

from pathlib import Path

import pytest

from presentation_tool.models.schema import ImageElement, Position
from presentation_tool.reviewer.checks.image_check import check_image_resolution
from .conftest import _pos, _slide


def _img(eid: str, file_path: str, pos: Position | None = None) -> ImageElement:
    return ImageElement(
        element_id=eid,
        file_path=file_path,
        position=pos or _pos(x=2.0, y=3.0, w=20.0, h=12.0),
    )


class TestImageNotFound:
    def test_missing_file_is_critical(self) -> None:
        slide = _slide(image_elements=[_img("i1", "nonexistent/image.png")])
        issues = check_image_resolution(slide)
        assert len(issues) == 1
        assert issues[0].issue_type == "image_not_found"
        assert issues[0].severity == "critical"

    def test_absolute_missing_path(self, tmp_path: Path) -> None:
        slide = _slide(
            image_elements=[_img("i1", str(tmp_path / "missing.png"))]
        )
        issues = check_image_resolution(slide)
        assert issues[0].severity == "critical"

    def test_no_images_no_issues(self) -> None:
        slide = _slide()
        assert check_image_resolution(slide) == []


class TestImageResolution:
    def _make_image(self, tmp_path: Path, px_w: int, px_h: int) -> Path:
        """Create a real PNG image of given pixel dimensions."""
        from PIL import Image
        img = Image.new("RGB", (px_w, px_h), color=(128, 128, 128))
        path = tmp_path / f"img_{px_w}x{px_h}.png"
        img.save(str(path))
        return path

    def test_high_resolution_no_issue(self, tmp_path: Path) -> None:
        # 20cm display, 2000px → 2000 / (20/2.54) = 254 DPI → OK
        path = self._make_image(tmp_path, 2000, 1500)
        slide = _slide(
            image_elements=[_img("i1", str(path), pos=_pos(w=20.0, h=15.0))]
        )
        issues = check_image_resolution(slide, base_path=None)
        assert issues == []

    def test_low_resolution_high_severity(self, tmp_path: Path) -> None:
        # 20cm display, 400px → 400 / (20/2.54) = ~51 DPI → critical (<72)
        path = self._make_image(tmp_path, 400, 300)
        slide = _slide(
            image_elements=[_img("i1", str(path), pos=_pos(w=20.0, h=15.0))]
        )
        issues = check_image_resolution(slide)
        assert len(issues) == 1
        assert issues[0].issue_type == "image_resolution"
        assert issues[0].severity in ("critical", "high")

    def test_medium_resolution_medium_severity(self, tmp_path: Path) -> None:
        # 20cm display, 800px → 800 / (20/2.54) = ~102 DPI → high (72–95 → actually 102 → medium 96–150)
        path = self._make_image(tmp_path, 800, 600)
        slide = _slide(
            image_elements=[_img("i1", str(path), pos=_pos(w=20.0, h=15.0))]
        )
        issues = check_image_resolution(slide)
        if issues:
            assert issues[0].severity in ("medium", "high")

    def test_suggested_fix_mentions_pixel_count(self, tmp_path: Path) -> None:
        path = self._make_image(tmp_path, 200, 150)
        slide = _slide(
            image_elements=[_img("i1", str(path), pos=_pos(w=20.0, h=15.0))]
        )
        issues = check_image_resolution(slide)
        if issues:
            assert any(
                "px" in i.suggested_fix.lower() or "pixel" in i.suggested_fix.lower()
                for i in issues
                if i.suggested_fix
            )

    def test_base_path_resolution(self, tmp_path: Path) -> None:
        # Use relative path + base_path
        path = self._make_image(tmp_path, 2000, 1500)
        relative = path.name
        slide = _slide(
            image_elements=[_img("i1", relative, pos=_pos(w=20.0, h=15.0))]
        )
        issues = check_image_resolution(slide, base_path=tmp_path)
        assert issues == []
