# Extending with LLM Backends

The pipeline has three interface points designed for LLM-backed drop-in replacements.
Each interface lives in `src/presentation_tool/interfaces/` and uses `abc.ABC`.

The rule-based MVP implementations can be swapped out without touching any other module.

---

## Interface Points

```
IContentAnalyzer      ← DocumentAnalyzer (rule-based MVP)
                      ← LLMContentAnalyzer (future)

IStorylinePlanner     ← RuleBasedStorylinePlanner (rule-based MVP)
                      ← LLMStorylinePlanner (future)

ISlideSchemaGenerator ← RuleBasedSchemaGenerator (rule-based MVP)
                      ← LLMSchemaGenerator (future)
```

---

## Interface Contracts

### `IContentAnalyzer`

```python
# interfaces/analyzer.py
class IContentAnalyzer(ABC):
    @abstractmethod
    def analyze(self, input_path: Path) -> AnalysisResult: ...
```

Input: a file or directory path.  
Output: `AnalysisResult` — structured representation of the source documents.

### `IStorylinePlanner`

```python
# interfaces/planner.py
class IStorylinePlanner(ABC):
    @abstractmethod
    def plan(self, analysis: AnalysisResult, presentation_type: str) -> StorylineOutline: ...
```

Input: `AnalysisResult` and a presentation type string (e.g. `"research"`).  
Output: `StorylineOutline` — ordered list of slide outlines with section, title, layout, and content hints.

### `ISlideSchemaGenerator`

```python
# interfaces/generator.py
class ISlideSchemaGenerator(ABC):
    @abstractmethod
    def generate(self, outline: StorylineOutline, theme: ThemeConfig) -> PresentationSchema: ...
```

Input: `StorylineOutline` and a loaded `ThemeConfig`.  
Output: `PresentationSchema` — complete, render-ready JSON schema.

---

## Implementing an LLM Backend

### Step 1 — Add the `anthropic` dependency

```toml
# pyproject.toml
[project.optional-dependencies]
llm = ["anthropic>=0.40"]
```

Install with:

```bash
pip install "presentation-tool[llm]"
```

### Step 2 — Implement the interface

```python
# presentation_tool/analyzer/llm_analyzer.py
from __future__ import annotations

import anthropic
from pathlib import Path

from presentation_tool.interfaces.analyzer import IContentAnalyzer
from presentation_tool.models.analysis import AnalysisResult


class LLMContentAnalyzer(IContentAnalyzer):
    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic.Anthropic()
        self._model = model

    def analyze(self, input_path: Path) -> AnalysisResult:
        text = input_path.read_text(encoding="utf-8")

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # cache the long prompt
                }
            ],
            messages=[{"role": "user", "content": text}],
        )

        # Parse the structured JSON response into AnalysisResult
        import json
        data = json.loads(response.content[0].text)
        return AnalysisResult(**data)
```

### Step 3 — Wire it in via CLI or pipeline

```python
# Use the LLM analyzer instead of the rule-based one
from presentation_tool.analyzer.llm_analyzer import LLMContentAnalyzer

analyzer = LLMContentAnalyzer()
analysis = analyzer.analyze(Path("input_docs/"))
```

The rest of the pipeline (`StorylinePlanner`, `SlideSchemaGenerator`, `PPTXRenderer`)
is unchanged — it only depends on `AnalysisResult`, not on how it was produced.

---

## Prompt Caching

When sending long documents or system prompts to the Claude API, enable prompt caching
to reduce latency and cost on repeated calls.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    system=[
        {
            "type": "text",
            "text": LONG_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ],
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": document_text,
                    "cache_control": {"type": "ephemeral"},  # cache the document too
                },
                {
                    "type": "text",
                    "text": "Extract the structure as described above.",
                },
            ],
        }
    ],
)
```

Cache hits are reported in `response.usage.cache_read_input_tokens`.
The cache TTL is 5 minutes; re-use the same `system` block across calls to benefit.

---

## Design Notes

**Why duck typing, not inheritance?**

Concrete implementations do not inherit from the interface classes. They are registered
at construction time via duck typing. This avoids circular imports between the
`interfaces/` package and any implementation package that might depend on models from
`presentation_tool.models`.

The only requirement is that the public method signature matches the abstract method.

**Why keep interfaces thin?**

The interface has one method per stage. Construction-time configuration (API keys,
model names, temperature) is handled in `__init__`, not via method parameters.
This keeps the pipeline orchestrator simple:

```python
analyzer  = LLMContentAnalyzer(model="claude-opus-4-8")
planner   = RuleBasedStorylinePlanner()    # mix and match
generator = LLMSchemaGenerator()

analysis = analyzer.analyze(input_path)
outline  = planner.plan(analysis, "research")
schema   = generator.generate(outline, theme)
```

---

## Suggested Prompt Structure

For `LLMSchemaGenerator`, structure the prompt to return a JSON object that validates
against `PresentationSchema`. Pin the schema version and include a few-shot example
to reduce formatting errors.

```python
SCHEMA_SYSTEM_PROMPT = f"""
You are a presentation designer. Given a StorylineOutline, produce a JSON object
that conforms to the SlideSchema specification version 1.1.

Rules:
- Every slide must have a unique slide_id (s001, s002, …)
- chart_type must be one of: bar, line, scatter, pie
- All positions are in centimetres (slide is 33.87 × 19.05 cm)
- Return only the JSON object — no prose, no markdown fences

Schema spec: {SCHEMA_SPEC_TEXT}
"""
```

Attach `SCHEMA_SPEC_TEXT` (contents of `docs/slide_schema_spec.md`) with
`cache_control: ephemeral` so it is cached across calls.
