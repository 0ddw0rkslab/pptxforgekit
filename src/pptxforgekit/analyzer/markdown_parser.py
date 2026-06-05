from __future__ import annotations

import re
from pathlib import Path

from pptxforgekit.models.analysis import Section


def parse_markdown(path: Path) -> tuple[str, str, list[Section]]:
    """Return (title, abstract, sections) from a markdown file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    title = ""
    abstract = ""
    sections: list[Section] = []
    current_heading = ""
    current_paragraphs: list[str] = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal current_paragraphs
        joined = " ".join(buffer).strip()
        if joined:
            current_paragraphs.append(joined)
        buffer.clear()

    def flush_section() -> None:
        nonlocal current_heading, current_paragraphs
        flush_buffer()
        if current_heading or current_paragraphs:
            sections.append(Section(heading=current_heading, paragraphs=list(current_paragraphs)))
        current_heading = ""
        current_paragraphs = []

    for line in lines:
        h1 = re.match(r"^#\s+(.+)", line)
        h2 = re.match(r"^##\s+(.+)", line)
        h3 = re.match(r"^###\s+(.+)", line)

        if h1:
            flush_section()
            heading_text = h1.group(1).strip()
            if not title:
                title = heading_text
            current_heading = heading_text
        elif h2 or h3:
            flush_section()
            current_heading = (h2 or h3).group(1).strip()  # type: ignore[union-attr]
        elif line.strip() == "":
            flush_buffer()
        else:
            buffer.append(line.strip())

    flush_section()

    # Use the first non-heading paragraph as abstract if none is explicitly labeled
    for sec in sections:
        lower = sec.heading.lower()
        if "abstract" in lower or "summary" in lower or "introduction" in lower:
            if sec.paragraphs:
                abstract = sec.paragraphs[0]
                break

    if not abstract:
        for sec in sections:
            if sec.paragraphs:
                abstract = sec.paragraphs[0]
                break

    return title, abstract, sections


def extract_key_messages(sections: list[Section]) -> list[str]:
    """Heuristically extract key messages from bullet lines."""
    messages: list[str] = []
    for sec in sections:
        for para in sec.paragraphs:
            for line in para.splitlines():
                stripped = line.strip()
                if stripped.startswith(("- ", "* ", "• ")):
                    messages.append(stripped.lstrip("-*• ").strip())
    return messages[:10]


def extract_conclusions(sections: list[Section]) -> list[str]:
    for sec in sections:
        if "conclusion" in sec.heading.lower():
            return sec.paragraphs[:5]
    return []
