from __future__ import annotations

from pydantic import BaseModel, Field


class SlideOutline(BaseModel):
    slide_id: str
    section: str
    title: str
    key_message: str
    suggested_layout: str  # cover | title_only | title_content | two_column | title_chart | title_table | blank
    content_hints: list[str] = Field(default_factory=list)
    data_refs: list[str] = Field(default_factory=list)


class StorylineOutline(BaseModel):
    presentation_type: str
    title: str
    total_slides: int
    slides: list[SlideOutline] = Field(default_factory=list)
