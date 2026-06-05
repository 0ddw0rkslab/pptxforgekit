from __future__ import annotations

from pathlib import Path

import pytest

from presentation_tool.models.analysis import AnalysisResult, DataFileRef, Section
from presentation_tool.models.outline import SlideOutline, StorylineOutline
from presentation_tool.models.theme import ThemeConfig

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_theme_yaml() -> Path:
    return FIXTURES / "themes" / "default.yaml"


@pytest.fixture
def fixture_md() -> Path:
    return FIXTURES / "docs" / "sample.md"


@pytest.fixture
def fixture_csv() -> Path:
    return FIXTURES / "docs" / "sample.csv"


@pytest.fixture
def fixture_xlsx() -> Path:
    return FIXTURES / "docs" / "sample.xlsx"


@pytest.fixture
def fixture_schema_json() -> Path:
    return FIXTURES / "schemas" / "sample_slides.json"


@pytest.fixture
def sample_theme() -> ThemeConfig:
    return ThemeConfig()


@pytest.fixture
def sample_analysis() -> AnalysisResult:
    return AnalysisResult(
        source_files=["sample.md"],
        title="Sample Research Paper",
        abstract="This is a test abstract.",
        key_messages=["First finding", "Second finding"],
        sections=[
            Section(heading="Introduction", paragraphs=["Background info."]),
            Section(heading="Methods", paragraphs=["We used X approach."]),
            Section(heading="Conclusion", paragraphs=["Main contribution confirmed."]),
        ],
        data_files=[
            DataFileRef(
                file_path="sample.csv",
                columns=["method", "accuracy", "f1_score"],
                row_count=3,
            )
        ],
        conclusions=["Main contribution confirmed."],
    )


@pytest.fixture
def sample_outline(sample_analysis: AnalysisResult) -> StorylineOutline:
    from presentation_tool.planner.storyline import RuleBasedStorylinePlanner
    return RuleBasedStorylinePlanner().plan(sample_analysis, "research")
