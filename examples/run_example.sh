#!/usr/bin/env bash
# End-to-end example run for presentation-tool
# Run from the project root: bash examples/run_example.sh

set -euo pipefail

DOCS="examples/input_docs"
THEME="examples/themes/default.yaml"
OUT="examples/output"

mkdir -p "$OUT"

echo "=== Step 1: Analyze input documents ==="
presentation-tool analyze "$DOCS" --output "$OUT/analysis.json"

echo ""
echo "=== Step 2: Plan research storyline ==="
presentation-tool plan "$OUT/analysis.json" --type research --output "$OUT/outline.json"

echo ""
echo "=== Step 3: Build slide schema ==="
presentation-tool build-schema "$OUT/outline.json" --theme "$THEME" --output "$OUT/slides.json"

echo ""
echo "=== Step 4: Render PPTX ==="
presentation-tool render "$OUT/slides.json" --theme "$THEME" --output "$OUT/presentation.pptx"

echo ""
echo "=== Step 5: Review (JSON + Markdown) ==="
presentation-tool review "$OUT/presentation.pptx" "$OUT/slides.json" \
    --theme "$THEME" --output "$OUT/review_report.json"
presentation-tool review "$OUT/presentation.pptx" "$OUT/slides.json" \
    --theme "$THEME" --output "$OUT/review_report.md"

echo ""
echo "=== Step 6: Auto-fix ==="
presentation-tool autofix "$OUT/slides.json" "$OUT/review_report.json" \
    --output "$OUT/slides_fixed.json"

echo ""
echo "=== Step 7: Re-render fixed schema ==="
presentation-tool render "$OUT/slides_fixed.json" --theme "$THEME" \
    --output "$OUT/presentation_fixed.pptx"

echo ""
echo "Done! Output files:"
ls -lh "$OUT/"
