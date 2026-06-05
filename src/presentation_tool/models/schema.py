from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CURRENT_SCHEMA_VERSION = "1.1"

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

SLIDE_W_CM = 33.87
SLIDE_H_CM = 19.05


def _check_hex_color(value: str | None, field_label: str = "color") -> str | None:
    """Validate a hex color string and normalise to upper-case."""
    if value is None:
        return None
    if not _HEX_COLOR_RE.match(value):
        raise ValueError(
            f"'{value}' is not a valid hex color for {field_label}. "
            f"Use '#RRGGBB' format (e.g. '#1F3864')."
        )
    return value.upper()


# ─────────────────────────────── Position ────────────────────────────────────


class Position(BaseModel):
    """Bounding box for a slide element, in centimetres.

    Origin is the top-left corner of the slide.
    Widescreen slide bounds: width = 33.87 cm, height = 19.05 cm.
    """

    x: float = Field(..., ge=0.0, description="Left edge (cm from slide left)")
    y: float = Field(..., ge=0.0, description="Top edge (cm from slide top)")
    w: float = Field(..., gt=0.0, description="Width in cm (must be > 0)")
    h: float = Field(..., gt=0.0, description="Height in cm (must be > 0)")


# ───────────────────────────── TextStyle ─────────────────────────────────────


class TextStyle(BaseModel):
    """Reusable text formatting style.

    Separating style from content lets the schema generator and the renderer
    stay decoupled: the generator decides *what* text to show; the style block
    says *how* it looks.
    """

    font_size: int = Field(18, ge=6, le=200, description="Font size in points")
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str | None = Field(None, description="Hex color string, e.g. '#1F3864'")
    align: Literal["left", "center", "right", "justify"] = "left"

    @field_validator("color", mode="before")
    @classmethod
    def _check_color(cls, v: Any) -> Any:
        return _check_hex_color(v, "TextStyle.color")


# ─────────────────────────── TextElement ─────────────────────────────────────


class TextElement(BaseModel):
    """A text box placed on a slide."""

    element_id: str = Field(..., min_length=1, description="Unique within the slide")
    role: Literal["title", "subtitle", "body", "caption", "footer", "label"]
    content: str = Field(
        ..., min_length=1, description="Text content; use \\n for line breaks"
    )
    position: Position
    style: TextStyle = Field(default_factory=TextStyle)
    z_index: int = Field(0, ge=0, description="Rendering order; higher = on top")


# ─────────────────────────── ChartElement ────────────────────────────────────


