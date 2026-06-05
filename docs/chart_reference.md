# Chart Reference

All charts are PowerPoint-native — the underlying data table stays **editable in PowerPoint** after rendering. No chart images are produced.

---

## Supported Chart Types

| `chart_type` | `bar_direction` | `stacked` | Result |
|---|---|---|---|
| `bar` | `vertical` (default) | `false` | Clustered column chart |
| `bar` | `vertical` | `true` | Stacked column chart |
| `bar` | `horizontal` | `false` | Clustered bar chart |
| `bar` | `horizontal` | `true` | Stacked bar chart |
| `line` | — | `false` | Line with markers |
| `line` | — | `true` | Stacked line with markers |
| `scatter` | — | — | XY scatter (requires numeric X column) |
| `pie` | — | — | Pie chart |

---

## Data Sources

### Inline data (no file required)

Define data directly inside the schema — ideal for hand-crafted or fixed slides:

```json
{
  "element_id": "c001",
  "chart_type": "bar",
  "bar_direction": "vertical",
  "x_column": "method",
  "y_columns": ["accuracy_pct"],
  "series_names": ["Accuracy (%)"],
  "series_colors": ["#1F3864"],
  "title": "Method Comparison",
  "y_label": "Accuracy",
  "y_unit": "(%)",
  "value_min": 70.0,
  "value_max": 100.0,
  "number_format": "0.0",
  "show_data_labels": true,
  "data_label_format": "0.0",
  "legend_position": "none",
  "position": { "x": 2.5, "y": 3.2, "w": 28.87, "h": 14.3 },
  "data_inline": [
    { "method": "Baseline", "accuracy_pct": 82.0 },
    { "method": "Ours",     "accuracy_pct": 91.3 }
  ]
}
```

### File-based data (CSV / XLSX)

```json
{
  "chart_type": "line",
  "data_source": "results/timeseries.csv",
  "x_column": "epoch",
  "y_columns": ["train_loss", "val_loss"],
  "series_names": ["Train Loss", "Val Loss"]
}
```

`data_source` can be an absolute path or a path relative to the `slides.json` file.

---

## ChartElement Field Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `chart_type` | `bar\|line\|scatter\|pie` | required | Chart category |
| `bar_direction` | `vertical\|horizontal` | `vertical` | Column vs. bar orientation |
| `stacked` | bool | `false` | Stacked variant |
| `x_column` | str\|null | `null` | Category column; null = first column |
| `y_columns` | list[str] | `[]` | Value columns; empty = all numeric columns |
| `series_names` | list[str] | `[]` | Display name overrides (one per y column) |
| `series_colors` | list[str] | `[]` | Per-series hex colors, e.g. `["#1F3864"]` |
| `title` | str | `""` | Chart title |
| `x_label` | str | `""` | X-axis label |
| `y_label` | str | `""` | Y-axis label |
| `y_unit` | str | `""` | Unit appended to y_label, e.g. `(%)` |
| `value_min` | float\|null | `null` | Y-axis minimum (null = auto) |
| `value_max` | float\|null | `null` | Y-axis maximum (null = auto) |
| `number_format` | str | `"General"` | Axis tick number format, e.g. `"0.0%"` |
| `show_data_labels` | bool\|null | `null` | null inherits the theme setting |
| `data_label_format` | str | `""` | Data label number format |
| `legend_position` | `right\|bottom\|top\|left\|none` | `right` | Legend placement |
| `data_source` | str | `""` | Path to CSV or XLSX file |
| `data_inline` | list[dict]\|null | `null` | Inline row records (takes priority over `data_source`) |
| `position` | Position | required | `{x, y, w, h}` in centimetres |

---

## Auto Chart Type Recommendation

When you have a DataFrame and are unsure which chart type fits best:

```python
from pptxforgekit.chart.recommender import ChartTypeRecommender
import pandas as pd

df = pd.read_csv("results.csv")
rec = ChartTypeRecommender().recommend(df, x_col="method", y_cols=["accuracy_pct"])
print(f"{rec.chart_type} ({rec.bar_direction}), confidence={rec.confidence:.2f}")
print(rec.reason)
```

Decision rules (in priority order):

- Datetime or epoch X column → **line**
- Numeric X + numeric Y + many points → **scatter**
- Categorical X, proportional Y summing ~100%, ≤ 7 categories → **pie**
- Categorical X with many categories or long labels → **horizontal bar**
- Otherwise → **vertical bar (column)**

---

## Data Validation

Validate chart data before rendering to catch problems early:

```python
from pathlib import Path
from pptxforgekit.chart.loader import ChartDataLoader
from pptxforgekit.chart.validator import ChartDataValidator

loader = ChartDataLoader()
df = loader.load(element, base_path=Path("."))

result = ChartDataValidator().validate(element, df)
result.log_summary()   # logs warnings / errors via the standard logger

if not result.is_valid:
    for err in result.errors():
        print(f"ERROR: {err}")
```

### Validation checks

| Check | Severity | Condition |
|---|---|---|
| Missing column | Error | `x_column` or a `y_columns` entry not found in DataFrame |
| Non-numeric Y | Error | Y column dtype is not numeric |
| NaN / null values | Warning | Any null cells in the data |
| Duplicate X values | Warning | Scatter or line chart with repeated X values |
| Negative pie values | Error | Pie chart with any negative Y value |
| Too many pie slices | Warning | Pie with more than 8 categories |
| Flat data | Info | All Y values are identical |

### Data consistency check

When both `data_source` and `data_inline` are present, verify the inline snapshot matches the file:

```python
from pptxforgekit.chart.validator import ChartDataValidator

result = ChartDataValidator().validate_data_consistency(element, base_path=Path("."))
if result.issues:
    for issue in result.issues:
        print(issue)
```

---

## Rendering a Chart-Only Schema

You can render a schema that contains only chart slides to preview chart output:

```bash
pptxforgekit render examples/schemas/sample_slides.json \
    --theme examples/themes/default.yaml \
    --output chart_preview.pptx
```
