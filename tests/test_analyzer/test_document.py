from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from presentation_tool.analyzer.document import DocumentAnalyzer
from presentation_tool.exceptions import AnalysisError
from presentation_tool.models.analysis import AnalysisResult


@pytest.fixture
def analyzer() -> DocumentAnalyzer:
    return DocumentAnalyzer()


class TestDocumentAnalyzerSingleFile:
    def test_analyze_markdown(self, analyzer: DocumentAnalyzer, fixture_md: Path) -> None:
        result = analyzer.analyze(fixture_md)
        assert isinstance(result, AnalysisResult)
        assert result.title == "Sample Research Paper"
        assert len(result.sections) >= 1

    def test_analyze_markdown_has_abstract(self, analyzer: DocumentAnalyzer, fixture_md: Path) -> None:
        result = analyzer.analyze(fixture_md)
        assert result.abstract != ""

    def test_analyze_markdown_has_conclusions(self, analyzer: DocumentAnalyzer, fixture_md: Path) -> None:
        result = analyzer.analyze(fixture_md)
        assert len(result.conclusions) >= 1

    def test_analyze_csv(self, analyzer: DocumentAnalyzer, fixture_csv: Path) -> None:
        result = analyzer.analyze(fixture_csv)
        assert len(result.data_files) == 1
        assert len(result.tables) == 1
        assert result.data_files[0].row_count >= 0

    def test_analyze_xlsx_single_sheet(self, analyzer: DocumentAnalyzer, tmp_path: Path) -> None:
        xlsx_path = tmp_path / "test.xlsx"
        df = pd.DataFrame({"method": ["A", "B"], "accuracy": [0.9, 0.85]})
        df.to_excel(xlsx_path, index=False)

        result = analyzer.analyze(xlsx_path)
        assert len(result.data_files) == 1
        assert "method" in result.data_files[0].columns

    def test_analyze_xlsx_multiple_sheets(self, analyzer: DocumentAnalyzer, tmp_path: Path) -> None:
        xlsx_path = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(xlsx_path) as writer:
            pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({"b": [2]}).to_excel(writer, sheet_name="Sheet2", index=False)

        result = analyzer.analyze(xlsx_path)
        assert len(result.data_files) == 2
        assert len(result.tables) == 2

    def test_analyze_missing_path_raises(self, analyzer: DocumentAnalyzer, tmp_path: Path) -> None:
        with pytest.raises(AnalysisError):
            analyzer.analyze(tmp_path / "nonexistent.md")

    def test_analyze_unsupported_extension_raises(self, analyzer: DocumentAnalyzer, tmp_path: Path) -> None:
        bad_file = tmp_path / "file.pdf"
        bad_file.write_text("content")
        with pytest.raises(AnalysisError):
            analyzer.analyze(bad_file)

    def test_source_files_populated(self, analyzer: DocumentAnalyzer, fixture_md: Path) -> None:
        result = analyzer.analyze(fixture_md)
        assert any(fixture_md.name in f for f in result.source_files)


class TestDocumentAnalyzerDirectory:
    def test_analyze_directory(self, analyzer: DocumentAnalyzer, tmp_path: Path) -> None:
        (tmp_path / "paper.md").write_text("# Title\n\n## Abstract\nHello.\n\n## Conclusion\nDone.")
        pd.DataFrame({"x": [1, 2], "y": [3, 4]}).to_csv(tmp_path / "data.csv", index=False)

        result = analyzer.analyze(tmp_path)
        assert result.title != ""
        assert len(result.data_files) == 1
        assert len(result.source_files) == 2

    def test_analyze_empty_directory_raises(self, analyzer: DocumentAnalyzer, tmp_path: Path) -> None:
        with pytest.raises(AnalysisError):
            analyzer.analyze(tmp_path)

    def test_analyze_directory_unsupported_files_skipped(
        self, analyzer: DocumentAnalyzer, tmp_path: Path
    ) -> None:
        (tmp_path / "notes.md").write_text("# Notes\n\n## Abstract\nStuff.\n\n## Conclusion\nOK.")
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02")

        result = analyzer.analyze(tmp_path)
        assert len(result.source_files) == 1
