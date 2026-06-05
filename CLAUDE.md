# CLAUDE.md — Presentation Generation Tool

This file is the authoritative guide for AI assistants and contributors working on this codebase.
Read it in full before generating any code or making architectural decisions.

---

## Project Overview

A pipeline-based presentation generation tool that converts documents into polished PPTX files.
It is designed as an open-source CLI tool with a clean module boundary for each stage of the pipeline.

**Core pipeline:**

```
Input Docs → ContentAnalyzer → StorylinePlanner → SlideSchemaGenerator
    → PPTXRenderer → SlideReviewer → AutoFixer → Exporter
         ↑                                            ↓
      ThemeLoader ──────────────────────────── final .pptx / reports
```

The key design invariant: **PPTX is never generated directly from raw input.**
Everything flows through the `slide schema` (a JSON intermediate representation).
This decouples content logic from rendering and makes every stage independently testable.

---

## MVP Scope

### In scope (MVP)

| Feature | Notes |
|---|---|
| Theme loading | YAML and JSON formats |
| Document analysis | `.md`, `.txt`, `.csv`, `.xlsx` |
| Storyline planning | `research` presentation type only |
| Slide schema generation | Full JSON schema output |
| PPTX rendering | `python-pptx`, all layout types |
| Native chart generation | Bar, line, scatter, pie — editable in PPT |
| Basic review checks | Overlap, clipping, font size, text density |
| Review report | JSON and Markdown output |
| CLI | All 8 sub-commands |

### Out of scope (post-MVP, design for extensibility)

- PDF / DOCX parsing
- LLM-based document analysis
- Image semantic analysis
- Advanced auto-layout engine
- PDF export (optional, LibreOffice headless only)
- GUI / web app
- Template marketplace
- Business report, proposal, interview, paper review storyline types

---

## Architecture

### Guiding principles

1. **Schema-first**: every render decision is driven by `SlideSchema`, not by ad-hoc logic.
2. **Interface-based extensibility**: `ContentAnalyzer`, `StorylinePlanner`, `SlideSchemaGenerator`
   each have an abstract base class so LLM-backed implementations can be swapped in later.
3. **Independent modules**: each module can be unit-tested without running the full pipeline.
4. **No image-based charts**: all charts are PowerPoint-native (`python-pptx` `Chart` objects)
   so end users can edit values directly in PowerPoint.
5. **Explicit errors, logged warnings**: raise typed exceptions at module boundaries;
   use structured logging (not `print`) for progress and diagnostics.

### Module responsibilities

| Module | Class | Responsibility |
|---|---|---|
| `theme` | `ThemeLoader` | Parse theme file → `ThemeConfig` |
| `analyzer` | `DocumentAnalyzer` | Parse input docs → `AnalysisResult` |
| `planner` | `StorylinePlanner` | `AnalysisResult` + type → `StorylineOutline` |
| `schema` | `SlideSchemaGenerator` | `StorylineOutline` + theme → `SlideSchema[]` |
| `assets` | `AssetManager` | Image validation, crop, aspect ratio, caption |
| `chart` | `ChartBuilder` | Data → `python-pptx` Chart objects |
| `renderer` | `PPTXRenderer` | `SlideSchema[]` + theme → `.pptx` file |
| `reviewer` | `SlideReviewer` | `.pptx` + `SlideSchema[]` → `ReviewReport` |
| `fixer` | `AutoFixer` | `ReviewReport` → patched `SlideSchema[]` |
| `exporter` | `Exporter` | Collects all outputs, writes final files |

---

## Folder Structure

