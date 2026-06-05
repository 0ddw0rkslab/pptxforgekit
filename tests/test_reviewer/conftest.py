from __future__ import annotations

from pathlib import Path

import pytest

from pptxforgekit.models.schema import (
    ChartElement,
    Position,
    SlideSchema,
    TextElement,
    TextStyle,
    ValidationMetadata,
)
from pptxforgekit.models.theme import ThemeConfig

FIXTURES = Path(__file__).parents[1] / "fixtures"
DATA_DIR = FIXTURES / "data"


def _pos(x=2.0, y=0.5, w=20.0, h=5.0) -> Position:
    return Position(x=x, y=y, w=w, h=h)


def _slide(slide_id: str = "s001", **kwargs) -> SlideSchema:
    return SlideSchema(
        slide_id=slide_id,
        title="Test Slide",
        layout_type="title_content",
        validation_metadata=ValidationMetadata(
            created_at="2026-06-04T00:00:00Z",
            last_modified="2026-06-04T00:00:00Z",
        ),
        **kwargs,
    )


def _text(
    eid: str = "t1",
    content: str = "Hello world",
    role: str = "body",
    font_size: int = 20,
    pos: Position | None = None,
    color: str | None = None,
) -> TextElement:
    return TextElement(
        element_id=eid,
        role=role,
        content=content,
        position=pos or _pos(),
        style=TextStyle(font_size=font_size, color=color),
    )


def _chart(
    eid: str = "c1",
    chart_type: str = "bar",
    y_columns: list | None = None,
    title: str = "Chart",
    pos: Position | None = None,
    **kw,
) -> ChartElement:
    return ChartElement(
        element_id=eid,
        chart_type=chart_type,
        data_inline=[{"cat": "A", "val": 1.0}, {"cat": "B", "val": 2.0}],
        x_column="cat",
        y_columns=y_columns or ["val"],
        title=title,
        position=pos or _pos(w=20.0, h=10.0),
        **kw,
    )


@pytest.fixture
def default_theme() -> ThemeConfig:
    return ThemeConfig()
