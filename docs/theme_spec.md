# Theme Specification

Themes control the visual appearance of every rendered slide: colors, fonts, margins,
footer, chart defaults, and rule-based quality constraints.

Themes are loaded by `ThemeLoader` and produce a `ThemeConfig` object consumed by
`PPTXRenderer`, `SlideSchemaGenerator`, and `SlideReviewer`.

---

## Supported Formats

| Extension | Format |
|---|---|
| `.yaml` / `.yml` | YAML (recommended) |
| `.json` | JSON |

Load a theme:

```bash
pptxforgekit init-theme --output my_theme.yaml   # scaffold a starter file
```

```python
from pptxforgekit.theme.loader import ThemeLoader
theme = ThemeLoader().load("themes/default.yaml")
```

---

## Full YAML Reference

```yaml
name: my_theme          # required; free-text label

# ── Colors ────────────────────────────────────────────────────────────────────
colors:
  primary:    "#1F3864"  # headings, title text, table header background
  secondary:  "#2F75B6"  # secondary accents
  accent:     "#ED7D31"  # highlights, callouts
  background: "#FFFFFF"  # slide background
  text:       "#000000"  # body text
  text_light: "#595959"  # captions, footer text

# ── Fonts ─────────────────────────────────────────────────────────────────────
fonts:
  title_font:   Calibri   # font family for title / subtitle elements
  body_font:    Calibri   # font family for body / caption elements
  title_size:   36        # pt — cover slide title
  heading_size: 28        # pt — section slide titles
  body_size:    20        # pt — bullet body text
  caption_size: 14        # pt — captions, figure labels, footer
  min_size:     12        # pt — absolute minimum; reviewer flags below this

# ── Margins ───────────────────────────────────────────────────────────────────
margins:
  top:    1.5   # cm — used by reviewer overlap checks
  bottom: 1.5
  left:   2.0
  right:  2.0

# ── Footer ────────────────────────────────────────────────────────────────────
footer:
  show_page_number: true   # render slide number in the footer area
  show_date:        false  # render today's date
  custom_text:      ""     # static text shown on every slide; overrides date/number

# ── Chart defaults ────────────────────────────────────────────────────────────
chart_style:
  preferred_type: bar        # default chart type when generator picks one automatically
                             # one of: bar | line | scatter | pie
  color_sequence:            # series colors applied in order; cycles if more series exist
    - "#2F75B6"
    - "#ED7D31"
    - "#A9D18E"
    - "#FF0000"
    - "#9E480E"
  show_legend:      true
  show_data_labels: false
  label_style:      outside_end   # data label position (outside_end | inside_end | center)

# ── Quality rules ─────────────────────────────────────────────────────────────
rules:
  - rule_type: max_bullets        # reviewer flags slides with more bullet points than this
    value: 6
  - rule_type: min_font_size      # reviewer flags text elements below this point size
    value: 12
  - rule_type: max_text_chars     # reviewer flags body elements with more characters
    value: 400
```

---

## Field Reference

### `colors`

All values are hex color strings (`#RRGGBB`). All six keys are optional; unspecified
keys fall back to the defaults shown above.

| Key | Used for |
|---|---|
| `primary` | Title text, table header background, figure labels |
| `secondary` | Secondary accent elements |
| `accent` | Callouts, highlights |
| `background` | Slide background (`_set_background` in renderer) |
| `text` | Default body text color |
| `text_light` | Captions, footer, secondary text |

### `fonts`

| Key | Type | Default | Description |
|---|---|---|---|
| `title_font` | string | `"Calibri"` | Font family for `role: title` and `role: subtitle` |
| `body_font` | string | `"Calibri"` | Font family for all other roles |
| `title_size` | int | `36` | Cover slide title size (pt) |
| `heading_size` | int | `28` | Section slide title size (pt) |
| `body_size` | int | `20` | Bullet body text (pt) |
| `caption_size` | int | `14` | Captions, figure labels, footer (pt) |
| `min_size` | int | `12` | Reviewer minimum; AutoFixer raises below this |

Font families must be installed on the system where PowerPoint opens the file.
Calibri and Arial are safe cross-platform choices.

### `margins`

Margins (cm) are used by the reviewer's overlap and clipping checks as the expected
"safe zone". They do not directly constrain element positions — elements can be placed
anywhere within the 33.87 × 19.05 cm canvas.

### `footer`

The footer is rendered in the bottom strip (`y ≈ 17.85 cm`) on every slide.
`footer_override` in a `SlideSchema` supersedes these settings for that slide only.

### `chart_style`

| Key | Values | Description |
|---|---|---|
| `preferred_type` | `bar`, `line`, `scatter`, `pie` | Default when generator picks automatically |
| `color_sequence` | list of hex strings | Applied per-series in order; cycles |
| `show_legend` | bool | Default legend visibility |
| `show_data_labels` | bool | Default data label visibility |
| `label_style` | `outside_end`, `inside_end`, `center` | Data label position |

Per-element overrides in `ChartElement.series_colors`, `show_data_labels`, etc. take
precedence over these theme defaults.

### `rules`

Rules are read by `SlideReviewer` and `AutoFixer`. Any `rule_type` string is valid;
the built-in checks recognise:

| `rule_type` | Checked by | Effect |
|---|---|---|
| `max_bullets` | `text_check.py` | Flags slides with more bullet points |
| `min_font_size` | `text_check.py` | Flags and auto-fixes text below this size |
| `max_text_chars` | `text_check.py` | Flags high character-count body elements |

Custom rules are stored and can be queried via `theme.get_rule("my_rule")` or
`theme.get_rule_value("my_rule", default=None)`.

---

## Minimal Theme

Only `name` is required. All other fields fall back to defaults:

```yaml
name: minimal
colors:
  primary: "#003366"
```

---

## JSON Format

The JSON format mirrors the YAML structure exactly:

```json
{
  "name": "json_theme",
  "colors": { "primary": "#FF0000" },
  "fonts": { "title_size": 40 }
}
```