```
pptxforgekit/
├── src/
│   └── pptxforgekit/
│       ├── __init__.py
│       ├── cli.py                  # Click-based CLI entry point
│       ├── pipeline.py             # Optional: full pipeline orchestrator
│       ├── models/                 # Pure data models (no I/O, no side effects)
│       │   ├── __init__.py
│       │   ├── theme.py            # ThemeConfig, ChartStyle, FontRule, etc.
│       │   ├── analysis.py         # AnalysisResult, Section, Figure, Table
│       │   ├── outline.py          # StorylineOutline, SlideOutline
│       │   ├── schema.py           # SlideSchema, TextElement, ChartElement, etc.
│       │   └── review.py           # ReviewReport, ReviewIssue, Severity
│       ├── interfaces/             # Abstract base classes for LLM extensibility
│       │   ├── __init__.py
│       │   ├── analyzer.py         # IContentAnalyzer
│       │   ├── planner.py          # IStorylinePlanner
│       │   └── generator.py        # ISlideSchemaGenerator
│       ├── theme/
│       │   ├── __init__.py
│       │   └── loader.py
│       ├── analyzer/
│       │   ├── __init__.py
│       │   ├── document.py         # DocumentAnalyzer (implements IContentAnalyzer)
│       │   ├── markdown_parser.py
│       │   ├── csv_parser.py
│       │   └── xlsx_parser.py
│       ├── planner/
│       │   ├── __init__.py
│       │   └── storyline.py        # RuleBasedStorylinePlanner (implements IStorylinePlanner)
│       ├── schema/
│       │   ├── __init__.py
│       │   └── generator.py        # RuleBasedSchemaGenerator (implements ISlideSchemaGenerator)
│       ├── assets/
│       │   ├── __init__.py
│       │   └── manager.py
│       ├── chart/
│       │   ├── __init__.py
│       │   └── builder.py
│       ├── renderer/
│       │   ├── __init__.py
│       │   ├── pptx.py             # PPTXRenderer
│       │   └── layout_engine.py    # Computes element positions from layout_type
│       ├── reviewer/
│       │   ├── __init__.py
│       │   ├── slide.py            # SlideReviewer orchestrator
│       │   └── checks/             # One file per check category
│       │       ├── theme_check.py
│       │       ├── layout_check.py
│       │       ├── text_check.py
│       │       ├── chart_check.py
│       │       ├── image_check.py
│       │       └── data_consistency_check.py
│       ├── fixer/
│       │   ├── __init__.py
│       │   └── auto.py
│       └── exporter/
│           ├── __init__.py
│           └── export.py
├── tests/
│   ├── conftest.py
│   ├── test_theme/
│   │   └── test_loader.py
│   ├── test_analyzer/
│   │   └── test_document.py
│   ├── test_planner/
│   │   └── test_storyline.py
│   ├── test_schema/
│   │   └── test_generator.py
│   ├── test_renderer/
│   │   └── test_pptx.py
│   ├── test_reviewer/
│   │   └── test_checks.py
│   ├── test_fixer/
│   │   └── test_auto.py
│   └── fixtures/
│       ├── themes/
│       │   └── default.yaml
│       ├── docs/
│       │   ├── sample.md
│       │   ├── sample.csv
│       │   └── sample.xlsx
│       └── schemas/
│           └── sample_slides.json
├── examples/
│   ├── input_docs/
│   │   ├── research_paper.md
│   │   ├── experiment_results.csv
│   │   └── measurements.xlsx
│   ├── themes/
│   │   ├── default.yaml
│   │   └── academic.yaml
│   ├── expected_output/
│   │   └── slides_schema.json
│   └── run_example.sh
├── docs/
│   ├── architecture.md
│   ├── slide_schema_spec.md
│   ├── theme_spec.md
│   └── extending_with_llm.md
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── ISSUE_TEMPLATE/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── LICENSE                         # MIT
└── .gitignore
```

---

## Core Data Models

### `ThemeConfig`

```python
@dataclass
class ThemeConfig:
    name: str
    colors: ColorPalette          # primary, secondary, accent, background, text
    fonts: FontConfig             # title_font, body_font, sizes
    margins: Margins              # top, bottom, left, right (in cm)
    title_position: TitlePosition # top_left, top_center, etc.
    footer: FooterConfig          # show_page_number, show_date, custom_text
    chart_style: ChartStyle       # preferred_type, color_sequence, label_style
    rules: list[ThemeRule]        # max_bullets, min_font_size, etc.
```

### `AnalysisResult`

```python
@dataclass
class AnalysisResult:
    source_files: list[str]
    title: str
    abstract: str
    key_messages: list[str]
    sections: list[Section]       # heading, paragraphs, figures, tables
    tables: list[TableCandidate]
    figures: list[FigureCandidate]
    data_files: list[DataFileRef] # csv/xlsx paths with column summaries
    conclusions: list[str]
    metadata: dict[str, Any]
```

