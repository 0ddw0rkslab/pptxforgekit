from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TableCandidate(BaseModel):
    source_file: str
    title: str
    columns: list[str]
    row_count: int
    sample_rows: list[list[Any]] = Field(default_factory=list)


class FigureCandidate(BaseModel):
    source_file: str
    caption: str
    file_path: str
    width: int = 0
    height: int = 0


class DataFileRef(BaseModel):
    file_path: str
    columns: list[str]
    row_count: int
    dtypes: dict[str, str] = Field(default_factory=dict)
    sample: list[dict[str, Any]] = Field(default_factory=list)


class Section(BaseModel):
    heading: str
    paragraphs: list[str] = Field(default_factory=list)
    figures: list[FigureCandidate] = Field(default_factory=list)
    tables: list[TableCandidate] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    source_files: list[str]
    title: str
    abstract: str = ""
    key_messages: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    tables: list[TableCandidate] = Field(default_factory=list)
    figures: list[FigureCandidate] = Field(default_factory=list)
    data_files: list[DataFileRef] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
