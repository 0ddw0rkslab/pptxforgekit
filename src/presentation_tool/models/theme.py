from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColorPalette:
    primary: str = "#1F3864"
    secondary: str = "#2F75B6"
    accent: str = "#ED7D31"
    background: str = "#FFFFFF"
    text: str = "#000000"
    text_light: str = "#595959"


@dataclass
class FontConfig:
    title_font: str = "Calibri"
    body_font: str = "Calibri"
    title_size: int = 36
    heading_size: int = 28
    body_size: int = 20
    caption_size: int = 14
    min_size: int = 12


@dataclass
class Margins:
    top: float = 1.5     # cm
    bottom: float = 1.5
    left: float = 2.0
    right: float = 2.0


@dataclass
class TitlePosition:
    x: float = 2.0
    y: float = 0.5
    w: float = 29.87   # slide_width(33.87) - left(2.0) - right(2.0)
    h: float = 2.0


@dataclass
class FooterConfig:
    show_page_number: bool = True
    show_date: bool = False
    custom_text: str = ""


@dataclass
class ChartStyle:
    preferred_type: str = "bar"
    color_sequence: list[str] = field(
        default_factory=lambda: ["#2F75B6", "#ED7D31", "#A9D18E", "#FF0000", "#9E480E"]
    )
    show_legend: bool = True
    show_data_labels: bool = False
    label_style: str = "outside_end"


@dataclass
class ThemeRule:
    rule_type: str
    value: int | float | str
    description: str = ""


@dataclass
class ThemeConfig:
    name: str = "default"
    colors: ColorPalette = field(default_factory=ColorPalette)
    fonts: FontConfig = field(default_factory=FontConfig)
    margins: Margins = field(default_factory=Margins)
    title_position: TitlePosition = field(default_factory=TitlePosition)
    footer: FooterConfig = field(default_factory=FooterConfig)
    chart_style: ChartStyle = field(default_factory=ChartStyle)
    rules: list[ThemeRule] = field(default_factory=list)

    def get_rule(self, rule_type: str) -> ThemeRule | None:
        for rule in self.rules:
            if rule.rule_type == rule_type:
                return rule
        return None

    def get_rule_value(self, rule_type: str, default: Any = None) -> Any:
        rule = self.get_rule(rule_type)
        return rule.value if rule is not None else default
