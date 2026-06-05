from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from presentation_tool.exceptions import ExportError
from presentation_tool.models.review import ReviewReport
from presentation_tool.models.schema import PresentationSchema

logger = logging.getLogger(__name__)


@dataclass
class ExportBundle:
    schema_path: Path
    pptx_path: Path
    review_json_path: Path | None = None
    review_md_path: Path | None = None


class Exporter:
    def export_schema(self, schema: PresentationSchema, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(schema.to_json(), encoding="utf-8")
        logger.info("Schema exported: %s", output_path)

    def export_review(
        self,
        report: ReviewReport,
        json_path: Path | None = None,
        md_path: Path | None = None,
    ) -> None:
        if json_path:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            report.write_json(json_path)
            logger.info("Review JSON exported: %s", json_path)
        if md_path:
            md_path.parent.mkdir(parents=True, exist_ok=True)
            report.write_markdown(md_path)
            logger.info("Review Markdown exported: %s", md_path)

    def copy_pptx(self, src: Path, dest: Path) -> None:
        if not src.exists():
            raise ExportError(f"PPTX source not found: {src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src != dest:
            shutil.copy2(src, dest)
        logger.info("PPTX exported: %s", dest)
