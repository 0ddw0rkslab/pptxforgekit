# Slide Schema Specification

Version: **1.1** (`schema_version` field in every schema file)

The slide schema is the central intermediate representation (IR) of the pipeline.
PPTX is never generated directly from raw input — all rendering decisions flow through this JSON document.

---

## Top-level Structure

```json
{
  "schema_version": "1.1",
  "presentation": { ... },
  "slides": [ ... ]
}
```

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Must be `"1.1"`. Bump when the format changes. |
| `presentation` | `PresentationMeta` | Deck-level metadata |
| `slides` | `SlideSchema[]` | Ordered list of slides |

---

## `PresentationMeta`

```json
{
  "title": "My Presentation",
  "presentation_type": "research",
  "theme_file": "themes/default.yaml",
  "total_slides": 10,
  "generated_at": "2026-06-01T00:00:00Z",
  "author": "Jane Smith",
  "description": ""
}
```

| Field | Type | Notes |
|---|---|---|
| `title` | `string` | Required, non-empty |
| `presentation_type` | `string` | `"research"` (MVP); future: `"business"`, `"proposal"` |
| `theme_file` | `string` | Path to the theme file, relative to the schema file |
| `total_slides` | `int >= 0` | Must equal `len(slides)` — validated on load |
| `generated_at` | `string` | ISO 8601 timestamp |
| `author` | `string \| null` | Optional |
| `description` | `string` | Optional free text |

---

## `SlideSchema`

```json
{
  "slide_id": "s001",
  "slide_number": 1,
  "section": "cover",
  "title": "Background",
  "key_message": "Prior work fails on dataset Y.",
  "layout_type": "title_content",
  "background_color": null,
  "footer_override": null,
  "text_elements": [ ... ],
  "chart_elements": [ ... ],
  "image_elements": [ ... ],
  "table_elements": [ ... ],
  "speaker_note": "...",
  "validation_metadata": { ... }
}
```

