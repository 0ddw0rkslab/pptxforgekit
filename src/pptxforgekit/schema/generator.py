from __future__ import annotations

import logging
from datetime import UTC, datetime

from pptxforgekit.interfaces.generator import ISlideSchemaGenerator
from pptxforgekit.models.outline import SlideOutline, StorylineOutline
from pptxforgekit.models.schema import (
    CURRENT_SCHEMA_VERSION,
    ChartElement,
    PresentationMeta,
    PresentationSchema,
    SlideSchema,
    TableElement,
    TextElement,
    TextStyle,
    ValidationMetadata,
)
from pptxforgekit.models.theme import ThemeConfig
from pptxforgekit.renderer.layout_engine import get_position as _pos

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class RuleBasedSchemaGenerator(ISlideSchemaGenerator):
    def generate(self, outline: StorylineOutline, theme: ThemeConfig) -> PresentationSchema:
        logger.info(
            "Generating schema for '%s' (%d slides)", outline.title, outline.total_slides
        )
        now = _now_iso()
        slides = [
            self._build_slide(s, theme, now, slide_number=i)
            for i, s in enumerate(outline.slides, start=1)
        ]
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

    def _build_slide(
        self,
        outline: SlideOutline,
        theme: ThemeConfig,
        now: str,
        slide_number: int,
    ) -> SlideSchema:
        layout = outline.suggested_layout
        text_elements: list[TextElement] = []
        chart_elements: list[ChartElement] = []
        table_elements: list[TableElement] = []

        # ── Title ──
        if layout != "blank":
            title_font = (
                theme.fonts.title_size if layout == "cover" else theme.fonts.heading_size
            )
            text_elements.append(TextElement(
                element_id=f"{outline.slide_id}_title",
                role="title",
                content=outline.title,
                position=_pos(layout, "title"),
                style=TextStyle(
                    font_size=title_font,
                    bold=True,
                    color=theme.colors.primary,
                ),
            ))

        # ── Layout-specific body ──
        if layout == "cover":
            subtitle_text = outline.key_message or (
                outline.content_hints[0] if outline.content_hints else ""
            )
            if subtitle_text:
                text_elements.append(TextElement(
                    element_id=f"{outline.slide_id}_subtitle",
                    role="subtitle",
                    content=subtitle_text,
                    position=_pos("cover", "subtitle"),
                    style=TextStyle(
                        font_size=theme.fonts.body_size,
                        color=theme.colors.text_light,
                    ),
                ))

        elif layout == "title_content":
            body_text = self._build_body_text(outline)
            if body_text:
                text_elements.append(TextElement(
                    element_id=f"{outline.slide_id}_body",
                    role="body",
                    content=body_text,
                    position=_pos("title_content", "body"),
                    style=TextStyle(
                        font_size=theme.fonts.body_size,
                        color=theme.colors.text,
                    ),
                ))

        elif layout == "two_column":
            half = max(1, len(outline.content_hints) // 2)
            left_hints = outline.content_hints[:half] or outline.content_hints
            right_hints = outline.content_hints[half:]
            if left_hints:
                text_elements.append(TextElement(
                    element_id=f"{outline.slide_id}_body_left",
                    role="body",
                    content=self._hints_to_bullets(left_hints),
                    position=_pos("two_column", "body_left"),
                    style=TextStyle(font_size=theme.fonts.body_size),
                ))
            if right_hints:
                text_elements.append(TextElement(
                    element_id=f"{outline.slide_id}_body_right",
                    role="body",
                    content=self._hints_to_bullets(right_hints),
                    position=_pos("two_column", "body_right"),
                    style=TextStyle(font_size=theme.fonts.body_size),
                ))

        elif layout == "title_chart":
            chart_elements.extend(self._build_chart_elements(outline, theme))

        elif layout == "title_table":
            table_elements.extend(self._build_table_elements(outline))

        return SlideSchema(
            slide_id=outline.slide_id,
            slide_number=slide_number,
            section=outline.section,
            title=outline.title,
            key_message=outline.key_message,
            layout_type=layout,  # type: ignore[arg-type]
            text_elements=text_elements,
            chart_elements=chart_elements,
            table_elements=table_elements,
            speaker_note=self._build_speaker_note(outline),
            validation_metadata=ValidationMetadata(
                created_at=now,
                last_modified=now,
                schema_version=CURRENT_SCHEMA_VERSION,
            ),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_body_text(self, outline: SlideOutline) -> str:
        if outline.content_hints:
            return self._hints_to_bullets(outline.content_hints[:6])
        return outline.key_message

    def _hints_to_bullets(self, hints: list[str]) -> str:
        return "\n".join(f"• {h}" for h in hints if h.strip())

    def _build_chart_elements(
        self, outline: SlideOutline, theme: ThemeConfig
    ) -> list[ChartElement]:
        if not outline.data_refs:
            return []
        return [ChartElement(
            element_id=f"{outline.slide_id}_chart",
            chart_type=theme.chart_style.preferred_type,  # type: ignore[arg-type]
            data_source=outline.data_refs[0],
            x_column=None,    # auto-detect
            y_columns=[],     # auto-detect
            title=outline.title,
            position=_pos("title_chart", "chart"),
        )]

    def _build_table_elements(self, outline: SlideOutline) -> list[TableElement]:
        if not outline.data_refs:
            return []
        return [TableElement(
            element_id=f"{outline.slide_id}_table",
            headers=["Column"],
            rows=[],
            caption=outline.data_refs[0],
            position=_pos("title_table", "table"),
        )]

    def _build_speaker_note(self, outline: SlideOutline) -> str:
        parts: list[str] = []
        if outline.key_message:
            parts.append(f"Key message: {outline.key_message}")
        if outline.content_hints:
            points = "\n".join(f"  - {h}" for h in outline.content_hints)
            parts.append(f"Points to cover:\n{points}")
        return "\n\n".join(parts)
