from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from pptxforgekit.models.analysis import DataFileRef, TableCandidate

logger = logging.getLogger(__name__)

_SAMPLE_ROWS = 5


def parse_csv(path: Path) -> tuple[DataFileRef, TableCandidate]:
    logger.debug("Parsing CSV: %s", path)
    df = pd.read_csv(path)
    return _df_to_refs(path, df)


def _df_to_refs(path: Path, df: pd.DataFrame) -> tuple[DataFileRef, TableCandidate]:
    columns = [str(c) for c in df.columns.tolist()]
    dtypes = {str(k): str(v) for k, v in df.dtypes.to_dict().items()}

    sample_dicts: list[dict[str, Any]] = (
        df.head(_SAMPLE_ROWS).fillna("").astype(str).to_dict(orient="records")
    )
    sample_rows: list[list[Any]] = (
        df.head(_SAMPLE_ROWS).fillna("").astype(str).values.tolist()
    )

    data_ref = DataFileRef(
        file_path=str(path),
        columns=columns,
        row_count=len(df),
        dtypes=dtypes,
        sample=sample_dicts,
    )
    table_candidate = TableCandidate(
        source_file=str(path),
        title=path.stem,
        columns=columns,
        row_count=len(df),
        sample_rows=sample_rows,
    )
    return data_ref, table_candidate
