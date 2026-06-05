from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptxforgekit.exceptions import ExportError
from pptxforgekit.exporter.export import Exporter
from pptxforgekit.models.review import ReviewReport
from pptxforgekit.models.schema import PresentationMeta, PresentationSchema, SlideSchema


@pytest.fixture
def exporter() -> Exporter:
    return Exporter()


@pytest.fixture
def simple_schema() -> PresentationSchema:
    slide = SlideSchema(slide_id="s001", title="Hello", layout_type="cover")
    return PresentationSchema(
        presentation=PresentationMeta(title="Test Deck", total_slides=1),
        slides=[slide],
    )


@pytest.fixture
def simple_report() -> ReviewReport:
    return ReviewReport(
        pptx_file="test.pptx",
        schema_file="test.json",
        reviewed_at="2026-01-01T00:00:00Z",
        issues=[],
    )


class TestExportSchema:
    def test_writes_json_file(
        self, exporter: Exporter, simple_schema: PresentationSchema, tmp_path: Path
    ) -> None:
        out = tmp_path / "schema.json"
        exporter.export_schema(simple_schema, out)
        assert out.exists()

    def test_json_is_valid(
        self, exporter: Exporter, simple_schema: PresentationSchema, tmp_path: Path
    ) -> None:
        out = tmp_path / "schema.json"
        exporter.export_schema(simple_schema, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["presentation"]["title"] == "Test Deck"
        assert data["presentation"]["total_slides"] == 1

    def test_creates_parent_dirs(
        self, exporter: Exporter, simple_schema: PresentationSchema, tmp_path: Path
    ) -> None:
        out = tmp_path / "subdir" / "deep" / "schema.json"
        exporter.export_schema(simple_schema, out)
        assert out.exists()

    def test_roundtrip(
        self, exporter: Exporter, simple_schema: PresentationSchema, tmp_path: Path
    ) -> None:
        out = tmp_path / "schema.json"
        exporter.export_schema(simple_schema, out)
        loaded = PresentationSchema.from_file(out)
        assert loaded.slides[0].slide_id == "s001"


class TestExportReview:
    def test_writes_json(
        self, exporter: Exporter, simple_report: ReviewReport, tmp_path: Path
    ) -> None:
        out = tmp_path / "report.json"
        exporter.export_review(simple_report, json_path=out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["pptx_file"] == "test.pptx"

    def test_writes_markdown(
        self, exporter: Exporter, simple_report: ReviewReport, tmp_path: Path
    ) -> None:
        out = tmp_path / "report.md"
        exporter.export_review(simple_report, md_path=out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Review Report" in content

    def test_writes_both_formats(
        self, exporter: Exporter, simple_report: ReviewReport, tmp_path: Path
    ) -> None:
        json_out = tmp_path / "r.json"
        md_out = tmp_path / "r.md"
        exporter.export_review(simple_report, json_path=json_out, md_path=md_out)
        assert json_out.exists()
        assert md_out.exists()

    def test_no_output_paths_is_noop(
        self, exporter: Exporter, simple_report: ReviewReport
    ) -> None:
        exporter.export_review(simple_report)  # should not raise


class TestCopyPptx:
    def test_copies_file(self, exporter: Exporter, tmp_path: Path) -> None:
        src = tmp_path / "src.pptx"
        src.write_bytes(b"PK fake pptx")
        dest = tmp_path / "out" / "dest.pptx"
        exporter.copy_pptx(src, dest)
        assert dest.exists()
        assert dest.read_bytes() == b"PK fake pptx"

    def test_missing_source_raises(self, exporter: Exporter, tmp_path: Path) -> None:
        with pytest.raises(ExportError, match="not found"):
            exporter.copy_pptx(tmp_path / "missing.pptx", tmp_path / "dest.pptx")

    def test_same_src_dest_is_noop(self, exporter: Exporter, tmp_path: Path) -> None:
        src = tmp_path / "file.pptx"
        src.write_bytes(b"data")
        exporter.copy_pptx(src, src)  # should not raise or corrupt
        assert src.read_bytes() == b"data"
