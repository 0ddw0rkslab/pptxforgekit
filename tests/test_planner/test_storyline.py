from __future__ import annotations

import pytest

from pptxforgekit.exceptions import PlanningError
from pptxforgekit.models.analysis import AnalysisResult, DataFileRef, Section
from pptxforgekit.models.outline import StorylineOutline
from pptxforgekit.planner.storyline import RuleBasedStorylinePlanner


@pytest.fixture
def planner() -> RuleBasedStorylinePlanner:
    return RuleBasedStorylinePlanner()


@pytest.fixture
def minimal_analysis() -> AnalysisResult:
    return AnalysisResult(
        source_files=["paper.md"],
        title="Test Paper",
        abstract="An abstract.",
        key_messages=["Finding A", "Finding B"],
        sections=[
            Section(heading="Introduction", paragraphs=["Background here."]),
            Section(heading="Methods", paragraphs=["We did X."]),
            Section(heading="Conclusion", paragraphs=["We conclude Y."]),
        ],
        conclusions=["We conclude Y."],
    )


@pytest.fixture
def analysis_with_data(minimal_analysis: AnalysisResult) -> AnalysisResult:
    minimal_analysis.data_files = [
        DataFileRef(
            file_path="results.csv",
            columns=["method", "accuracy"],
            row_count=3,
        )
    ]
    return minimal_analysis


@pytest.fixture
def analysis_with_multi_data(minimal_analysis: AnalysisResult) -> AnalysisResult:
    minimal_analysis.data_files = [
        DataFileRef(file_path="exp1.csv", columns=["x", "y"], row_count=5),
        DataFileRef(file_path="exp2.csv", columns=["a", "b"], row_count=4),
    ]
    return minimal_analysis


class TestRuleBasedStorylinePlanner:
    def test_plan_research_returns_outline(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        assert isinstance(outline, StorylineOutline)
        assert outline.presentation_type == "research"

    def test_plan_research_title_matches(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        assert outline.title == "Test Paper"

    def test_plan_research_slide_count_matches(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        assert outline.total_slides == len(outline.slides)

    def test_plan_research_slide_ids_unique(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        ids = [s.slide_id for s in outline.slides]
        assert len(ids) == len(set(ids))

    def test_plan_research_slide_ids_sequential(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        for i, slide in enumerate(outline.slides, start=1):
            assert slide.slide_id == f"s{i:03d}"

    def test_plan_research_cover_slide_first(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        first = outline.slides[0]
        assert first.section == "cover"
        assert first.suggested_layout == "cover"

    def test_plan_research_qa_slide_last(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        last = outline.slides[-1]
        assert last.section == "qa"

    def test_plan_with_data_files_includes_results_slide(
        self, planner: RuleBasedStorylinePlanner, analysis_with_data: AnalysisResult
    ) -> None:
        outline = planner.plan(analysis_with_data, "research")
        sections = [s.section for s in outline.slides]
        assert "results" in sections

    def test_plan_results_slide_has_data_ref(
        self, planner: RuleBasedStorylinePlanner, analysis_with_data: AnalysisResult
    ) -> None:
        outline = planner.plan(analysis_with_data, "research")
        results_slides = [s for s in outline.slides if s.section == "results"]
        assert any(len(s.data_refs) > 0 for s in results_slides)

    def test_plan_multiple_data_files_creates_extra_results_slides(
        self, planner: RuleBasedStorylinePlanner, analysis_with_multi_data: AnalysisResult
    ) -> None:
        outline = planner.plan(analysis_with_multi_data, "research")
        results_slides = [s for s in outline.slides if s.section == "results"]
        assert len(results_slides) == 2

    def test_plan_no_data_files_skips_results_slide(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        outline = planner.plan(minimal_analysis, "research")
        sections = [s.section for s in outline.slides]
        assert "results" not in sections

    def test_plan_unsupported_type_raises(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        with pytest.raises(PlanningError, match="Unsupported"):
            planner.plan(minimal_analysis, "business")

    def test_plan_all_slides_have_valid_layout(
        self, planner: RuleBasedStorylinePlanner, minimal_analysis: AnalysisResult
    ) -> None:
        valid_layouts = {
            "cover", "title_only", "title_content", "two_column",
            "title_chart", "title_table", "title_image", "blank",
        }
        outline = planner.plan(minimal_analysis, "research")
        for slide in outline.slides:
            assert slide.suggested_layout in valid_layouts, (
                f"Slide {slide.slide_id} has unknown layout: {slide.suggested_layout}"
            )
