from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pptxforgekit.models.schema import (
    CURRENT_SCHEMA_VERSION,
    ChartElement,
    Position,
    PresentationMeta,
    PresentationSchema,
    SlideSchema,
    TableElement,
    TextElement,
    TextStyle,
    ValidationMetadata,
)

# ─────────────────────────────── helpers ─────────────────────────────────────

VALID_POS = Position(x=2.0, y=0.5, w=10.0, h=3.0)


def _make_text(eid: str = "t1", content: str = "Hello") -> TextElement:
    return TextElement(
        element_id=eid,
        role="body",
        content=content,
        position=VALID_POS,
    )


def _make_chart(eid: str = "c1") -> ChartElement:
    return ChartElement(
        element_id=eid,
        chart_type="bar",
        data_source="",
        position=VALID_POS,
        data_inline=[{"label": "A", "value": 1.0}],
    )


def _make_slide(slide_id: str = "s001", **kwargs) -> SlideSchema:
    defaults = dict(
        slide_id=slide_id,
        title="Test Slide",
        layout_type="title_content",
        validation_metadata=ValidationMetadata(
            created_at="2026-06-04T00:00:00Z",
            last_modified="2026-06-04T00:00:00Z",
        ),
    )
    defaults.update(kwargs)
    return SlideSchema(**defaults)


def _make_presentation(slides: list[SlideSchema]) -> PresentationSchema:
    return PresentationSchema(
        presentation=PresentationMeta(
            title="Test",
            total_slides=len(slides),
            generated_at="2026-06-04T00:00:00Z",
        ),
        slides=slides,
    )


# ─────────────────────────────── Position ────────────────────────────────────


class TestPosition:
    def test_valid(self) -> None:
        p = Position(x=0.0, y=0.5, w=10.0, h=3.0)
        assert p.w == 10.0

    def test_negative_x_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Position(x=-1.0, y=0.0, w=5.0, h=2.0)

    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            Position(x=0.0, y=0.0, w=0.0, h=2.0)

    def test_zero_height_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            Position(x=0.0, y=0.0, w=5.0, h=0.0)

    def test_negative_height_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            Position(x=0.0, y=0.0, w=5.0, h=-1.0)


# ───────────────────────────── TextStyle ─────────────────────────────────────


class TestTextStyle:
    def test_valid_color(self) -> None:
        s = TextStyle(color="#1F3864")
        assert s.color == "#1F3864"

    def test_color_normalised_to_upper(self) -> None:
        s = TextStyle(color="#1f3864")
        assert s.color == "#1F3864"

    def test_none_color_allowed(self) -> None:
        s = TextStyle(color=None)
        assert s.color is None

    def test_invalid_hex_raises(self) -> None:
        with pytest.raises(ValidationError, match="not a valid hex color"):
            TextStyle(color="#ZZZZZZ")

    def test_short_hex_raises(self) -> None:
        with pytest.raises(ValidationError, match="not a valid hex color"):
            TextStyle(color="#FFF")

    def test_named_color_raises(self) -> None:
        with pytest.raises(ValidationError, match="not a valid hex color"):
            TextStyle(color="red")

    def test_font_size_min(self) -> None:
        with pytest.raises(ValidationError):
            TextStyle(font_size=5)

    def test_font_size_max(self) -> None:
        with pytest.raises(ValidationError):
            TextStyle(font_size=201)

    def test_valid_align_values(self) -> None:
        for align in ("left", "center", "right", "justify"):
            s = TextStyle(align=align)
            assert s.align == align

    def test_invalid_align_raises(self) -> None:
        with pytest.raises(ValidationError):
            TextStyle(align="middle")  # type: ignore[arg-type]


# ───────────────────────────── ChartElement ──────────────────────────────────


class TestChartElement:
    def test_requires_data_source_or_inline(self) -> None:
        with pytest.raises(ValidationError, match="data_source.*data_inline"):
            ChartElement(
                element_id="c1",
                chart_type="bar",
                data_source="",
                position=VALID_POS,
                data_inline=None,
            )

    def test_data_inline_sufficient(self) -> None:
        c = _make_chart()
        assert c.element_id == "c1"

    def test_data_source_sufficient(self) -> None:
        c = ChartElement(
            element_id="c1",
            chart_type="bar",
            data_source="data.csv",
            position=VALID_POS,
        )
        assert c.data_source == "data.csv"

    def test_x_column_defaults_to_none(self) -> None:
        c = _make_chart()
        assert c.x_column is None

    def test_invalid_chart_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChartElement(
                element_id="c1",
                chart_type="histogram",  # type: ignore[arg-type]
                data_source="data.csv",
                position=VALID_POS,
            )


# ───────────────────────────── TableElement ──────────────────────────────────