class ChartElement(BaseModel):
    """A PowerPoint-native chart (editable data in PPT, never an image).

    All chart data remains editable in PowerPoint after rendering.
    Use ``bar_direction="horizontal"`` for horizontal bar charts.
    Use ``stacked=True`` for stacked bar or stacked line variants.
    """

    element_id: str = Field(..., min_length=1)
    chart_type: Literal["bar", "line", "scatter", "pie"]

    # ── Data source ───────────────────────────────────────────────────────────
    data_source: str = Field(
        "",
        description=(
            "Path to a CSV, XLSX, or JSON data file. "
            "Can be absolute or relative to the schema file's directory."
        ),
    )
    data_inline: list[dict[str, Any]] | None = Field(
        None,
        description=(
            "Inline data as a list of row records (used when no data file is available). "
            'E.g. [{"method": "A", "accuracy": 0.91}, {"method": "B", "accuracy": 0.85}]'
        ),
    )

    # ── Column mapping ────────────────────────────────────────────────────────
    x_column: str | None = Field(
        None,
        description="Column name for categories / X-axis. null = auto-select first column.",
    )
    y_columns: list[str] = Field(
        default_factory=list,
        description=(
            "Column names for Y-axis values. "
            "Empty = auto-select all numeric columns."
        ),
    )

    # ── Labels and titles ─────────────────────────────────────────────────────
    title: str = Field("", description="Chart title displayed above the chart")
    x_label: str = Field("", description="X-axis label")
    y_label: str = Field("", description="Y-axis label")
    y_unit: str = Field(
        "",
        description="Unit string appended to y_label, e.g. '(%)' or '(ms)'",
    )

    # ── Axis scale ────────────────────────────────────────────────────────────
    value_min: float | None = Field(
        None, description="Y-axis minimum value. null = auto-scale."
    )
    value_max: float | None = Field(
        None, description="Y-axis maximum value. null = auto-scale."
    )
    number_format: str = Field(
        "General",
        description=(
            "Excel number format string for Y-axis tick labels. "
            "Common values: 'General', '0.0', '0.0%', '#,##0', '0.00E+00'."
        ),
    )

    # ── Series customisation ──────────────────────────────────────────────────
    series_names: list[str] = Field(
        default_factory=list,
        description=(
            "Display names for each series (overrides column names in legend). "
            "Length must match y_columns when non-empty."
        ),
    )
    series_colors: list[str] = Field(
        default_factory=list,
        description=(
            "Per-series hex color overrides (e.g. ['#1F3864', '#ED7D31']). "
            "Falls back to theme colors for unspecified series."
        ),
    )

    # ── Data labels ───────────────────────────────────────────────────────────
    show_data_labels: bool | None = Field(
        None,
        description="Show data labels on bars/points. null = follow theme setting.",
    )
    data_label_format: str = Field(
        "",
        description=(
            "Number format for data labels. "
            "E.g. '0.0' for one decimal, '0.0%' for percentages. "
            "Empty = inherit number_format."
        ),
    )

    # ── Chart style ───────────────────────────────────────────────────────────
    stacked: bool = Field(
        False,
        description=(
            "Render as stacked variant. "
            "Applies to 'bar' (stacked column / stacked bar) "
            "and 'line' (stacked line with markers)."
        ),
    )
    bar_direction: Literal["vertical", "horizontal"] = Field(
        "vertical",
        description=(
            "'vertical' = column chart (bars point up, default). "
            "'horizontal' = bar chart (bars point right)."
        ),
    )
    legend_position: Literal["right", "bottom", "top", "left", "none"] = Field(
        "right",
        description="Legend placement. 'none' hides the legend.",
    )

    # ── Layout ────────────────────────────────────────────────────────────────
    position: Position
    z_index: int = Field(0, ge=0)

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("series_colors", mode="before")
    @classmethod
    def _check_series_colors(cls, v: list[Any]) -> list[str]:
        result: list[str] = []
        for i, c in enumerate(v):
            validated = _check_hex_color(str(c), f"series_colors[{i}]")
            result.append(validated if validated is not None else str(c))
        return result

    @model_validator(mode="after")
    def _require_data(self) -> ChartElement:
        if not self.data_source and self.data_inline is None:
            raise ValueError(
                f"ChartElement '{self.element_id}': "
                f"provide either 'data_source' (file path) or "
                f"'data_inline' (list of records). Both are currently absent."
            )
        return self

    @model_validator(mode="after")
    def _check_series_names_length(self) -> ChartElement:
        if self.series_names and self.y_columns:
            if len(self.series_names) != len(self.y_columns):
                raise ValueError(
                    f"ChartElement '{self.element_id}': "
                    f"series_names has {len(self.series_names)} entries "
                    f"but y_columns has {len(self.y_columns)} entries. "
                    f"Lengths must match when series_names is provided."
                )
        return self


# ─────────────────────────── ImageElement ────────────────────────────────────


class ImageElement(BaseModel):
    """An image placed on a slide."""

    element_id: str = Field(..., min_length=1)
    file_path: str = Field(
        ...,
        min_length=1,
        description="Absolute path, or path relative to the schema file's directory.",
    )
    caption: str = Field("", description="Caption text shown below the image")
    alt_text: str = Field("", description="Accessibility description of the image")
    figure_label: str = Field(
        "", description="Panel label displayed on the image, e.g. '(A)', 'Figure 1'"
    )
    position: Position
    fit_mode: Literal["fit", "fill", "crop"] = "fit"
    z_index: int = Field(0, ge=0)