### `StorylineOutline`

```python
@dataclass
class StorylineOutline:
    presentation_type: str        # "research", "business", etc.
    total_slides: int
    slides: list[SlideOutline]

@dataclass
class SlideOutline:
    slide_id: str                 # "s001", "s002", ...
    section: str
    title: str
    key_message: str
    suggested_layout: str         # "title_only", "title_content", "two_column", etc.
    content_hints: list[str]
    data_refs: list[str]          # reference to AnalysisResult assets
```

### `SlideSchema` (the central intermediate representation)

```json
{
  "schema_version": "1.0",
  "presentation": {
    "title": "...",
    "type": "research",
    "theme_file": "theme.yaml",
    "total_slides": 12,
    "generated_at": "2026-06-04T00:00:00Z"
  },
  "slides": [
    {
      "slide_id": "s001",
      "section": "introduction",
      "title": "Background",
      "key_message": "Problem X is unsolved due to Y.",
      "layout_type": "title_content",
      "text_elements": [
        {
          "element_id": "t001",
          "role": "body",
          "content": "- Point A\n- Point B",
          "position": {"x": 1.0, "y": 2.5, "w": 20.0, "h": 10.0},
          "font_size": 20,
          "bold": false
        }
      ],
      "chart_elements": [
        {
          "element_id": "c001",
          "chart_type": "bar",
          "data_source": "results.csv",
          "x_column": "method",
          "y_columns": ["accuracy"],
          "title": "Accuracy by Method",
          "x_label": "Method",
          "y_label": "Accuracy (%)",
          "position": {"x": 12.0, "y": 3.0, "w": 12.0, "h": 9.0}
        }
      ],
      "image_elements": [],
      "table_elements": [],
      "speaker_note": "Emphasize that prior work fails on X.",
      "data_source": "results.csv",
      "validation_metadata": {
        "created_at": "2026-06-04T00:00:00Z",
        "last_modified": "2026-06-04T00:00:00Z",
        "reviewer_flags": []
      }
    }
  ]
}
```

### `ReviewReport`

```python
@dataclass
class ReviewIssue:
    issue_id: str
    slide_id: str
    element_id: str | None
    check_category: str           # "layout", "text", "chart", "image", "data"
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    auto_fixable: bool
    suggested_fix: str | None

@dataclass
class ReviewReport:
    pptx_file: str
    schema_file: str
    reviewed_at: str
    total_issues: int
    issues: list[ReviewIssue]
    summary: dict[str, int]       # count by severity
```

---

## CLI Commands

All 8 commands must be implemented as Click sub-commands under `pptxforgekit`.

```bash
# 1. Create a starter theme file
pptxforgekit init-theme --output theme.yaml

# 2. Analyze input documents
pptxforgekit analyze ./input_docs --output analysis.json

# 3. Plan the storyline
pptxforgekit plan analysis.json --type research --output outline.json

# 4. Generate slide schema
pptxforgekit build-schema outline.json --theme theme.yaml --output slides.json

# 5. Render PPTX from schema
pptxforgekit render slides.json --theme theme.yaml --output presentation.pptx

# 6. Review the rendered PPTX
pptxforgekit review presentation.pptx slides.json --output review_report.md

# 7. Auto-fix schema based on review
pptxforgekit autofix slides.json review_report.json --output slides_fixed.json

# 8. Re-render fixed schema
pptxforgekit render slides_fixed.json --theme theme.yaml --output presentation_fixed.pptx
```

The `render` command must also accept a manually edited `slides.json` as input —
users can modify the schema in any text editor and re-render without re-running the full pipeline.

---

## Implementation Phases

### Phase 1 — Foundation (implement first)

1. All data models (`src/pptxforgekit/models/`)
2. All abstract interfaces (`src/pptxforgekit/interfaces/`)
3. `ThemeLoader` with YAML/JSON support
4. `pyproject.toml` and project scaffolding
5. `README.md` initial draft

### Phase 2 — Pipeline core

6. `DocumentAnalyzer` (markdown, txt, csv, xlsx)
7. `StorylinePlanner` (rule-based, research type)
8. `SlideSchemaGenerator` (rule-based)
9. Unit tests for phases 1–2