class TestTableElement:
    def test_valid_table(self) -> None:
        t = TableElement(
            element_id="t1",
            headers=["A", "B"],
            rows=[["1", "2"], ["3", "4"]],
            position=VALID_POS,
        )
        assert len(t.rows) == 2

    def test_row_length_mismatch_raises(self) -> None:
        with pytest.raises(ValidationError, match="wrong number of cells"):
            TableElement(
                element_id="t1",
                headers=["A", "B"],
                rows=[["1", "2", "3"]],   # 3 cells but 2 headers
                position=VALID_POS,
            )

    def test_column_widths_length_mismatch_raises(self) -> None:
        with pytest.raises(ValidationError, match="column_widths has"):
            TableElement(
                element_id="t1",
                headers=["A", "B"],
                rows=[],
                position=VALID_POS,
                column_widths=[5.0],   # 1 entry but 2 headers
            )

    def test_zero_column_width_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be > 0"):
            TableElement(
                element_id="t1",
                headers=["A", "B"],
                rows=[],
                position=VALID_POS,
                column_widths=[5.0, 0.0],
            )

    def test_empty_headers_raises(self) -> None:
        with pytest.raises(ValidationError):
            TableElement(
                element_id="t1",
                headers=[],
                rows=[],
                position=VALID_POS,
            )


# ─────────────────────────────── SlideSchema ─────────────────────────────────


class TestSlideSchema:
    def test_valid_slide(self) -> None:
        slide = _make_slide()
        assert slide.slide_id == "s001"
        assert slide.validation_metadata.schema_version == CURRENT_SCHEMA_VERSION

    def test_duplicate_element_ids_raises(self) -> None:
        with pytest.raises(ValidationError, match="duplicate element_id"):
            _make_slide(
                text_elements=[_make_text("dup"), _make_text("dup")],
            )

    def test_duplicate_ids_across_element_types(self) -> None:
        with pytest.raises(ValidationError, match="duplicate element_id"):
            _make_slide(
                text_elements=[_make_text("shared_id")],
                chart_elements=[_make_chart("shared_id")],
            )

    def test_unique_ids_ok(self) -> None:
        slide = _make_slide(
            text_elements=[_make_text("t1"), _make_text("t2")],
            chart_elements=[_make_chart("c1")],
        )
        assert len(slide.text_elements) == 2

    def test_invalid_background_color_raises(self) -> None:
        with pytest.raises(ValidationError, match="not a valid hex color"):
            _make_slide(background_color="blue")

    def test_valid_background_color(self) -> None:
        slide = _make_slide(background_color="#F0F4FA")
        assert slide.background_color == "#F0F4FA"

    def test_empty_title_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_slide(title="")

    def test_footer_override_stored(self) -> None:
        slide = _make_slide(footer_override="CONFIDENTIAL")
        assert slide.footer_override == "CONFIDENTIAL"

    def test_slide_number_stored(self) -> None:
        slide = _make_slide(slide_number=3)
        assert slide.slide_number == 3

    def test_validation_metadata_defaults(self) -> None:
        slide = SlideSchema(
            slide_id="s001",
            title="T",
            layout_type="blank",
        )
        assert slide.validation_metadata.status == "draft"
        assert slide.validation_metadata.is_locked is False
        assert slide.validation_metadata.slide_version == 1


# ────────────────────────── PresentationSchema ───────────────────────────────


class TestPresentationSchema:
    def test_total_slides_mismatch_raises(self) -> None:
        slide = _make_slide()
        with pytest.raises(ValidationError, match="total_slides"):
            PresentationSchema(
                presentation=PresentationMeta(
                    title="T",
                    total_slides=99,   # wrong
                    generated_at="2026-06-04T00:00:00Z",
                ),
                slides=[slide],
            )

    def test_duplicate_slide_ids_raises(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate slide_id"):
            _make_presentation([_make_slide("s001"), _make_slide("s001")])

    def test_unique_slide_ids_ok(self) -> None:
        pres = _make_presentation([_make_slide("s001"), _make_slide("s002")])
        assert len(pres.slides) == 2

    def test_empty_slides_ok(self) -> None:
        pres = _make_presentation([])
        assert pres.presentation.total_slides == 0

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        original = _make_presentation([_make_slide("s001")])
        out = tmp_path / "schema.json"
        original.write(out)
        loaded = PresentationSchema.from_file(out)
        assert loaded.presentation.title == original.presentation.title
        assert loaded.slides[0].slide_id == "s001"

    def test_schema_version_in_output(self) -> None:
        pres = _make_presentation([])
        data = json.loads(pres.to_json())
        assert data["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_from_file_error_includes_path(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"schema_version": "1.1", "presentation": {}}', encoding="utf-8")
        with pytest.raises(Exception, match="bad.json"):
            PresentationSchema.from_file(bad)


# ────────────────────────── sample files ─────────────────────────────────────


EXAMPLES_DIR = Path(__file__).parents[2] / "examples" / "schemas"


@pytest.mark.parametrize("filename", [
    "sample_text_slide.json",
    "sample_chart_slide.json",
    "sample_image_slide.json",
])
def test_sample_files_are_valid(filename: str) -> None:
    path = EXAMPLES_DIR / filename
    assert path.exists(), f"Sample file not found: {path}"
    schema = PresentationSchema.from_file(path)
    assert schema.schema_version == CURRENT_SCHEMA_VERSION
    assert len(schema.slides) == schema.presentation.total_slides
    for slide in schema.slides:
        assert slide.slide_id
        assert slide.title
