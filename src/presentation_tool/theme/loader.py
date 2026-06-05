from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from presentation_tool.exceptions import ThemeLoadError
from presentation_tool.models.theme import (
    ChartStyle,
    ColorPalette,
    FontConfig,
    FooterConfig,
    Margins,
    ThemeConfig,
    ThemeRule,
    TitlePosition,
)

logger = logging.getLogger(__name__)

# Default widescreen slide width minus standard side margins
_DEFAULT_CONTENT_WIDTH = 29.87


class ThemeLoader:
    def load(self, path: Path) -> ThemeConfig:
        logger.info("Loading theme from %s", path)
        if not path.exists():
            raise ThemeLoadError(f"Theme file not found: {path}")
        raw = self._read_file(path)
        return self._parse(raw, source=str(path))

    def _read_file(self, path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        text = path.read_text(encoding="utf-8")
        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        if suffix == ".json":
            return json.loads(text)
        raise ThemeLoadError(f"Unsupported theme format '{suffix}'. Use .yaml or .json.")

    def _parse(self, raw: dict[str, Any], source: str) -> ThemeConfig:
        try:
            return ThemeConfig(
                name=raw.get("name", Path(source).stem),
                colors=self._parse_colors(raw.get("colors", {})),
                fonts=self._parse_fonts(raw.get("fonts", {})),
                margins=self._parse_margins(raw.get("margins", {})),
                title_position=self._parse_title_position(raw.get("title_position", {})),
                footer=self._parse_footer(raw.get("footer", {})),
                chart_style=self._parse_chart_style(raw.get("chart_style", {})),
                rules=self._parse_rules(raw.get("rules", [])),
            )
        except (TypeError, ValueError) as exc:
            raise ThemeLoadError(f"Invalid theme file '{source}': {exc}") from exc

    def _parse_colors(self, d: dict[str, Any]) -> ColorPalette:
        return ColorPalette(
            primary=d.get("primary", "#1F3864"),
            secondary=d.get("secondary", "#2F75B6"),
            accent=d.get("accent", "#ED7D31"),
            background=d.get("background", "#FFFFFF"),
            text=d.get("text", "#000000"),
            text_light=d.get("text_light", "#595959"),
        )

    def _parse_fonts(self, d: dict[str, Any]) -> FontConfig:
        return FontConfig(
            title_font=d.get("title_font", "Calibri"),
            body_font=d.get("body_font", "Calibri"),
            title_size=int(d.get("title_size", 36)),
            heading_size=int(d.get("heading_size", 28)),
            body_size=int(d.get("body_size", 20)),
            caption_size=int(d.get("caption_size", 14)),
            min_size=int(d.get("min_size", 12)),
        )

    def _parse_margins(self, d: dict[str, Any]) -> Margins:
        return Margins(
            top=float(d.get("top", 1.5)),
            bottom=float(d.get("bottom", 1.5)),
            left=float(d.get("left", 2.0)),
            right=float(d.get("right", 2.0)),
        )

    def _parse_title_position(self, d: dict[str, Any]) -> TitlePosition:
        return TitlePosition(
            x=float(d.get("x", 2.0)),
            y=float(d.get("y", 0.5)),
            w=float(d.get("w", _DEFAULT_CONTENT_WIDTH)),
            h=float(d.get("h", 2.0)),
        )

    def _parse_footer(self, d: dict[str, Any]) -> FooterConfig:
        return FooterConfig(
            show_page_number=bool(d.get("show_page_number", True)),
            show_date=bool(d.get("show_date", False)),
            custom_text=str(d.get("custom_text", "")),
        )

    def _parse_chart_style(self, d: dict[str, Any]) -> ChartStyle:
        return ChartStyle(
            preferred_type=d.get("preferred_type", "bar"),
            color_sequence=list(
                d.get("color_sequence", ["#2F75B6", "#ED7D31", "#A9D18E", "#FF0000", "#9E480E"])
            ),
            show_legend=bool(d.get("show_legend", True)),
            show_data_labels=bool(d.get("show_data_labels", False)),
            label_style=str(d.get("label_style", "outside_end")),
        )

    def _parse_rules(self, items: list[Any]) -> list[ThemeRule]:
        rules = []
        for item in items:
            if not isinstance(item, dict):
                continue
            rule_type = item.get("rule_type")
            value = item.get("value")
            if rule_type is None or value is None:
                logger.warning("Skipping invalid rule entry: %s", item)
                continue
            rules.append(ThemeRule(
                rule_type=str(rule_type),
                value=value,
                description=str(item.get("description", "")),
            ))
        return rules


def default_theme_yaml() -> str:
    return """\
name: default

colors:
  primary: "#1F3864"
  secondary: "#2F75B6"
  accent: "#ED7D31"
  background: "#FFFFFF"
  text: "#000000"
  text_light: "#595959"

fonts:
  title_font: Calibri
  body_font: Calibri
  title_size: 36
  heading_size: 28
  body_size: 20
  caption_size: 14
  min_size: 12

margins:
  top: 1.5
  bottom: 1.5
  left: 2.0
  right: 2.0

title_position:
  x: 2.0
  y: 0.5
  w: 29.87
  h: 2.0

footer:
  show_page_number: true
  show_date: false
  custom_text: ""

chart_style:
  preferred_type: bar
  color_sequence:
    - "#2F75B6"
    - "#ED7D31"
    - "#A9D18E"
    - "#FF0000"
    - "#9E480E"
  show_legend: true
  show_data_labels: false
  label_style: outside_end

rules:
  - rule_type: max_bullets
    value: 6
    description: "Maximum bullet points per slide"
  - rule_type: min_font_size
    value: 12
    description: "Minimum font size in points"
  - rule_type: max_text_chars
    value: 400
    description: "Maximum characters in a body text element"
"""