### Phase 3 — Rendering

10. `ChartBuilder` (bar, line, scatter, pie — native)
11. `AssetManager` (image validation, sizing)
12. `PPTXRenderer` (all layout types, charts, images, tables, speaker notes)
13. Integration test: schema → pptx round-trip

### Phase 4 — Review & Fix

14. `SlideReviewer` with all check modules
15. `AutoFixer`
16. `Exporter`
17. Full CLI wiring

### Phase 5 — Polish (before GitHub release)

18. Example input files and `run_example.sh`
19. Full test suite with fixtures
20. GitHub Actions CI (lint + test)
21. `docs/` pages

---

## Coding Conventions

- **Python 3.11+**; use `from __future__ import annotations` in all files.
- **Type hints everywhere** — no untyped function signatures.
- **`dataclasses` or `pydantic` v2** for all data models.
  - Use `pydantic` if JSON validation / serialization is the primary use case (models, schema).
  - Use plain `dataclass` for internal-only objects.
- **Logging**: use `logging.getLogger(__name__)` — never `print()` in library code.
- **Exceptions**: define project-specific exception classes in `pptxforgekit/exceptions.py`.
  Raise them with a clear message; do not swallow exceptions silently.
- **No comments that describe what the code does.** Only comment *why* when the reason is non-obvious.
- **One public class per file** in `theme/`, `analyzer/`, `renderer/`, etc.
  Helper functions live in the same file or a `_helpers.py` sibling.
- **Interfaces** (`interfaces/`) must use `abc.ABC` and `@abstractmethod`.
  Concrete implementations must not import from `interfaces/` to avoid circular deps —
  they register via duck typing, not inheritance hierarchy.
- **No global state.** Every module is instantiated with its dependencies injected at construction time.
- **`position` values** in schema elements use centimeters (float), matching `python-pptx` Cm() units.

---

## Dependencies

### Core (required)

| Package | Purpose |
|---|---|
| `python-pptx` | PPTX file generation and native charts |
| `pydantic` v2 | Data model validation and JSON serialization |
| `click` | CLI framework |
| `pyyaml` | Theme YAML parsing |
| `openpyxl` | XLSX reading |
| `pandas` | CSV/XLSX data handling for charts |
| `Pillow` | Image resolution / aspect ratio checks |

### Optional

| Package | Purpose |
|---|---|
| `pypdf` | PDF parsing (post-MVP) |
| `python-docx` | DOCX parsing (post-MVP) |
| `anthropic` | LLM-backed analyzer/planner (post-MVP) |

### Dev

| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-cov` | Coverage |
| `ruff` | Linter + formatter |
| `mypy` | Static type checking |

---

## Testing Requirements

- Every module must have a corresponding test file in `tests/test_<module>/`.
- Unit tests must not write to the filesystem — use `tmp_path` (pytest fixture) for output files.
- The `fixtures/` directory contains real sample files used across tests.
- Target: **>80% line coverage** on all non-CLI code.
- The CI pipeline runs: `ruff check .`, `mypy src/`, `pytest --cov`.

---

## What NOT to do

- Do not generate PPTX directly from raw text — always go through the schema.
- Do not use `matplotlib` to render charts as images and embed them. Use `python-pptx` native charts.
- Do not use `print()` in any library code.
- Do not add features beyond the MVP scope during the initial implementation pass.
- Do not hardcode file paths — accept them as CLI arguments or constructor parameters.
- Do not commit generated `.pptx` or `.json` output files to the repository.
- Do not add `Optional[X]` — use `X | None` (Python 3.10+ union syntax).

---

## LLM Extension Points (post-MVP)

The interfaces in `interfaces/` are designed to accept LLM-backed implementations:

```
IContentAnalyzer      → LLMContentAnalyzer (uses Claude to extract structure)
IStorylinePlanner     → LLMStorylinePlanner (uses Claude to plan narrative arc)
ISlideSchemaGenerator → LLMSchemaGenerator  (uses Claude to fill slide content)
```

When implementing LLM versions, use `anthropic` SDK with prompt caching enabled
(`cache_control: {"type": "ephemeral"}` on long system prompts and document blocks).

---

## License

MIT. All contributors must ensure that dependencies are MIT/Apache/BSD compatible.
