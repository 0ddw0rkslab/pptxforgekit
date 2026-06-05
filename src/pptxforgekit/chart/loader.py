from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from pptxforgekit.exceptions import ChartBuildError
from pptxforgekit.models.schema import ChartElement

logger = logging.getLogger(__name__)

_SUPPORTED_EXTS = {".csv", ".xlsx", ".xls", ".json"}


class ChartDataLoader:
    """Loads chart data from a file or inline records into a DataFrame.

    Resolution order:
    1. ``data_inline`` (if present, takes precedence over the file)
    2. ``data_source`` file path (absolute, or resolved against ``base_path``)
    """

    def load(
        self,
        element: ChartElement,
        base_path: Path | None = None,
    ) -> pd.DataFrame:
        if element.data_inline is not None:
            logger.debug("Chart '%s': using inline data (%d rows)", element.element_id, len(element.data_inline))
            return self.load_from_inline(element.data_inline)

        if not element.data_source:
            raise ChartBuildError(
                f"ChartElement '{element.element_id}': "
                f"no data source available (both data_source and data_inline are absent)."
            )

        path = self._resolve_path(element.data_source, base_path, element.element_id)
        logger.debug("Chart '%s': loading from file %s", element.element_id, path)
        return self.load_from_file(path)

    # ── public helpers ────────────────────────────────────────────────────────

    def load_from_file(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            raise ChartBuildError(f"Data file not found: {path}")

        ext = path.suffix.lower()
        if ext not in _SUPPORTED_EXTS:
            raise ChartBuildError(
                f"Unsupported data file format '{ext}'. "
                f"Supported: {sorted(_SUPPORTED_EXTS)}"
            )

        try:
            if ext == ".csv":
                return pd.read_csv(path)
            if ext in (".xlsx", ".xls"):
                return pd.read_excel(path)
            if ext == ".json":
                # Records format: [{col: val}, ...]  OR column-oriented: {col: [val, ...]}
                df = pd.read_json(path)
                return df
        except Exception as exc:
            raise ChartBuildError(f"Failed to read data file '{path}': {exc}") from exc

        # Should be unreachable but satisfies type checker
        raise ChartBuildError(f"Unhandled extension: {ext}")

    def load_from_inline(self, records: list[dict[str, Any]]) -> pd.DataFrame:
        if not records:
            raise ChartBuildError("data_inline is empty — need at least one row.")
        try:
            return pd.DataFrame(records)
        except Exception as exc:
            raise ChartBuildError(f"Failed to build DataFrame from inline data: {exc}") from exc

    # ── private ───────────────────────────────────────────────────────────────

    def _resolve_path(
        self, data_source: str, base_path: Path | None, element_id: str
    ) -> Path:
        p = Path(data_source)
        if p.is_absolute():
            return p
        if base_path:
            candidate = base_path / p
            if candidate.exists():
                return candidate
        # Last resort: treat as relative to cwd
        return p