# ─────────────────────────── TableElement ────────────────────────────────────


class TableElement(BaseModel):
    """A table placed on a slide."""

    element_id: str = Field(..., min_length=1)
    headers: list[str] = Field(..., min_length=1, description="Column header labels")
    rows: list[list[str]] = Field(default_factory=list)
    caption: str = ""
    position: Position
    column_widths: list[float] | None = Field(
        None,
        description=(
            "Per-column widths in cm. "
            "Length must match headers. "
            "Values must be > 0 and should sum close to position.w."
        ),
    )
    z_index: int = Field(0, ge=0)

    @model_validator(mode="after")
    def _check_row_lengths(self) -> TableElement:
        n = len(self.headers)
        bad = [i for i, row in enumerate(self.rows) if len(row) != n]
        if bad:
            raise ValueError(
                f"TableElement '{self.element_id}': "
                f"row(s) {bad} have the wrong number of cells. "
                f"Expected {n} cell(s) per row (one per header). "
                f"Found lengths: {[len(self.rows[i]) for i in bad]}."
            )
        return self

    @model_validator(mode="after")
    def _check_column_widths(self) -> TableElement:
        if self.column_widths is None:
            return self
        if len(self.column_widths) != len(self.headers):
            raise ValueError(
                f"TableElement '{self.element_id}': "
                f"column_widths has {len(self.column_widths)} entries "
                f"but there are {len(self.headers)} headers. "
                f"Lengths must match."
            )
        if any(w <= 0 for w in self.column_widths):
            raise ValueError(
                f"TableElement '{self.element_id}': "
                f"all column_widths must be > 0."
            )
        return self


# ────────────────────────── ValidationMetadata ───────────────────────────────

SlideStatus = Literal["draft", "review", "approved"]


class ValidationMetadata(BaseModel):
    """Tracks authorship, version, and review state of a slide.

    This block is written by the generator and updated by each pipeline stage.
    Users can set ``is_locked = true`` to prevent auto-fixer from touching a slide.
    """

    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp (auto-set by generator)",
    )
    last_modified: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 last-modified timestamp (updated on every save)",
    )
    schema_version: str = Field(
        CURRENT_SCHEMA_VERSION,
        description="Schema version at the time this slide was generated",
    )
    status: SlideStatus = Field(
        "draft",
        description="Workflow status: draft → review → approved",
    )
    slide_version: int = Field(
        1, ge=1, description="Increments each time the slide is saved / auto-fixed"
    )
    author: str | None = Field(
        None, description="Name or email of the person who last modified this slide"
    )
    is_locked: bool = Field(
        False,
        description=(
            "If true, auto-fixer will skip this slide and reviewer issues "
            "will be reported but not automatically resolved."
        ),
    )
    reviewer_flags: list[str] = Field(
        default_factory=list,
        description="Free-text flags left by the reviewer (e.g. 'data inconsistency in chart')",
    )


# ─────────────────────────── SlideSchema ─────────────────────────────────────


