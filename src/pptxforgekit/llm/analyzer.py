from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field

from pptxforgekit.analyzer.csv_parser import parse_csv
from pptxforgekit.analyzer.document import DocumentAnalyzer
from pptxforgekit.analyzer.xlsx_parser import parse_xlsx
from pptxforgekit.exceptions import AnalysisError
from pptxforgekit.interfaces.analyzer import IContentAnalyzer
from pptxforgekit.llm.prompts import ANALYZER_SYSTEM, ANALYZER_USER_TEMPLATE
from pptxforgekit.llm.provider import LLMProvider
from pptxforgekit.models.analysis import (
    AnalysisResult,
    DataFileRef,
    FigureCandidate,
    Section,
    TableCandidate,
)

logger = logging.getLogger(__name__)

_TEXT_EXTS = {".md", ".txt"}
_DATA_EXTS = {".csv", ".xlsx"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}

# ~30,000 chars ≈ 7,500 tokens — keeps requests within free-tier per-minute limits
_MAX_COMBINED_CHARS = 30_000


class _LLMAnalysisOutput(BaseModel):
    """Intermediate model matching the LLM JSON output schema."""
    title: str = ""
    abstract: str = ""
    key_messages: list[str] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMContentAnalyzer(IContentAnalyzer):
    """LLM-powered document analyzer.

    Text documents (.md, .txt) are sent to the LLM for deep extraction.
    Data files (.csv, .xlsx) are still processed by the rule-based parser
    since LLMs cannot read binary files.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._rule_analyzer = DocumentAnalyzer()

    def analyze(self, input_path: Path) -> AnalysisResult:
        if input_path.is_dir():
            return self._analyze_directory(input_path)
        if input_path.is_file():
            return self._analyze_single(input_path)
        raise AnalysisError(f"Path does not exist: {input_path}")

    # ── directory ─────────────────────────────────────────────────────────────

    def _analyze_directory(self, directory: Path) -> AnalysisResult:
        directory = directory.resolve()
        all_files = [f for f in directory.rglob("*") if f.is_file()]

        text_files = [f for f in all_files if f.suffix.lower() in _TEXT_EXTS]
        data_files = [f for f in all_files if f.suffix.lower() in _DATA_EXTS]
        image_files = [f for f in all_files if f.suffix.lower() in _IMAGE_EXTS]

        if not text_files and not data_files:
            raise AnalysisError(f"No supported files found in {directory}")

        # ── LLM extracts structure from text ──────────────────────────────────
        combined_text = ""
        for f in sorted(text_files):
            try:
                combined_text += f"\n\n=== {f.name} ===\n\n"
                combined_text += f.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                logger.warning("Could not read %s: %s", f, exc)
        if len(combined_text) > _MAX_COMBINED_CHARS:
            logger.warning(
                "Document text truncated from %d to %d chars to stay within token limits",
                len(combined_text),
                _MAX_COMBINED_CHARS,
            )
            combined_text = combined_text[:_MAX_COMBINED_CHARS]

        llm_out = self._call_llm(combined_text) if combined_text.strip() else _LLMAnalysisOutput()

        # ── Rule-based parser handles data files ──────────────────────────────
        data_refs: list[DataFileRef] = []
        tables: list[TableCandidate] = []
        for f in data_files:
            try:
                if f.suffix.lower() == ".csv":
                    ref, tbl = parse_csv(f)
                    data_refs.append(ref)
                    tables.append(tbl)
                else:
                    for ref, tbl in parse_xlsx(f):
                        data_refs.append(ref)
                        tables.append(tbl)
            except Exception as exc:
                logger.warning("Skipping data file %s: %s", f, exc)

        # ── Probe images ──────────────────────────────────────────────────────
        figures: list[FigureCandidate] = [
            self._rule_analyzer._probe_image(f) for f in image_files
        ]

        sections = [
            Section(heading=s.get("heading", ""), paragraphs=s.get("paragraphs", []))
            for s in llm_out.sections
        ]

        return AnalysisResult(
            source_files=[str(f) for f in sorted(all_files)],
            title=llm_out.title or directory.name,
            abstract=llm_out.abstract,
            key_messages=llm_out.key_messages[:10],
            sections=sections,
            tables=tables,
            figures=figures,
            data_files=data_refs,
            conclusions=llm_out.conclusions[:5],
            metadata=llm_out.metadata,
        )

    # ── single file ───────────────────────────────────────────────────────────

    def _analyze_single(self, path: Path) -> AnalysisResult:
        ext = path.suffix.lower()
        if ext in _TEXT_EXTS:
            text = path.read_text(encoding="utf-8", errors="replace")
            llm_out = self._call_llm(text)
            sections = [
                Section(heading=s.get("heading", ""), paragraphs=s.get("paragraphs", []))
                for s in llm_out.sections
            ]
            return AnalysisResult(
                source_files=[str(path)],
                title=llm_out.title or path.stem,
                abstract=llm_out.abstract,
                key_messages=llm_out.key_messages[:10],
                sections=sections,
                data_files=[],
                conclusions=llm_out.conclusions[:5],
                metadata=llm_out.metadata,
            )
        # Delegate data/image files to rule-based analyzer
        return self._rule_analyzer.analyze(path)

    # ── LLM call ──────────────────────────────────────────────────────────────

    def _call_llm(self, document_text: str) -> _LLMAnalysisOutput:
        user_prompt = ANALYZER_USER_TEMPLATE.format(document_text=document_text)
        logger.info(
            "[LLMContentAnalyzer] calling %s/%s",
            self._provider.provider_name,
            self._provider.model,
        )
        return cast(_LLMAnalysisOutput, self._provider.complete_json(
            user_prompt=user_prompt,
            system_prompt=ANALYZER_SYSTEM,
            model_class=_LLMAnalysisOutput,
            rate_limit_retries=5,
            rate_limit_backoff=15.0,
        ))
