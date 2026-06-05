# CLI Reference

All commands are sub-commands of `presentation-tool`. Run any command with `--help` for full option details.

```
presentation-tool --help
presentation-tool <command> --help
```

---

## Commands

### `init-theme`

Create a starter `theme.yaml` with default values.

```bash
presentation-tool init-theme --output theme.yaml
```

| Option | Default | Description |
|---|---|---|
| `-o / --output` | `theme.yaml` | Output path |

---

### `analyze`

Parse input documents and produce `analysis.json`.

```bash
presentation-tool analyze ./input_docs --output analysis.json
presentation-tool analyze ./input_docs --output analysis.json --llm claude
presentation-tool analyze paper.md     --output analysis.json --llm gpt --model gpt-4o-mini
```

| Option | Required | Description |
|---|---|---|
| `INPUT_PATH` | Yes | Directory or single file (`.md`, `.txt`, `.csv`, `.xlsx`) |
| `-o / --output` | Yes | Output path for `analysis.json` |
| `--llm` | No | LLM provider: `claude`, `gpt`, `gemini`, `ollama` |
| `--model` | No | Model ID for the chosen provider (see `llm-info`) |

Without `--llm`, a rule-based parser extracts structure. With `--llm`, text files are sent to the LLM for richer extraction; CSV/XLSX files are always handled by the rule-based parser.

---

### `plan`

Generate a storyline outline from `analysis.json`.

```bash
presentation-tool plan analysis.json --type research --output outline.json
presentation-tool plan analysis.json --output outline.json --llm gemini
```

| Option | Default | Description |
|---|---|---|
| `ANALYSIS_JSON` | — | Path to `analysis.json` |
| `--type` | `research` | Presentation type |
| `-o / --output` | — | Output path for `outline.json` |
| `--llm` | No | LLM provider |
| `--model` | No | Model ID |

---

### `build-schema`

Generate the slide schema JSON from `outline.json` and a theme file.

```bash
presentation-tool build-schema outline.json --theme theme.yaml --output slides.json
presentation-tool build-schema outline.json --theme theme.yaml --output slides.json --llm claude --model claude-opus-4-8
```

| Option | Required | Description |
|---|---|---|
| `OUTLINE_JSON` | Yes | Path to `outline.json` |
| `--theme` | Yes | Theme YAML or JSON file |
| `-o / --output` | Yes | Output path for `slides.json` |
| `--llm` | No | LLM provider |
| `--model` | No | Model ID |

The generated `slides.json` can be edited by hand and re-rendered without re-running earlier stages.

---

### `render`

Render a slide schema into a `.pptx` file.

```bash
presentation-tool render slides.json --theme theme.yaml --output presentation.pptx
```

| Option | Required | Description |
|---|---|---|
| `SCHEMA_JSON` | Yes | Path to `slides.json` (or any hand-crafted schema) |
| `--theme` | Yes | Theme YAML or JSON file |
| `-o / --output` | Yes | Output `.pptx` path |

`data_source` paths inside the schema are resolved relative to the directory containing `slides.json`.

---

### `review`

Review a rendered PPTX against its schema and write a report.

```bash
presentation-tool review presentation.pptx slides.json --output review_report.md
presentation-tool review presentation.pptx slides.json --theme theme.yaml --output review_report.json
```

| Option | Required | Description |
|---|---|---|
| `PPTX_FILE` | Yes | Rendered `.pptx` file |
| `SCHEMA_JSON` | Yes | Corresponding `slides.json` |
| `--theme` | No | Theme file (uses defaults if omitted) |
| `-o / --output` | Yes | Report path — `.json` for autofix input, `.md` for human reading |

---

### `autofix`

Apply auto-fixable issues from a review report to the schema.

```bash
presentation-tool autofix slides.json review_report.json --output slides_fixed.json
```

| Option | Required | Description |
|---|---|---|
| `SCHEMA_JSON` | Yes | Source schema |
| `REVIEW_JSON` | Yes | Review report (`.json` format) |
| `-o / --output` | Yes | Output path for fixed schema |

---

### `llm-info`

Show all available LLM providers, their supported models, required API keys, and install commands.

```bash
presentation-tool llm-info
```

---

## Full Pipeline Example

```bash
# 1. Theme
presentation-tool init-theme --output theme.yaml

# 2–4. Analyze → Plan → Schema  (add --llm <provider> to any step)
presentation-tool analyze ./input_docs   --output analysis.json
presentation-tool plan    analysis.json  --type research --output outline.json
presentation-tool build-schema outline.json --theme theme.yaml --output slides.json

# 5. Render
presentation-tool render slides.json --theme theme.yaml --output presentation.pptx

# 6. Review (save both formats)
presentation-tool review presentation.pptx slides.json --output review_report.json
presentation-tool review presentation.pptx slides.json --output review_report.md

# 7. Fix + re-render
presentation-tool autofix slides.json review_report.json --output slides_fixed.json
presentation-tool render  slides_fixed.json --theme theme.yaml --output presentation_fixed.pptx
```

---

## LLM Integration

### Setup

Install the extras for the provider(s) you want:

```bash
pip install -e ".[llm-claude]"    # Anthropic Claude
pip install -e ".[llm-openai]"    # OpenAI GPT
pip install -e ".[llm-gemini]"    # Google Gemini (free tier available)
pip install -e ".[llm-ollama]"    # Ollama — local models, no API key
pip install -e ".[llm-all]"       # all providers
```

Copy `.env.example` to `.env` and add your key(s):

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
# OLLAMA_BASE_URL=http://localhost:11434  (only if not on localhost)
```

### Provider and model selection

```bash
# Use provider default model
presentation-tool analyze ./docs --output analysis.json --llm claude

# Specify a model explicitly
presentation-tool analyze ./docs --output analysis.json --llm gpt --model gpt-4o-mini
presentation-tool analyze ./docs --output analysis.json --llm ollama --model mistral
```

Run `presentation-tool analyze --help` to see the full model list inline, or use `presentation-tool llm-info` for a detailed provider overview.

### Which stages support LLM?

| Stage | `--llm` effect |
|---|---|
| `analyze` | LLM extracts title, abstract, sections, key messages, conclusions from text files |
| `plan` | LLM plans the narrative arc and decides slide structure |
| `build-schema` | LLM writes slide body text and chooses chart content |
| `render` / `review` / `autofix` | Rule-based only — no `--llm` option |

### Tip: mix rule-based and LLM stages

You do not have to use LLM for every stage. For example, use the LLM only for analysis (the hardest extraction step) and keep plan + build-schema rule-based:

```bash
presentation-tool analyze ./docs --output analysis.json --llm claude
presentation-tool plan    analysis.json --output outline.json          # rule-based
presentation-tool build-schema outline.json --theme theme.yaml --output slides.json  # rule-based
```

---

## Tips

**Re-render without re-running the pipeline**

Edit `slides.json` in any text editor, then:

```bash
presentation-tool render slides.json --theme theme.yaml --output presentation.pptx
```

**Iterate on a single slide**

Change only the relevant `slide_id` block in `slides.json` and re-render. The full pipeline does not need to run again.

**Use the review JSON for scripted fixes**

`review_report.json` lists every issue with its `auto_fixable` flag. Feed it to `autofix`, then inspect the remaining unfixable issues in `review_report.md`.

**Ollama: no API key needed**

Ollama runs models locally. Install Ollama, pull a model, then:

```bash
ollama pull mistral
presentation-tool analyze ./docs --output analysis.json --llm ollama --model mistral
```
