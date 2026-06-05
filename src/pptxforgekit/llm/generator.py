from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from pptxforgekit.interfaces.generator import ISlideSchemaGenerator
from pptxforgekit.llm.prompts import GENERATOR_SYSTEM, GENERATOR_USER_TEMPLATE
from pptxforgekit.llm.provider import LLMProvider
from pptxforgekit.models.outline import StorylineOutline
from pptxforgekit.models.schema import (
    CURRENT_SCHEMA_VERSION,
    ChartElement,
    PresentationMeta,
    PresentationSchema,
    SlideSchema,
    TextElement,
    TextStyle,
    ValidationMetadata,
)
from pptxforgekit.models.theme import ThemeConfig
from pptxforgekit.renderer.layout_engine import get_position

logger = logging.getLogger(__name__)


# ── LLM output models ─────────────────────────────────────────────────────────

class _TextBlock(BaseModel):
    role: str = "body"
    content: str = ""


class _ChartBlock(BaseModel):
    chart_type: str = "bar"
    data_source: str = ""
    data_inline: list[dict[str, Any]] | None = None
    x_column: str | None = None
    y_columns: list[str] = Field(default_factory=list)
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    y_unit: str = ""
    bar_direction: str = "vertical"
    stacked: bool = False
    legend_position: str = "right"
    show_data_labels: bool = False
    number_format: str = "General"


class _LLMSlideContent(BaseModel):
    slide_id: str
    title: str = ""
    layout_type: str = "title_content"
    text_blocks: list[_TextBlock] = Field(default_factory=list)
    chart_blocks: list[_ChartBlock] = Field(default_factory=list)
    speaker_note: str = ""


class _LLMGeneratorOutput(BaseModel):
    slides: list[_LLMSlideContent] = Field(default_factory=list)


# ── Implementation ────────────────────────────────────────────────────────────

_VALID_CHART_TYPES = {"bar", "line", "scatter", "pie"}
_VALID_LAYOUTS = {
    "cover", "title_only", "title_content", "two_column",
    "title_chart", "title_table", "title_image", "blank",
}
_VALID_BAR_DIRS = {"vertical", "horizontal"}
_VALID_LEGEND = {"right", "bottom", "top", "left", "none"}


