from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

Severity = Literal["low", "medium", "high", "critical"]

SEVERITY_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}
SEVERITY_EMOJI: dict[str, str] = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🔵",
}

# Canonical issue_type values — each maps to a check_category
ISSUE_TYPES: dict[str, str] = {
    # layout
    "element_overlap":        "layout",
    "element_clipping":       "layout",
    # text
    "text_overflow":          "text",
    "minimum_font_size":      "text",
    "excessive_text_density": "text",
    # image
    "image_resolution":       "image",
    "image_not_found":        "image",
    # chart
    "chart_label_readability":"chart",
    # theme
    "theme_consistency":      "theme",
    # data
    "data_consistency":       "data",
}


class ReviewIssue(BaseModel):
    """A single problem found on a slide during review.

    ``issue_type`` is the canonical identifier for the kind of problem
    (used for filtering and auto-fix routing).
    ``check_category`` is the broader bucket the issue belongs to.
    """

    issue_id: str = Field(..., description="Unique ID for this issue, e.g. 's001_overlap_001'")
    slide_id: str
    element_id: str | None = Field(None, description="The element that has the problem, if applicable")
    issue_type: str = Field(
        ...,
        description=(
            "Specific issue kind. One of: "
            + ", ".join(f"'{k}'" for k in ISSUE_TYPES)
        ),
    )
    check_category: str = Field(
        ...,
        description="Broad category: layout | text | image | chart | theme | data",
    )
    severity: Severity
    message: str = Field(..., description="Human-readable description of the problem")
    suggested_fix: str | None = Field(
        None, description="Actionable recommendation for fixing the issue"
    )
    auto_fixable: bool = Field(
        False,
        description="Whether AutoFixer can resolve this issue without human review",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured metadata the AutoFixer uses to apply the fix. "
            "Keys depend on issue_type (e.g. 'secondary_element_id' for overlap, "
            "'overflow_ratio' for text_overflow)."
        ),
    )


class ReviewReport(BaseModel):
    """Aggregated review results for one presentation."""

    pptx_file: str
    schema_file: str
    reviewed_at: str
    issues: list[ReviewIssue] = Field(default_factory=list)

    # ── computed aggregates ───────────────────────────────────────────────────

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_issues(self) -> int:
        return len(self.issues)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for issue in self.issues:
            counts[issue.severity] += 1
        return counts

    @computed_field  # type: ignore[prop-decorator]
    @property
    def by_type(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for issue in self.issues:
            counts[issue.issue_type] += 1
        return dict(counts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def by_slide(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for issue in self.issues:
            counts[issue.slide_id] += 1
        return dict(counts)

    # ── helpers ───────────────────────────────────────────────────────────────

    def has_blocking_issues(self) -> bool:
        return any(i.severity in ("high", "critical") for i in self.issues)

    def issues_for_slide(self, slide_id: str) -> list[ReviewIssue]:
        return [i for i in self.issues if i.slide_id == slide_id]

    def issues_of_type(self, issue_type: str) -> list[ReviewIssue]:
        return [i for i in self.issues if i.issue_type == issue_type]

    # ── output ────────────────────────────────────────────────────────────────

    def to_markdown(self) -> str:
        sorted_issues = sorted(
            self.issues, key=lambda i: -SEVERITY_ORDER[i.severity]
        )
        blocking = sum(
            1 for i in self.issues if i.severity in ("high", "critical")
        )

        lines: list[str] = [
            "# Review Report",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| **PPTX** | `{self.pptx_file}` |",
            f"| **Schema** | `{self.schema_file}` |",
            f"| **Reviewed at** | {self.reviewed_at} |",
            f"| **Total issues** | {self.total_issues} ({blocking} blocking) |",
            "",
            "## Severity Summary",
            "",
            "| Severity | Count |",
            "|---|---|",
        ]
        for sev in ("critical", "high", "medium", "low"):
            count = self.summary.get(sev, 0)
            emoji = SEVERITY_EMOJI[sev]
            lines.append(f"| {emoji} **{sev.upper()}** | {count} |")

        lines += [
            "",
            "## Issues by Type",
            "",
            "| Issue Type | Count | Worst Severity |",
            "|---|---|---|",
        ]
        for itype, count in sorted(self.by_type.items(), key=lambda x: -x[1]):
            type_issues = self.issues_of_type(itype)
            worst = max(type_issues, key=lambda i: SEVERITY_ORDER[i.severity])
            emoji = SEVERITY_EMOJI[worst.severity]
            lines.append(f"| `{itype}` | {count} | {emoji} {worst.severity} |")

        if self.by_slide:
            lines += [
                "",
                "## Issues by Slide",
                "",
                "| Slide | Issues |",
                "|---|---|",
            ]
            for slide_id, count in sorted(self.by_slide.items()):
                lines.append(f"| `{slide_id}` | {count} |")

        lines += ["", "---", "", "## Issue Details", ""]

        for issue in sorted_issues:
            emoji = SEVERITY_EMOJI[issue.severity]
            lines.append(
                f"### {emoji} `{issue.issue_id}` — "
                f"[{issue.severity.upper()}] `{issue.issue_type}`"
            )
            lines.append("")
            lines.append(f"- **Slide**: `{issue.slide_id}`")
            lines.append(f"- **Category**: {issue.check_category}")
            if issue.element_id:
                lines.append(f"- **Element**: `{issue.element_id}`")
            lines.append(f"- **Message**: {issue.message}")
            if issue.suggested_fix:
                lines.append(f"- **Suggested fix**: {issue.suggested_fix}")
            if issue.auto_fixable:
                lines.append("- **Auto-fixable**: yes")
            lines.append("")

        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_file(cls, path: str | Path) -> ReviewReport:
        return cls.model_validate(
            json.loads(Path(path).read_text(encoding="utf-8"))
        )

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    def write_markdown(self, path: str | Path) -> None:
        Path(path).write_text(self.to_markdown(), encoding="utf-8")
