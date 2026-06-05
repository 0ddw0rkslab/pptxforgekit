from __future__ import annotations

from pathlib import Path

import pytest

from pptxforgekit.exceptions import ThemeLoadError
from pptxforgekit.models.theme import ThemeConfig
from pptxforgekit.theme.loader import ThemeLoader, default_theme_yaml


class TestThemeLoader:
    def test_load_yaml(self, fixture_theme_yaml: Path) -> None:
        theme = ThemeLoader().load(fixture_theme_yaml)
        assert isinstance(theme, ThemeConfig)
        assert theme.name == "test_theme"
        assert theme.colors.primary == "#1F3864"
        assert theme.fonts.title_size == 36
        assert theme.fonts.min_size == 12

    def test_load_yaml_rules(self, fixture_theme_yaml: Path) -> None:
        theme = ThemeLoader().load(fixture_theme_yaml)
        max_bullets = theme.get_rule("max_bullets")
        assert max_bullets is not None
        assert int(max_bullets.value) == 6

    def test_get_rule_missing_returns_none(self, fixture_theme_yaml: Path) -> None:
        theme = ThemeLoader().load(fixture_theme_yaml)
        assert theme.get_rule("nonexistent_rule") is None

    def test_get_rule_value_with_default(self, sample_theme: ThemeConfig) -> None:
        val = sample_theme.get_rule_value("nonexistent", default=99)
        assert val == 99

    def test_load_json(self, tmp_path: Path) -> None:
        import json
        json_file = tmp_path / "theme.json"
        json_file.write_text(
            json.dumps({"name": "json_theme", "colors": {"primary": "#FF0000"}}),
            encoding="utf-8",
        )
        theme = ThemeLoader().load(json_file)
        assert theme.name == "json_theme"
        assert theme.colors.primary == "#FF0000"
        # Defaults are applied for unspecified fields
        assert theme.colors.background == "#FFFFFF"

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ThemeLoadError, match="not found"):
            ThemeLoader().load(tmp_path / "nonexistent.yaml")

    def test_load_unsupported_format_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "theme.txt"
        f.write_text("name: broken", encoding="utf-8")
        with pytest.raises(ThemeLoadError, match="Unsupported"):
            ThemeLoader().load(f)

    def test_default_theme_yaml_roundtrip(self, tmp_path: Path) -> None:
        out = tmp_path / "default.yaml"
        out.write_text(default_theme_yaml(), encoding="utf-8")
        theme = ThemeLoader().load(out)
        assert theme.name == "default"
        assert len(theme.rules) == 3