class LLMSchemaGenerator(ISlideSchemaGenerator):
    """LLM-powered slide schema generator.

    The LLM decides content and layout; canonical element positions are
    applied from layout_engine (LLMs are unreliable at exact float coordinates).
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(self, outline: StorylineOutline, theme: ThemeConfig) -> PresentationSchema:
        outline_json = outline.model_dump_json(indent=2)
        user_prompt = GENERATOR_USER_TEMPLATE.format(
            primary_color=theme.colors.primary,
            body_size=theme.fonts.body_size,
            max_bullets=theme.get_rule_value("max_bullets", 6),
            outline_json=outline_json,
        )

        logger.info(
            "[LLMSchemaGenerator] calling %s/%s for %d slides",
            self._provider.provider_name,
            self._provider.model,
            outline.total_slides,
        )

        llm_out: _LLMGeneratorOutput = self._provider.complete_json(
            user_prompt=user_prompt,
            system_prompt=GENERATOR_SYSTEM,
            model_class=_LLMGeneratorOutput,
        )

        now = datetime.now(timezone.utc).isoformat()
        slides = [
            self._build_slide(llm_slide, outline_slide, theme, now, i)
            for i, (llm_slide, outline_slide) in enumerate(
                zip(llm_out.slides, outline.slides), start=1
            )
        ]

        # Pad with rule-based fallback if LLM returned fewer slides
        if len(llm_out.slides) < len(outline.slides):
            from pptxforgekit.schema.generator import RuleBasedSchemaGenerator
            fallback = RuleBasedSchemaGenerator()
            remaining = outline.slides[len(llm_out.slides):]
            for i, outline_slide in enumerate(remaining, start=len(slides) + 1):
                slides.append(fallback._build_slide(outline_slide, theme, now, i))

        return PresentationSchema(
            schema_version=CURRENT_SCHEMA_VERSION,
            presentation=PresentationMeta(
                title=outline.title,
                presentation_type=outline.presentation_type,
                total_slides=len(slides),
                generated_at=now,
            ),
            slides=slides,
        )

    # ── slide builder ─────────────────────────────────────────────────────────

    def _build_slide(
        self,
        llm_slide: _LLMSlideContent,
        outline_slide: Any,
        theme: ThemeConfig,
        now: str,
        slide_number: int,
    ) -> SlideSchema:
        layout = (
            llm_slide.layout_type
            if llm_slide.layout_type in _VALID_LAYOUTS
            else outline_slide.suggested_layout
        )

        text_elements: list[TextElement] = []
        chart_elements: list[ChartElement] = []
        elem_counter = 0

        # ── title ─────────────────────────────────────────────────────────────
        if layout != "blank":
            elem_counter += 1
            title_fs = (
                theme.fonts.title_size if layout == "cover" else theme.fonts.heading_size
            )
            text_elements.append(TextElement(
                element_id=f"{outline_slide.slide_id}_t{elem_counter:02d}",
                role="title" if layout != "cover" else "title",
                content=llm_slide.title or outline_slide.title,
                position=get_position(layout, "title"),
                style=TextStyle(
                    font_size=title_fs,
                    bold=True,
                    color=theme.colors.primary,
                ),
            ))

        # ── text blocks ───────────────────────────────────────────────────────
        role_slot_map = {
            "subtitle": "subtitle",
            "body": "body",
            "body_left": "body_left",
            "body_right": "body_right",
            "caption": "body",
        }
        for block in llm_slide.text_blocks:
            role = block.role
            if not block.content.strip():
                continue
            slot = role_slot_map.get(role, "body")
            # Skip if layout doesn't support this slot
            try:
                pos = get_position(layout, slot)
            except Exception:
                pos = get_position("title_content", "body")

            elem_counter += 1
            is_title_role = role in ("title", "subtitle")
            text_elements.append(TextElement(
                element_id=f"{outline_slide.slide_id}_t{elem_counter:02d}",
                role=role if role in ("title", "subtitle", "body", "caption", "footer", "label") else "body",  # type: ignore[arg-type]
                content=block.content,
                position=pos,
                style=TextStyle(
                    font_size=(
                        theme.fonts.heading_size if is_title_role
                        else theme.fonts.body_size
                    ),
                    color=theme.colors.primary if is_title_role else theme.colors.text,
                ),
            ))

        # ── chart blocks ──────────────────────────────────────────────────────
        for j, cb in enumerate(llm_slide.chart_blocks):
            chart_type = cb.chart_type if cb.chart_type in _VALID_CHART_TYPES else "bar"
            bar_dir = cb.bar_direction if cb.bar_direction in _VALID_BAR_DIRS else "vertical"
            legend = cb.legend_position if cb.legend_position in _VALID_LEGEND else "right"

            # Require at least data_source or data_inline
            if not cb.data_source and not cb.data_inline:
                cb.data_inline = [{"value": 0}]

            chart_elements.append(ChartElement(
                element_id=f"{outline_slide.slide_id}_c{j + 1:02d}",
                chart_type=chart_type,  # type: ignore[arg-type]
                data_source=cb.data_source,
                data_inline=cb.data_inline,
                x_column=cb.x_column,
                y_columns=cb.y_columns,
                title=cb.title,
                x_label=cb.x_label,
                y_label=cb.y_label,
                y_unit=cb.y_unit,
                bar_direction=bar_dir,  # type: ignore[arg-type]
                stacked=cb.stacked,
                legend_position=legend,  # type: ignore[arg-type]
                show_data_labels=cb.show_data_labels,
                number_format=cb.number_format,
                position=get_position(layout, "chart"),
            ))

        return SlideSchema(
            slide_id=outline_slide.slide_id,
            slide_number=slide_number,
            section=outline_slide.section,
            title=llm_slide.title or outline_slide.title,
            key_message=outline_slide.key_message,
            layout_type=layout,  # type: ignore[arg-type]
            text_elements=text_elements,
            chart_elements=chart_elements,
            speaker_note=llm_slide.speaker_note or self._default_note(outline_slide),
            validation_metadata=ValidationMetadata(
                created_at=now,
                last_modified=now,
                schema_version=CURRENT_SCHEMA_VERSION,
            ),
        )

    def _default_note(self, outline_slide: Any) -> str:
        parts = []
        if outline_slide.key_message:
            parts.append(f"Key message: {outline_slide.key_message}")
        return "\n".join(parts)
