from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from presentation_tool import __version__

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("presentation_tool.cli")

# ── LLM helpers ───────────────────────────────────────────────────────────────

def _model_help() -> str:
    from presentation_tool.llm.registry import DEFAULT_MODELS, KNOWN_MODELS
    # \b tells Click to stop reflowing this paragraph (preserves indentation)
    lines = [
        "\b",
        "Model ID for the chosen --llm provider (* = default):",
    ]
    for provider, models in KNOWN_MODELS.items():
        default = DEFAULT_MODELS[provider]
        model_strs = [f"{m}*" if m == default else m for m in models]
        lines.append(f"  {provider:8s}: {', '.join(model_strs)}")
    return "\n".join(lines)


_LLM_OPTION = click.option(
    "--llm",
    "llm_provider",
    default=None,
    type=click.Choice(["claude", "gpt", "gemini", "ollama"], case_sensitive=False),
    help="Use an LLM backend instead of the rule-based engine.",
    show_default=False,
)
_MODEL_OPTION = click.option(
    "--model",
    "llm_model",
    default=None,
    help=_model_help(),
)


def _load_provider(llm_provider: str | None, llm_model: str | None):
    """Return an LLMProvider if --llm is specified, else None."""
    if llm_provider is None:
        return None
    try:
        # Load .env if python-dotenv is available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        from presentation_tool.llm.registry import build_provider
        return build_provider(llm_provider, model=llm_model)
    except Exception as exc:
        _fail(str(exc))


def _fail(msg: str) -> None:
    click.echo(f"Error: {msg}", err=True)
    sys.exit(1)


@click.group()
@click.version_option(__version__, prog_name="presentation-tool")
def main() -> None:
    """Pipeline-based presentation generation tool."""


# ──────────────────────────────────────────────────────────────────────────────
# init-theme
# ──────────────────────────────────────────────────────────────────────────────
@main.command("init-theme")
@click.option("--output", "-o", default="theme.yaml", show_default=True,
              help="Output path for the starter theme file")
def init_theme(output: str) -> None:
    """Create a starter theme.yaml with default values."""
    from presentation_tool.theme.loader import default_theme_yaml

    out = Path(output)
    if out.exists():
        click.confirm(f"{out} already exists. Overwrite?", abort=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(default_theme_yaml(), encoding="utf-8")
    click.echo(f"Theme written to: {out}")


# ──────────────────────────────────────────────────────────────────────────────
# analyze
# ──────────────────────────────────────────────────────────────────────────────
@main.command("analyze")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="Output path for analysis.json")
@_LLM_OPTION
@_MODEL_OPTION
def analyze(input_path: str, output: str, llm_provider: str | None, llm_model: str | None) -> None:
    """Analyze input documents and produce analysis.json.

    Add --llm <provider> to use an LLM for richer extraction.
    """
    from presentation_tool.exceptions import AnalysisError

    provider = _load_provider(llm_provider, llm_model)

    try:
        if provider is not None:
            from presentation_tool.llm.analyzer import LLMContentAnalyzer
            analyzer = LLMContentAnalyzer(provider)
            click.echo(f"Using LLM: {provider.provider_name}/{provider.model}")
        else:
            from presentation_tool.analyzer.document import DocumentAnalyzer
            analyzer = DocumentAnalyzer()

        result = analyzer.analyze(Path(input_path))
    except AnalysisError as exc:
        _fail(str(exc))
        return

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Analysis written to: {out}")
    click.echo(f"  Title: {result.title}")
    click.echo(f"  Sections: {len(result.sections)}")
    click.echo(f"  Data files: {len(result.data_files)}")


# ──────────────────────────────────────────────────────────────────────────────
# plan
# ──────────────────────────────────────────────────────────────────────────────
@main.command("plan")
@click.argument("analysis_json", type=click.Path(exists=True))
@click.option("--type", "presentation_type", default="research", show_default=True,
              help="Presentation type [research]")
