from __future__ import annotations

import logging
from typing import cast

from pydantic import BaseModel, Field

from pptxforgekit.exceptions import PlanningError
from pptxforgekit.interfaces.planner import IStorylinePlanner
from pptxforgekit.llm.prompts import PLANNER_SYSTEM, PLANNER_USER_TEMPLATE
from pptxforgekit.llm.provider import LLMProvider
from pptxforgekit.models.analysis import AnalysisResult
from pptxforgekit.models.outline import SlideOutline, StorylineOutline

logger = logging.getLogger(__name__)

_VALID_LAYOUTS = {
    "cover", "title_only", "title_content", "two_column",
    "title_chart", "title_table", "title_image", "blank",
}


class _LLMSlide(BaseModel):
    slide_id: str
    section: str = ""
    title: str
    key_message: str = ""
    suggested_layout: str = "title_content"
    content_hints: list[str] = Field(default_factory=list)
    data_refs: list[str] = Field(default_factory=list)


class _LLMOutlineOutput(BaseModel):
    presentation_type: str = "research"
    title: str = ""
    total_slides: int = 0
    slides: list[_LLMSlide] = Field(default_factory=list)


class LLMStorylinePlanner(IStorylinePlanner):
    """LLM-powered storyline planner.

    Uses the LLM to decide the narrative arc and slide structure,
    going beyond the fixed research template used by the rule-based planner.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def plan(self, analysis: AnalysisResult, presentation_type: str) -> StorylineOutline:
        if presentation_type != "research":
            raise PlanningError(
                f"LLMStorylinePlanner currently supports 'research' type only. "
                f"Got: '{presentation_type}'"
            )

        analysis_json = analysis.model_dump_json(indent=2)
        user_prompt = PLANNER_USER_TEMPLATE.format(analysis_json=analysis_json)

        logger.info(
            "[LLMStorylinePlanner] calling %s/%s",
            self._provider.provider_name,
            self._provider.model,
        )

        llm_out = cast(_LLMOutlineOutput, self._provider.complete_json(
            user_prompt=user_prompt,
            system_prompt=PLANNER_SYSTEM,
            model_class=_LLMOutlineOutput,
        ))

        slides = self._coerce_slides(llm_out.slides)

        return StorylineOutline(
            presentation_type="research",
            title=llm_out.title or analysis.title,
            total_slides=len(slides),
            slides=slides,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _coerce_slides(self, raw: list[_LLMSlide]) -> list[SlideOutline]:
        """Normalise LLM output: fix IDs, validate layouts, cap hints."""
        slides: list[SlideOutline] = []
        for i, s in enumerate(raw, start=1):
            layout = s.suggested_layout if s.suggested_layout in _VALID_LAYOUTS else "title_content"
            slides.append(SlideOutline(
                slide_id=f"s{i:03d}",  # always sequential regardless of LLM output
                section=s.section or "content",
                title=s.title,
                key_message=s.key_message[:200],
                suggested_layout=layout,
                content_hints=s.content_hints[:6],
                data_refs=s.data_refs,
            ))
        return slides
