# Architecture

## Pipeline Overview

```
Input Docs → DocumentAnalyzer → StorylinePlanner → SlideSchemaGenerator
    → PPTXRenderer → SlideReviewer → AutoFixer → Exporter
         ↑                                            ↓
      ThemeLoader ──────────────────────────── final .pptx / reports
```

The key design invariant: **PPTX is never generated from raw input.**
Every render decision flows through `SlideSchema` (a JSON intermediate representation).

## Module Responsibilities

| Module | Class | Input → Output |
|---|---|---|
| `theme/loader.py` | `ThemeLoader` | YAML/JSON → `ThemeConfig` |
| `analyzer/document.py` | `DocumentAnalyzer` | files → `AnalysisResult` |
| `planner/storyline.py` | `RuleBasedStorylinePlanner` | `AnalysisResult` → `StorylineOutline` |
| `schema/generator.py` | `RuleBasedSchemaGenerator` | `StorylineOutline` + theme → `SlideSchema[]` |
| `chart/builder.py` | `ChartBuilder` | `ChartElement` + data → native pptx chart |
| `assets/manager.py` | `AssetManager` | image path → validated/cropped image |
| `renderer/pptx.py` | `PPTXRenderer` | `SlideSchema[]` + theme → `.pptx` |
| `reviewer/slide.py` | `SlideReviewer` | `.pptx` + schema → `ReviewReport` |
| `fixer/auto.py` | `AutoFixer` | `ReviewReport` + schema → `FixResult` |
| `exporter/export.py` | `Exporter` | various outputs → final files |

## Extensibility

The `interfaces/` package defines abstract base classes. Each interface has both a
rule-based implementation and an LLM-backed implementation that can be selected at
runtime via the `--llm` CLI flag:

```
interfaces/analyzer.py   → IContentAnalyzer
                              ├── DocumentAnalyzer        (rule-based, default)
                              └── LLMContentAnalyzer      (llm/, uses any provider)

interfaces/planner.py    → IStorylinePlanner
                              ├── RuleBasedStorylinePlanner (rule-based, default)
                              └── LLMStorylinePlanner       (llm/)

interfaces/generator.py  → ISlideSchemaGenerator
                              ├── RuleBasedSchemaGenerator  (rule-based, default)
                              └── LLMSchemaGenerator        (llm/)
```

LLM providers (Claude, GPT, Gemini, Ollama) are abstracted behind `llm/provider.py`
and selected via `llm/registry.py`. See [extending_with_llm.md](extending_with_llm.md)
for writing a custom provider or a new LLM-backed stage.

## SlideSchema as Central IR

The JSON schema is the single contract between all pipeline stages. It is versioned
(`schema_version`) and validated by Pydantic on read. Any stage can be run in
isolation by loading or hand-crafting a `slides.json`.

See `src/presentation_tool/models/schema.py` for the full Pydantic model definitions.
