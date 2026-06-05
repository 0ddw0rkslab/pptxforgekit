from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, computed_field

from pptxforgekit.models.review import SEVERITY_ORDER, ReviewIssue
from pptxforgekit.models.schema import PresentationSchema


class AppliedFix(BaseModel):
    """Record of a single successful auto-fix."""

    issue_id: str
    issue_type: str
    slide_id: str
    element_id: str | None
    description: str = Field(..., description="Human-readable summary of the change made")
    before: dict[str, Any] = Field(default_factory=dict, description="Snapshot of relevant values before the fix")
    after: dict[str, Any] = Field(default_factory=dict, description="Snapshot of relevant values after the fix")


class SplitSuggestion(BaseModel):
    """A recommended content split for a text-dense slide element.

    The AutoFixer does not apply this change automatically — it records
    what the split would look like so a human can apply it manually.
    """

    issue_id: str
    slide_id: str
    element_id: str
    content_part_a: str = Field(..., description="Content to keep on the current slide")
    content_part_b: str = Field(..., description="Content to move to a new slide")
    split_at_line: int = Field(..., description="0-based line index where the split occurs")
    reason: str


class FixResult(BaseModel):
    """Output of AutoFixer.fix() — fixed schema plus audit trail."""

    source_schema_file: str
    source_report_file: str
    fixed_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    fixed_schema: PresentationSchema
    applied_fixes: list[AppliedFix] = Field(default_factory=list)
    remaining_issues: list[ReviewIssue] = Field(default_factory=list)
    split_suggestions: list[SplitSuggestion] = Field(default_factory=list)

    # ── computed ──────────────────────────────────────────────────────────────

    @computed_field  # type: ignore[misc]
    @property
    def n_fixed(self) -> int:
        return len(self.applied_fixes)

    @computed_field  # type: ignore[misc]
    @property
    def n_remaining(self) -> int:
        return len(self.remaining_issues)

    # ── output ────────────────────────────────────────────────────────────────

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    def write_markdown(self, path: str | Path) -> None:
        Path(path).write_text(self.to_markdown(), encoding="utf-8")

    def to_markdown(self) -> str:
        lines: list[str] = [
            "# Fix Result Report",
            "",
            "| | |",
            "|---|---|",
            f"| **Source schema** | `{self.source_schema_file}` |",
            f"| **Source report** | `{self.source_report_file}` |",
            f"| **Fixed at** | {self.fixed_at} |",
            f"| **Applied fixes** | {self.n_fixed} |",
            f"| **Remaining issues** | {self.n_remaining} |",
            f"| **Split suggestions** | {len(self.split_suggestions)} |",
            "",
        ]

        # ── applied fixes ─────────────────────────────────────────────────────
        if self.applied_fixes:
            lines += [
                f"## Applied Fixes ({self.n_fixed})",
                "",
                "| # | Issue ID | Type | Slide | Element | Description |",
                "|---|---|---|---|---|---|",
            ]
            for i, fix in enumerate(self.applied_fixes, 1):
                eid = f"`{fix.element_id}`" if fix.element_id else "—"
                lines.append(
                    f"| {i} | `{fix.issue_id}` | `{fix.issue_type}` "
                    f"| `{fix.slide_id}` | {eid} | {fix.description} |"
                )
            lines.append("")
        else:
            lines += ["## Applied Fixes (0)", "", "_No fixes were applied._", ""]

        # ── remaining issues ──────────────────────────────────────────────────
        if self.remaining_issues:
            sorted_remaining = sorted(
                self.remaining_issues,
                key=lambda i: -SEVERITY_ORDER[i.severity],
            )
            lines += [
                f"## Remaining Issues ({self.n_remaining})",
                "",
                "These issues require manual review:",
                "",
                "| Issue ID | Type | Severity | Slide | Element | Message |",
                "|---|---|---|---|---|---|",
            ]
            for issue in sorted_remaining:
                eid = f"`{issue.element_id}`" if issue.element_id else "—"
                msg = issue.message[:60] + ("…" if len(issue.message) > 60 else "")
                lines.append(
                    f"| `{issue.issue_id}` | `{issue.issue_type}` "
                    f"| {issue.severity} | `{issue.slide_id}` | {eid} | {msg} |"
                )
            lines.append("")
        else:
            lines += ["## Remaining Issues (0)", "", "_All issues were resolved._", ""]

        # ── split suggestions ─────────────────────────────────────────────────
        if self.split_suggestions:
            lines += [f"## Split Suggestions ({len(self.split_suggestions)})", ""]
            for sug in self.split_suggestions:
                lines += [
                    f"### Slide `{sug.slide_id}`: Split `{sug.element_id}`",
                    "",
                    f"**Reason**: {sug.reason}",
                    f"**Split at line**: {sug.split_at_line}",
                    "",
                    "**Keep on current slide:**",
                    "",
                    "```",
                    sug.content_part_a,
                    "```",
                    "",
                    "**Move to new slide:**",
                    "",
                    "```",
                    sug.content_part_b,
                    "```",
                    "",
                ]

        return "\n".join(lines)
