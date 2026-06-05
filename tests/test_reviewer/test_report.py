from __future__ import annotations

import json
from pathlib import Path

from pptxforgekit.models.review import ReviewIssue, ReviewReport


def _issue(
    slide_id: str = "s001",
    issue_type: str = "element_overlap",
    check_category: str = "layout",
    severity: str = "medium",
    seq: int = 1,
) -> ReviewIssue:
    return ReviewIssue(
        issue_id=f"{slide_id}_{issue_type}_{seq:03d}",
        slide_id=slide_id,
        issue_type=issue_type,
        check_category=check_category,
        severity=severity,
        message=f"Test issue {seq}",
        suggested_fix="Fix it.",
    )


def _report(issues: list[ReviewIssue] | None = None) -> ReviewReport:
    return ReviewReport(
        pptx_file="test.pptx",
        schema_file="slides.json",
        reviewed_at="2026-06-04T12:00:00Z",
        issues=issues or [],
    )


# ── computed fields ───────────────────────────────────────────────────────────


class TestReviewReportAggregates:
    def test_total_issues_count(self) -> None:
        r = _report([_issue(seq=1), _issue(seq=2)])
        assert r.total_issues == 2

    def test_summary_counts(self) -> None:
        issues = [
            _issue(severity="critical"),
            _issue(severity="high"),
            _issue(severity="high"),
            _issue(severity="medium"),
            _issue(severity="low"),
        ]
        r = _report(issues)
        assert r.summary["critical"] == 1
        assert r.summary["high"] == 2
        assert r.summary["medium"] == 1
        assert r.summary["low"] == 1

    def test_by_type_counts(self) -> None:
        issues = [
            _issue(issue_type="element_overlap", seq=1),
            _issue(issue_type="element_overlap", seq=2),
            _issue(issue_type="text_overflow", seq=1),
        ]
        r = _report(issues)
        assert r.by_type["element_overlap"] == 2
        assert r.by_type["text_overflow"] == 1

    def test_by_slide_counts(self) -> None:
        issues = [
            _issue(slide_id="s001", seq=1),
            _issue(slide_id="s001", seq=2),
            _issue(slide_id="s002", seq=1),
        ]
        r = _report(issues)
        assert r.by_slide["s001"] == 2
        assert r.by_slide["s002"] == 1

    def test_has_blocking_issues(self) -> None:
        r = _report([_issue(severity="high")])
        assert r.has_blocking_issues()

    def test_no_blocking_issues(self) -> None:
        r = _report([_issue(severity="medium"), _issue(severity="low")])
        assert not r.has_blocking_issues()

    def test_empty_report_no_blocking(self) -> None:
        assert not _report([]).has_blocking_issues()


# ── JSON output ───────────────────────────────────────────────────────────────


class TestReviewReportJson:
    def test_json_contains_issues(self) -> None:
        r = _report([_issue()])
        data = json.loads(r.to_json())
        assert data["total_issues"] == 1
        assert data["issues"][0]["issue_type"] == "element_overlap"

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        original = _report([_issue(severity="high")])
        path = tmp_path / "report.json"
        original.write_json(path)
        loaded = ReviewReport.from_file(path)
        assert loaded.total_issues == original.total_issues
        assert loaded.issues[0].severity == "high"
        assert loaded.issues[0].issue_type == "element_overlap"

    def test_json_has_schema_fields(self) -> None:
        r = _report([_issue()])
        data = json.loads(r.to_json())
        assert "pptx_file" in data
        assert "schema_file" in data
        assert "reviewed_at" in data
        assert "summary" in data


# ── Markdown output ───────────────────────────────────────────────────────────


class TestReviewReportMarkdown:
    def test_markdown_contains_severity_summary(self) -> None:
        r = _report([_issue(severity="critical"), _issue(severity="medium")])
        md = r.to_markdown()
        assert "CRITICAL" in md
        assert "MEDIUM" in md

    def test_markdown_contains_issue_type_table(self) -> None:
        r = _report([_issue(issue_type="element_overlap")])
        md = r.to_markdown()
        assert "element_overlap" in md

    def test_markdown_contains_slide_table(self) -> None:
        r = _report([_issue(slide_id="s003")])
        md = r.to_markdown()
        assert "s003" in md

    def test_markdown_contains_suggested_fix(self) -> None:
        issue = _issue()
        issue.suggested_fix = "Move the element to the left."
        r = _report([issue])
        md = r.to_markdown()
        assert "Move the element" in md

    def test_markdown_sorted_by_severity(self) -> None:
        r = _report([
            _issue(severity="low", seq=1),
            _issue(severity="critical", seq=2),
            _issue(severity="medium", seq=3),
        ])
        md = r.to_markdown()
        critical_pos = md.find("CRITICAL")
        low_pos = md.find("LOW")
        assert critical_pos < low_pos

    def test_markdown_write_and_read(self, tmp_path: Path) -> None:
        r = _report([_issue()])
        path = tmp_path / "report.md"
        r.write_markdown(path)
        text = path.read_text(encoding="utf-8")
        assert "# Review Report" in text
        assert "element_overlap" in text

    def test_empty_report_renders_cleanly(self) -> None:
        r = _report([])
        md = r.to_markdown()
        assert "Total issues" in md
        assert "0" in md