class SlideSchema(BaseModel):
    """Complete specification of a single slide.

    Rendering order within a slide is controlled by ``z_index`` on each element.
    Layout type is a structural hint for the generator; the renderer uses
    explicit element positions regardless of layout type.
    """

    slide_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier across the presentation (e.g. 's001').",
    )
    slide_number: int = Field(
        0,
        ge=0,
        description=(
            "Display order (1-indexed). Informational only — "
            "actual order is determined by position in the slides list."
        ),
    )
    section: str = Field("", description="Section or chapter name")
    title: str = Field(
        ..., min_length=1, description="Slide title as it appears on the slide"
    )
    key_message: str = Field(
        "",
        description=(
            "One-sentence core takeaway. "
            "Used in speaker notes, review checks, and LLM prompts."
        ),
    )
    layout_type: Literal[
        "cover",
        "title_only",
        "title_content",
        "two_column",
        "title_chart",
        "title_table",
        "title_image",
        "blank",
    ]
    background_color: str | None = Field(
        None,
        description=(
            "Per-slide background color override (hex, e.g. '#F0F4FA'). "
            "null = use theme background."
        ),
    )
    footer_override: str | None = Field(
        None,
        description=(
            "Override the footer text for this slide only. "
            "null = use theme footer settings."
        ),
    )
    text_elements: list[TextElement] = Field(default_factory=list)
    chart_elements: list[ChartElement] = Field(default_factory=list)
    image_elements: list[ImageElement] = Field(default_factory=list)
    table_elements: list[TableElement] = Field(default_factory=list)
    speaker_note: str = Field("", description="Speaker notes shown in presenter view")
    validation_metadata: ValidationMetadata = Field(
        default_factory=ValidationMetadata
    )

    @field_validator("background_color", mode="before")
    @classmethod
    def _check_bg_color(cls, v: Any) -> Any:
        return _check_hex_color(v, "SlideSchema.background_color")

    @model_validator(mode="after")
    def _check_unique_element_ids(self) -> SlideSchema:
        all_ids: list[str] = (
            [e.element_id for e in self.text_elements]
            + [e.element_id for e in self.chart_elements]
            + [e.element_id for e in self.image_elements]
            + [e.element_id for e in self.table_elements]
        )
        seen: set[str] = set()
        dupes: list[str] = []
        for eid in all_ids:
            if eid in seen:
                dupes.append(eid)
            seen.add(eid)
        if dupes:
            raise ValueError(
                f"Slide '{self.slide_id}' has duplicate element_id(s): {dupes}. "
                f"Every element on a slide must have a unique element_id."
            )
        return self


# ────────────────────────── PresentationMeta ─────────────────────────────────


class PresentationMeta(BaseModel):
    title: str = Field(..., min_length=1)
    presentation_type: str = "research"
    theme_file: str = ""
    total_slides: int = Field(..., ge=0)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    author: str | None = None
    description: str = ""


# ─────────────────────────── PresentationSchema ──────────────────────────────


class PresentationSchema(BaseModel):
    """Root object for a complete slide deck schema (v1.1).

    A valid schema must satisfy:
    - ``schema_version`` == "1.1"
    - ``presentation.total_slides`` == ``len(slides)``
    - All ``slide_id`` values are unique
    - Within each slide, all ``element_id`` values are unique
    """

    schema_version: str = Field(
        CURRENT_SCHEMA_VERSION,
        description=f"Must be '{CURRENT_SCHEMA_VERSION}'. Bump when the format changes.",
    )
    presentation: PresentationMeta
    slides: list[SlideSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_slide_ids(self) -> PresentationSchema:
        ids = [s.slide_id for s in self.slides]
        seen: set[str] = set()
        dupes: list[str] = []
        for sid in ids:
            if sid in seen:
                dupes.append(sid)
            seen.add(sid)
        if dupes:
            raise ValueError(
                f"Duplicate slide_id(s) in presentation: {dupes}. "
                f"Each slide must have a unique slide_id (e.g. 's001', 's002')."
            )
        return self

    @model_validator(mode="after")
    def _check_total_slides(self) -> PresentationSchema:
        declared = self.presentation.total_slides
        actual = len(self.slides)
        if declared != actual:
            raise ValueError(
                f"presentation.total_slides is {declared} "
                f"but the slides list contains {actual} slide(s). "
                f"Please set total_slides to {actual}."
            )
        return self

    # ── I/O helpers ───────────────────────────────────────────────────────────

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> PresentationSchema:
        return cls.model_validate_json(json_str)

    @classmethod
    def from_file(cls, path: str | Path) -> PresentationSchema:
        raw = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate(json.loads(raw))
        except Exception as exc:
            # Wrap with file path so users know which file caused the error
            raise ValueError(f"Schema file '{path}': {exc}") from exc

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")