@click.option("--output", "-o", required=True, help="Output path for outline.json")
@_LLM_OPTION
@_MODEL_OPTION
def plan(
    analysis_json: str,
    presentation_type: str,
    output: str,
    llm_provider: str | None,
    llm_model: str | None,
) -> None:
    """Generate a storyline outline from analysis.json.

    Add --llm <provider> to let an LLM craft the narrative arc.
    """
    from presentation_tool.models.analysis import AnalysisResult
    from presentation_tool.exceptions import PlanningError

    analysis = AnalysisResult.model_validate_json(
        Path(analysis_json).read_text(encoding="utf-8")
    )

    provider = _load_provider(llm_provider, llm_model)

    try:
        if provider is not None:
            from presentation_tool.llm.planner import LLMStorylinePlanner
            planner = LLMStorylinePlanner(provider)
            click.echo(f"Using LLM: {provider.provider_name}/{provider.model}")
        else:
            from presentation_tool.planner.storyline import RuleBasedStorylinePlanner
            planner = RuleBasedStorylinePlanner()

        outline = planner.plan(analysis, presentation_type)
    except PlanningError as exc:
        _fail(str(exc))
        return

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(outline.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Outline written to: {out}")
    click.echo(f"  Slides: {outline.total_slides}")


# ──────────────────────────────────────────────────────────────────────────────
# build-schema
# ──────────────────────────────────────────────────────────────────────────────
@main.command("build-schema")
@click.argument("outline_json", type=click.Path(exists=True))
@click.option("--theme", "theme_file", required=True, type=click.Path(exists=True),
              help="Theme YAML or JSON file")
@click.option("--output", "-o", required=True, help="Output path for slides.json")
@_LLM_OPTION
@_MODEL_OPTION
def build_schema(
    outline_json: str,
    theme_file: str,
    output: str,
    llm_provider: str | None,
    llm_model: str | None,
) -> None:
    """Generate a slide schema JSON from outline.json + theme.

    Add --llm <provider> to let an LLM fill in the slide content.
    """
    from presentation_tool.models.outline import StorylineOutline
    from presentation_tool.theme.loader import ThemeLoader
    from presentation_tool.exceptions import SchemaGenerationError, ThemeLoadError

    try:
        theme = ThemeLoader().load(Path(theme_file))
    except ThemeLoadError as exc:
        _fail(str(exc))
        return

    outline = StorylineOutline.model_validate_json(
        Path(outline_json).read_text(encoding="utf-8")
    )

    provider = _load_provider(llm_provider, llm_model)

    try:
        if provider is not None:
            from presentation_tool.llm.generator import LLMSchemaGenerator
            generator = LLMSchemaGenerator(provider)
            click.echo(f"Using LLM: {provider.provider_name}/{provider.model}")
        else:
            from presentation_tool.schema.generator import RuleBasedSchemaGenerator
            generator = RuleBasedSchemaGenerator()

        schema = generator.generate(outline, theme)
    except SchemaGenerationError as exc:
        _fail(str(exc))
        return

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    schema.write(out)
    click.echo(f"Schema written to: {out}")
    click.echo(f"  Slides: {len(schema.slides)}")


# ──────────────────────────────────────────────────────────────────────────────
# render
# ──────────────────────────────────────────────────────────────────────────────
@main.command("render")
@click.argument("schema_json", type=click.Path(exists=True))
@click.option("--theme", "theme_file", required=True, type=click.Path(exists=True),
              help="Theme YAML or JSON file")
@click.option("--output", "-o", required=True, help="Output path for .pptx file")
def render(schema_json: str, theme_file: str, output: str) -> None:
    """Render a slide schema JSON into a .pptx file."""
    from presentation_tool.models.schema import PresentationSchema
    from presentation_tool.renderer.pptx import PPTXRenderer
    from presentation_tool.theme.loader import ThemeLoader
    from presentation_tool.exceptions import RenderError, ThemeLoadError

    try:
        theme = ThemeLoader().load(Path(theme_file))
    except ThemeLoadError as exc:
        _fail(str(exc))
        return

    schema = PresentationSchema.from_file(schema_json)

    out = Path(output)
    try:
        PPTXRenderer(theme).render(schema, out, base_path=Path(schema_json).parent)
    except RenderError as exc:
        _fail(str(exc))
        return

    click.echo(f"PPTX written to: {out}")


# ──────────────────────────────────────────────────────────────────────────────
# review
# ──────────────────────────────────────────────────────────────────────────────
@main.command("review")
@click.argument("pptx_file", type=click.Path(exists=True))
@click.argument("schema_json", type=click.Path(exists=True))
@click.option("--theme", "theme_file", type=click.Path(exists=True), default=None,
              help="Theme YAML/JSON (optional, uses defaults if omitted)")
@click.option("--output", "-o", required=True,
              help="Output path (use .json or .md extension)")
def review(pptx_file: str, schema_json: str, theme_file: str | None, output: str) -> None:
    """Review a rendered PPTX against its schema and write a report."""
    from presentation_tool.models.schema import PresentationSchema
    from presentation_tool.reviewer.slide import SlideReviewer
    from presentation_tool.theme.loader import ThemeLoader
    from presentation_tool.models.theme import ThemeConfig

    schema = PresentationSchema.from_file(schema_json)
    theme: ThemeConfig
    if theme_file:
        theme = ThemeLoader().load(Path(theme_file))
    else:
        theme = ThemeConfig()

    report = SlideReviewer().review(
        schema,
        Path(pptx_file),
        Path(schema_json),
        theme,
    )

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.suffix == ".json":
        report.write_json(out)
    else:
        report.write_markdown(out)

    click.echo(f"Review report written to: {out}")
    click.echo(f"  Total issues: {report.total_issues}")
    for sev in ("critical", "high", "medium", "low"):
        count = report.summary.get(sev, 0)
        if count:
            click.echo(f"    {sev.upper()}: {count}")


# ──────────────────────────────────────────────────────────────────────────────
# autofix
# ──────────────────────────────────────────────────────────────────────────────
@main.command("autofix")
@click.argument("schema_json", type=click.Path(exists=True))
@click.argument("review_json", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="Output path for fixed slides JSON")
def autofix(schema_json: str, review_json: str, output: str) -> None:
    """Auto-fix schema issues identified in a review report."""
    from presentation_tool.fixer.auto import AutoFixer
    from presentation_tool.models.review import ReviewReport
    from presentation_tool.models.schema import PresentationSchema

    schema = PresentationSchema.from_file(schema_json)
    report = ReviewReport.from_file(review_json)

    result = AutoFixer().fix(
        schema,
        report,
        source_schema_file=schema_json,
        source_report_file=review_json,
    )

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.fixed_schema.write(out)
    click.echo(f"Fixed schema written to: {out}")
    click.echo(f"  Applied fixes:    {result.n_fixed}")
    click.echo(f"  Remaining issues: {result.n_remaining}")
    if result.split_suggestions:
        click.echo(
            f"  Split suggestions: {len(result.split_suggestions)} "
            f"(review review_report for details)"
        )


# ──────────────────────────────────────────────────────────────────────────────
# llm-info
# ──────────────────────────────────────────────────────────────────────────────
@main.command("llm-info")
def llm_info() -> None:
    """Show available LLM providers and their supported models."""
    from presentation_tool.llm.registry import PROVIDER_NAMES, DEFAULT_MODELS

    click.echo("Available LLM providers\n")
    provider_models: dict[str, list[str]] = {
        "claude": [
            "claude-opus-4-8           (most capable)",
            "claude-sonnet-4-6         (default - balanced)",
            "claude-haiku-4-5-20251001 (fastest)",
        ],
        "gpt": [
            "gpt-4o               (default - best)",
            "gpt-4o-mini          (fast, cheap)",
            "gpt-4-turbo",
            "o1",
            "o3-mini",
        ],
        "gemini": [
            "gemini-2.0-flash     (default - free tier available)",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        "ollama": [
            "llama3.2             (default - no API key needed)",
            "llama3.1:70b",
            "mistral",
            "qwen2.5",
            "phi4",
            "gemma2",
            "deepseek-r1",
            "...any model you have pulled",
        ],
    }
    env_vars = {
        "claude": "ANTHROPIC_API_KEY",
        "gpt": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "ollama": "(none - runs locally via Ollama)",
    }
    install_extras = {
        "claude": "pip install 'presentation-tool[llm-claude]'",
        "gpt": "pip install 'presentation-tool[llm-openai]'",
        "gemini": "pip install 'presentation-tool[llm-gemini]'",
        "ollama": "pip install 'presentation-tool[llm-ollama]'",
    }

    for name in PROVIDER_NAMES:
        click.echo(f"  {name}")
        click.echo(f"    Default model : {DEFAULT_MODELS[name]}")
        click.echo(f"    API key env   : {env_vars[name]}")
        click.echo(f"    Install       : {install_extras[name]}")
        click.echo("    Models:")
        for m in provider_models.get(name, []):
            click.echo(f"      - {m}")
        click.echo()

    click.echo("Usage examples:")
    click.echo("  presentation-tool analyze ./docs -o analysis.json --llm claude")
    click.echo("  presentation-tool analyze ./docs -o analysis.json --llm gpt --model gpt-4o-mini")
    click.echo("  presentation-tool plan analysis.json -o outline.json --llm gemini")
    click.echo("  presentation-tool build-schema outline.json --theme theme.yaml -o slides.json --llm ollama --model mistral")
