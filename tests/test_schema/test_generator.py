from __future__ import annotations

import json
from pathlib import Path

from pptxforgekit.models.analysis import AnalysisResult
from pptxforgekit.models.outline import StorylineOutline
from pptxforgekit.models.schema import CURRENT_SCHEMA_VERSION, PresentationSchema
from pptxforgekit.models.theme import ThemeConfig
from pptxforgekit.schema.generator import RuleBasedSchemaGenerator


class TestRuleBasedSchemaGenerator:
    def test_generates_schema(
        self, sample_outline: StorylineOutline, sample_theme: ThemeConfig
    ) -> None:
        schema = RuleBasedSchemaGenerator().generate(sample_outline, sample_theme)
        assert isinstance(schema, PresentationSchema)
        assert len(schema.slides) == sample_outline.total_slides
        assert schema.schema_version == CURRENT_SCHEMA_VERSION

    def test_first_slide_is_cover(
        self, sample_outline: StorylineOutline, sample_theme: ThemeConfig
    ) -> None:
        schema = RuleBasedSchemaGenerator().generate(sample_outline, sample_theme)
        cover = schema.slides[0]
        assert cover.layout_type == "cover"
        assert cover.section == "cover"

    def test_cover_has_title_element(
        self, sample_outline: StorylineOutline, sample_theme: ThemeConfig
    ) -> None:
        schema = RuleBasedSchemaGenerator().generate(sample_outline, sample_theme)
        cover = schema.slides[0]
        titles = [e for e in cover.text_elements if e.role == "title"]
        assert len(titles) == 1
        assert titles[0].content == sample_outline.title

    def test_title_element_position_within_slide(
        self, sample_outline: StorylineOutline, sample_theme: ThemeConfig
    ) -> None:
        schema = RuleBasedSchemaGenerator().generate(sample_outline, sample_theme)
        for slide in schema.slides:
            for elem in slide.text_elements:
                p = elem.position
                assert p.x + p.w <= 34.5, f"Element '{elem.element_id}' too wide"
                assert p.y + p.h <= 20.0, f"Element '{elem.element_id}' too tall"

    def test_schema_json_roundtrip(
        self, sample_outline: StorylineOutline, sample_theme: ThemeConfig, tmp_path: Path
    ) -> None:
        schema = RuleBasedSchemaGenerator().generate(sample_outline, sample_theme)
        out = tmp_path / "slides.json"
        schema.write(out)
        loaded = PresentationSchema.from_file(out)
        assert loaded.presentation.title == schema.presentation.title
        assert len(loaded.slides) == len(schema.slides)

    def test_data_slide_has_chart_element(
        self, sample_analysis: AnalysisResult, sample_theme: ThemeConfig
    ) -> None:
        from pptxforgekit.planner.storyline import RuleBasedStorylinePlanner
        outline = RuleBasedStorylinePlanner().plan(sample_analysis, "research")
        schema = RuleBasedSchemaGenerator().generate(outline, sample_theme)
        chart_slides = [s for s in schema.slides if s.chart_elements]
        assert len(chart_slides) >= 1