| Field | Type | Notes |
|---|---|---|
| `slide_id` | `string` | Unique across the deck, e.g. `"s001"` |
| `slide_number` | `int >= 0` | Display order, informational only |
| `section` | `string` | Section name: `"cover"`, `"background"`, `"results"`, etc. |
| `title` | `string` | Slide title as rendered |
| `key_message` | `string` | One-sentence takeaway; used in speaker notes and review |
| `layout_type` | `string` | See [Layout Types](#layout-types) |
| `background_color` | `string \| null` | Hex `"#RRGGBB"` override; `null` = use theme |
| `footer_override` | `string \| null` | Per-slide footer text; `null` = use theme footer |
| `speaker_note` | `string` | Presenter view text |

All `element_id` values within a slide must be unique across all element types.

---

## Layout Types

| `layout_type` | Description | Default slots |
|---|---|---|
| `cover` | Title page | `title`, `subtitle` |
| `title_only` | Title bar, blank body | `title` |
| `title_content` | Title + full-width body | `title`, `body` |
| `two_column` | Title + left/right columns | `title`, `body_left`, `body_right` |
| `title_chart` | Title + chart | `title`, `chart` |
| `title_table` | Title + table | `title`, `table` |
| `title_image` | Title + centred image | `title`, `image` |
| `blank` | No reserved slots | — |

Default slot positions (in cm) are defined in `renderer/layout_engine.py`.
Explicit `position` values in the schema override these defaults.

---

## `Position`

All element positions use **centimetres** (matching `python-pptx` `Cm()` units).
The widescreen slide canvas is **33.87 × 19.05 cm**.

```json
{ "x": 2.0, "y": 3.2, "w": 29.87, "h": 14.35 }
```

| Field | Constraint | Description |
|---|---|---|
| `x` | `>= 0` | Left edge from slide left |
| `y` | `>= 0` | Top edge from slide top |
| `w` | `> 0` | Width |
| `h` | `> 0` | Height |

---

## `TextElement`

```json
{
  "element_id": "s001_title",
  "role": "title",
  "content": "Background",
  "position": { "x": 2.0, "y": 0.5, "w": 29.87, "h": 2.0 },
  "style": {
    "font_size": 28,
    "bold": true,
    "italic": false,
    "underline": false,
    "color": "#1F3864",
    "align": "left"
  },
  "z_index": 0
}
```

| Field | Type | Notes |
|---|---|---|
| `role` | `string` | One of: `title`, `subtitle`, `body`, `caption`, `footer`, `label` |
| `content` | `string` | Use `\n` for line breaks; `•` for bullets |
| `style.font_size` | `int` (6–200) | Points |
| `style.align` | `string` | `left`, `center`, `right`, `justify` |
| `style.color` | `string \| null` | Hex `"#RRGGBB"`; `null` = theme text color |
| `z_index` | `int >= 0` | Render order; higher = on top |

---

## `ChartElement`

All charts are **PowerPoint-native** (`python-pptx` Chart objects). Never embed images.

```json
{
  "element_id": "s003_chart",
  "chart_type": "bar",
  "data_source": "results.csv",
  "data_inline": null,
  "x_column": "method",
  "y_columns": ["accuracy"],
  "title": "Accuracy by Method",
  "x_label": "Method",
  "y_label": "Accuracy",
  "y_unit": "(%)",
  "value_min": null,
  "value_max": null,
  "number_format": "0.0%",
  "series_colors": ["#2F75B6"],
  "show_data_labels": true,
  "stacked": false,
  "bar_direction": "vertical",
  "legend_position": "right",
  "position": { "x": 2.5, "y": 3.2, "w": 29.37, "h": 14.35 }
}
```

| Field | Type | Notes |
|---|---|---|
| `chart_type` | `string` | `bar`, `line`, `scatter`, `pie` |
| `data_source` | `string` | Path to CSV/XLSX, relative to schema file |
| `data_inline` | `list \| null` | Inline row records; used when no file is available |
| `x_column` | `string \| null` | Category column; `null` = auto-select first column |
| `y_columns` | `string[]` | Value columns; `[]` = auto-select all numeric columns |
| `bar_direction` | `string` | `"vertical"` (columns) or `"horizontal"` (bars) |
| `stacked` | `bool` | Stacked bar or stacked line |
| `legend_position` | `string` | `right`, `bottom`, `top`, `left`, `none` |
| `number_format` | `string` | Excel format string, e.g. `"0.0%"`, `"#,##0"` |

Either `data_source` or `data_inline` must be provided — both absent is a validation error.

---

## `ImageElement`

```json
{
  "element_id": "s004_img",
  "file_path": "figures/result_plot.png",
  "caption": "Figure 1: Accuracy curves.",
  "alt_text": "Line graph showing training and validation accuracy.",
  "figure_label": "(A)",
  "fit_mode": "fit",
  "position": { "x": 6.0, "y": 3.2, "w": 21.87, "h": 13.0 },
  "z_index": 0
}
```

| Field | Notes |
|---|---|
| `file_path` | Absolute, or relative to schema file directory |
| `fit_mode` | `fit` (letterbox), `fill` (crop to fill), `crop` |
| `figure_label` | Panel label rendered on the image, e.g. `"(A)"` |

---

## `TableElement`

```json
{
  "element_id": "s005_tbl",
  "headers": ["Method", "Accuracy", "F1"],
  "rows": [
    ["Baseline", "0.82", "0.80"],
    ["Ours", "0.91", "0.89"]
  ],
  "caption": "Table 1: Main results.",
  "column_widths": [10.0, 10.0, 9.87],
  "position": { "x": 2.0, "y": 3.2, "w": 29.87, "h": 14.35 }
}
```

- `rows` cell count per row must equal `len(headers)`.
- `column_widths` length must equal `len(headers)` when provided.

---

## `ValidationMetadata`

Tracks authorship and review state. Updated by each pipeline stage.

```json
{
  "created_at": "2026-06-01T00:00:00Z",
  "last_modified": "2026-06-01T00:00:00Z",
  "schema_version": "1.1",
  "status": "draft",
  "slide_version": 1,
  "author": null,
  "is_locked": false,
  "reviewer_flags": []
}
```

| Field | Notes |
|---|---|
| `status` | `draft` → `review` → `approved` |
| `is_locked` | `true` prevents AutoFixer from touching this slide |
| `reviewer_flags` | Free-text strings left by the reviewer |

---

## Validation Rules (enforced on load)

- `presentation.total_slides` must equal `len(slides)`
- All `slide_id` values must be unique
- Within each slide, all `element_id` values must be unique across all element types
- Hex color strings must match `#RRGGBB`
- `series_names` length must equal `y_columns` length when non-empty
- `column_widths` length must equal `headers` length when provided
- Either `data_source` or `data_inline` must be present in every `ChartElement`

---

## Loading and Saving

```python
from presentation_tool.models.schema import PresentationSchema

# Load from file
schema = PresentationSchema.from_file("slides.json")

# Save to file
schema.write("slides_fixed.json")

# Serialise to string
json_str = schema.to_json()
```
