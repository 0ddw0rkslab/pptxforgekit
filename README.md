# presentation-tool

A pipeline-based CLI tool for generating polished PowerPoint presentations from documents.

Rather than generating PPTX directly, it follows a structured pipeline:

```
Input Docs → ContentAnalyzer → StorylinePlanner → SlideSchemaGenerator
    → PPTXRenderer → SlideReviewer → AutoFixer → Exporter
```

Every slide is first expressed as a **slide schema** (JSON), which is the single source of truth for rendering. This makes each stage independently testable and the entire pipeline inspectable — or hand-editable in any text editor.

## Features

- Analyze Markdown, plain text, CSV, and Excel documents
- Generate storylines for research presentations
- Produce editable **native PowerPoint charts** (not image exports)
- Review generated slides for layout, text density, and data consistency issues
- Auto-fix common issues; report the rest
- Optional **LLM-backed pipeline**: Claude, GPT, Gemini, or Ollama (local)
- Fully CLI-driven with a clean JSON intermediate format

## Prerequisites

- Python 3.11 or later
- pip

> **Note:** This package is not yet on PyPI. Install from source using the instructions below.

## Installation

```bash
git clone https://github.com/0ddw0rkslab/pptxforgekit
cd presentation-tool
pip install -e .
```

For development (linter, type checker, test runner):

```bash
pip install -e ".[dev]"
```

To enable LLM-backed pipeline stages, install the extras for the provider(s) you use:

```bash
pip install -e ".[llm-claude]"    # Anthropic Claude
pip install -e ".[llm-openai]"    # OpenAI GPT
pip install -e ".[llm-gemini]"    # Google Gemini (free tier available)
pip install -e ".[llm-ollama]"    # Ollama (local, no API key needed)
pip install -e ".[llm-all]"       # all of the above
```

Then copy `.env.example` to `.env` and add your API key(s):

```bash
cp .env.example .env
# edit .env and set e.g. ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Start

```bash
# 1. Create a starter theme
presentation-tool init-theme --output theme.yaml

# 2. Analyze documents and generate a PPTX in one pipeline
presentation-tool analyze ./input_docs   --output analysis.json
presentation-tool plan    analysis.json  --type research --output outline.json
presentation-tool build-schema outline.json --theme theme.yaml --output slides.json
presentation-tool render  slides.json   --theme theme.yaml --output presentation.pptx
```

With an LLM for richer content:

```bash
presentation-tool analyze ./input_docs  --output analysis.json --llm claude
presentation-tool plan    analysis.json --output outline.json  --llm claude
presentation-tool build-schema outline.json --theme theme.yaml --output slides.json --llm claude

# list all providers and their models
presentation-tool llm-info
```

You can also manually edit `slides.json` and re-run `render` — no need to re-run the full pipeline.

## Supported Input Formats

| Format | Supported | Notes |
|--------|-----------|-------|
| Markdown (`.md`) | Yes | Headings, paragraphs, lists |
| Plain text (`.txt`) | Yes | Line-based parsing |
| CSV (`.csv`) | Yes | Auto-detected as chart/table data |
| Excel (`.xlsx`) | Yes | All sheets parsed |
| PDF | Planned | Post-MVP |
| Word (`.docx`) | Planned | Post-MVP |

## Documentation

| Document | Description |
|---|---|
| [docs/cli_reference.md](docs/cli_reference.md) | All 8 commands, options, LLM usage, and tips |
| [docs/chart_reference.md](docs/chart_reference.md) | Chart types, schema fields, inline data, validation |
| [docs/slide_schema_spec.md](docs/slide_schema_spec.md) | Full SlideSchema JSON format reference |
| [docs/theme_spec.md](docs/theme_spec.md) | Theme YAML/JSON format reference |
| [docs/architecture.md](docs/architecture.md) | Module layout and design decisions |
| [docs/extending_with_llm.md](docs/extending_with_llm.md) | Writing custom LLM-backed pipeline stages |

## Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Run lint: `ruff check . && mypy src/`
6. Open a pull request

## Roadmap

### v0.2 — Additional presentation types
- Business report storyline (`--type business`)
- Proposal storyline (`--type proposal`)

### v0.3 — Richer input formats
- PDF parsing via `pypdf`
- Word document parsing via `python-docx`

### v0.4 — Advanced rendering
- Image semantic analysis and auto-captioning
- Advanced auto-layout engine (conflict-free positioning)
- Optional PDF export via LibreOffice headless

## License

MIT
