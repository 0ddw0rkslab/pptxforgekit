from __future__ import annotations

import logging
from pathlib import Path

from pptxforgekit.exceptions import AnalysisError
from pptxforgekit.interfaces.analyzer import IContentAnalyzer
from pptxforgekit.models.analysis import (
    AnalysisResult,
    DataFileRef,
    FigureCandidate,
    Section,
    TableCandidate,
)

from .csv_parser import parse_csv
from .markdown_parser import (
    extract_conclusions,
    extract_key_messages,
    parse_markdown,
)
from .xlsx_parser import parse_xlsx

logger = logging.getLogger(__name__)

_SUPPORTED_EXTS = {".md", ".txt", ".csv", ".xlsx", ".png", ".jpg", ".jpeg"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}


class DocumentAnalyzer(IContentAnalyzer):
    def analyze(self, input_path: Path) -> AnalysisResult:
        if input_path.is_dir():
            return self._analyze_directory(input_path)
        if input_path.is_file():
            return self._analyze_single(input_path)
        raise AnalysisError(f"Input path does not exist: {input_path}")

    def _analyze_directory(self, directory: Path) -> AnalysisResult:
        directory = directory.resolve()
        logger.info("Analyzing directory: %s", directory)
        all_files = [f for f in directory.rglob("*") if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTS]
        if not all_files:
            raise AnalysisError(f"No supported files found in {directory}")

        title = directory.name
        abstract = ""
        key_messages: list[str] = []
        sections: list[Section] = []
        tables: list[TableCandidate] = []
        figures: list[FigureCandidate] = []
        data_files: list[DataFileRef] = []
        conclusions: list[str] = []

        for file in sorted(all_files):
            ext = file.suffix.lower()
            try:
                if ext in (".md", ".txt"):
                    t, a, secs = parse_markdown(file) if ext == ".md" else self._parse_txt(file)
                    if not title or title == directory.name:
                        title = t or title
                    if not abstract:
                        abstract = a
                    sections.extend(secs)
                    key_messages.extend(extract_key_messages(secs))
                    conclusions.extend(extract_conclusions(secs))
                elif ext == ".csv":
                    ref, tbl = parse_csv(file)
                    data_files.append(ref)
                    tables.append(tbl)
                elif ext == ".xlsx":
                    for ref, tbl in parse_xlsx(file):
                        data_files.append(ref)
                        tables.append(tbl)
                elif ext in _IMAGE_EXTS:
                    figures.append(self._probe_image(file))
            except Exception as exc:
                logger.warning("Skipping %s: %s", file, exc)

        return AnalysisResult(
            source_files=[str(f) for f in all_files],
            title=title,
            abstract=abstract,
            key_messages=list(dict.fromkeys(key_messages))[:10],
            sections=sections,
            tables=tables,
            figures=figures,
            data_files=data_files,
            conclusions=list(dict.fromkeys(conclusions))[:5],
        )

    def _analyze_single(self, path: Path) -> AnalysisResult:
        path = path.resolve()
        logger.info("Analyzing file: %s", path)
        ext = path.suffix.lower()
        if ext not in _SUPPORTED_EXTS:
            raise AnalysisError(f"Unsupported file type: {ext}")

        if ext in (".md", ".txt"):
            t, a, secs = parse_markdown(path) if ext == ".md" else self._parse_txt(path)
            return AnalysisResult(
                source_files=[str(path)],
                title=t or path.stem,
                abstract=a,
                key_messages=extract_key_messages(secs),
                sections=secs,
                tables=[],
                figures=[],
                data_files=[],
                conclusions=extract_conclusions(secs),
            )
        if ext == ".csv":
            ref, tbl = parse_csv(path)
            return AnalysisResult(
                source_files=[str(path)],
                title=path.stem,
                data_files=[ref],
                tables=[tbl],
            )
        if ext == ".xlsx":
            sheets = parse_xlsx(path)
            refs = [r for r, _ in sheets]
            tbls = [t for _, t in sheets]
            return AnalysisResult(
                source_files=[str(path)],
                title=path.stem,
                data_files=refs,
                tables=tbls,
            )
        raise AnalysisError(f"Cannot analyze standalone image: {path}")

    def _parse_txt(self, path: Path) -> tuple[str, str, list[Section]]:
        lines = path.read_text(encoding="utf-8").splitlines()
        title = lines[0].strip() if lines else path.stem
        body = " ".join(ln.strip() for ln in lines[1:] if ln.strip())
        sec = Section(heading=title, paragraphs=[body] if body else [])
        return title, body[:300], [sec]

    def _probe_image(self, path: Path) -> FigureCandidate:
        try:
            from PIL import Image
            with Image.open(path) as img:
                w, h = img.size
        except Exception:
            w, h = 0, 0
        return FigureCandidate(
            source_file=str(path),
            caption=path.stem,
            file_path=str(path),
            width=w,
            height=h,
        )
