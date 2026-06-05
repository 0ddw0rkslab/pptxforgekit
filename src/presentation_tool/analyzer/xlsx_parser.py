from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from presentation_tool.models.analysis import DataFileRef, TableCandidate

logger = logging.getLogger(__name__)

_SAMPLE_ROWS = 5


def parse_xlsx(path: Path) -> list[tuple[DataFileRef, TableCandidate]]:
    """Parse all sheets in an XLSX file, returning one pair per sheet."""
    logger.debug("Parsing XLSX: %s", path)
    xl = pd.ExcelFile(path)
    results = []
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name)
        results.append(_df_to_refs(path, df, sheet_name=str(sheet_name)))
    return results


def parse_xlsx_sheet(
    path: Path, sheet_name: int | str = 0
) -> tuple[DataFileRef, TableCandidate]:
    """Parse a single sheet from an XLSX file."""
    logger.debug("Parsing XLSX sheet: %s (sheet=%s)", path, sheet_name)
    df = pd.read_excel(path, sheet_name=sheet_name)
    return _df_to_refs(path, df, sheet_name=str(sheet_name))


def _df_to_refs(
    path: Path, df: pd.DataFrame, sheet_name: str
) -> tuple[DataFileRef, TableCandidate]:
    columns = [str(c) for c in df.columns.tolist()]
    dtypes = {str(k): str(v) for k, v in df.dtypes.to_dict().items()}

    sample_dicts: list[dict[str, Any]] = (
        df.head(_SAMPLE_ROWS).fillna("").astype(str).to_dict(orient="records")
    )
    sample_rows: list[list[Any]] = (
        df.head(_SAMPLE_ROWS).fillna("").astype(str).values.tolist()
    )

    ref_path = f"{path}[{sheet_name}]"
    title = f"{path.stem} — {sheet_name}"

    data_ref = DataFileRef(
        file_path=ref_path,
        columns=columns,
        row_count=len(df),
        dtypes=dtypes,
        sample=sample_dicts,
    )
    table_candidate = TableCandidate(
        source_file=ref_path,
        title=title,
        columns=columns,
        row_count=len(df),
        sample_rows=sample_rows,
    )
    return data_ref, table_candidate
