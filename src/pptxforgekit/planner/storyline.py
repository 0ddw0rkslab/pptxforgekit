from __future__ import annotations

import logging
from typing import Any

from pptxforgekit.exceptions import PlanningError
from pptxforgekit.interfaces.planner import IStorylinePlanner
from pptxforgekit.models.analysis import AnalysisResult, Section
from pptxforgekit.models.outline import SlideOutline, StorylineOutline

logger = logging.getLogger(__name__)

# Research presentation structure template
# Each entry: (section_key, title_template, layout, content_source_key)
_RESEARCH_TEMPLATE: list[dict[str, Any]] = [
    {
        "section": "cover",
        "title_key": "title",
        "layout": "cover",
        "content_hints": ["subtitle from abstract", "author / affiliation"],
    },
    {
        "section": "agenda",
        "title": "Agenda",
        "layout": "title_content",
        "content_hints": ["Background", "Methods", "Experiments", "Results", "Conclusion"],
    },
    {
        "section": "background",
        "title": "Background & Motivation",
        "layout": "title_content",
        "content_from": "sections",
        "section_keywords": ["background", "motivation", "introduction", "related"],
    },
    {
        "section": "problem",
        "title": "Problem Statement",
        "layout": "title_content",
        "content_from": "key_messages",
    },
    {
        "section": "method",
        "title": "Methods",
        "layout": "title_content",
        "content_from": "sections",
        "section_keywords": ["method", "approach", "model", "architecture", "algorithm"],
    },
    {
        "section": "experiment",
        "title": "Experimental Setup",
        "layout": "title_content",
        "content_from": "sections",
        "section_keywords": ["experiment", "setup", "dataset", "baseline"],
    },
    {
        "section": "results",
        "title": "Results",
        "layout": "title_chart",
        "content_from": "data_files",
    },
    {
        "section": "analysis",
        "title": "Analysis & Discussion",
        "layout": "title_content",
        "content_from": "sections",
        "section_keywords": ["discussion", "analysis", "ablation", "comparison"],
    },
    {
        "section": "conclusion",
        "title": "Conclusion",
        "layout": "title_content",
        "content_from": "conclusions",
    },
    {
        "section": "qa",
        "title": "Thank You & Q&A",
        "layout": "cover",
        "content_hints": [],
    },
]

_SUPPORTED_TYPES = {"research"}


class RuleBasedStorylinePlanner(IStorylinePlanner):
    def plan(self, analysis: AnalysisResult, presentation_type: str) -> StorylineOutline:
        if presentation_type not in _SUPPORTED_TYPES:
            raise PlanningError(
                f"Unsupported presentation type '{presentation_type}'. "
                f"Supported: {sorted(_SUPPORTED_TYPES)}"
            )
        logger.info("Planning '%s' storyline for: %s", presentation_type, analysis.title)
        if presentation_type == "research":
            return self._plan_research(analysis)
        raise PlanningError(f"No planner for type '{presentation_type}'")

    def _plan_research(self, analysis: AnalysisResult) -> StorylineOutline:
        slides: list[SlideOutline] = []
        slide_counter = 1

        for template in _RESEARCH_TEMPLATE:
            outline = self._build_slide(template, analysis, slide_counter)
            if outline is None:
                continue
            slides.append(outline)
            slide_counter += 1

            # Expand extra result slides if multiple data files exist
            if template["section"] == "results" and len(analysis.data_files) > 1:
                for i, data_file in enumerate(analysis.data_files[1:], start=1):
                    extra = SlideOutline(
                        slide_id=f"s{slide_counter:03d}",
                        section="results",
                        title="Results — " + data_file.file_path.replace("\\", "/").split("/")[-1],
                        key_message="",
                        suggested_layout="title_chart",
                        data_refs=[data_file.file_path],
                    )
                    slides.append(extra)
                    slide_counter += 1

        return StorylineOutline(
            presentation_type="research",
            title=analysis.title,
            total_slides=len(slides),
            slides=slides,
        )

    def _build_slide(
        self,
        template: dict[str, Any],
        analysis: AnalysisResult,
        counter: int,
    ) -> SlideOutline | None:
        slide_id = f"s{counter:03d}"
        section = template["section"]
        layout = template["layout"]

        # Determine title
        if "title_key" in template:
            title = analysis.title or "Untitled"
        else:
            title = str(template.get("title", section.title()))

        # Determine content_hints and data_refs
        content_hints: list[str] = list(template.get("content_hints", []))
        data_refs: list[str] = []
        key_message = ""

        content_from = template.get("content_from")

        if content_from == "key_messages":
            content_hints = list(analysis.key_messages[:6])
            key_message = content_hints[0] if content_hints else ""

        elif content_from == "conclusions":
            content_hints = list(analysis.conclusions[:6])
            key_message = content_hints[0] if content_hints else ""

        elif content_from == "data_files":
            if not analysis.data_files:
                logger.debug("No data files found; skipping results slide")
                return None
            first_file = analysis.data_files[0]
            data_refs = [first_file.file_path]
            cols = first_file.columns
            content_hints = [f"Column: {c}" for c in cols[:5]]
            key_message = f"Data from {first_file.file_path.split('/')[-1].split(chr(92))[-1]}"

        elif content_from == "sections":
            keywords: list[str] = template.get("section_keywords", [])
            matched = self._find_sections(analysis, keywords)
            if matched:
                for sec in matched[:2]:
                    content_hints.extend(sec.paragraphs[:3])
                key_message = content_hints[0] if content_hints else ""
            else:
                # Still produce the slide with empty hints so the pipeline doesn't skip it
                content_hints = [f"See source: {kw}" for kw in keywords[:2]]

        return SlideOutline(
            slide_id=slide_id,
            section=section,
            title=title,
            key_message=key_message[:200] if key_message else "",
            suggested_layout=layout,
            content_hints=content_hints[:6],
            data_refs=data_refs,
        )

    def _find_sections(self, analysis: AnalysisResult, keywords: list[str]) -> list[Section]:
        matched = []
        for sec in analysis.sections:
            heading_lower = sec.heading.lower()
            if any(kw in heading_lower for kw in keywords):
                matched.append(sec)
        return matched
