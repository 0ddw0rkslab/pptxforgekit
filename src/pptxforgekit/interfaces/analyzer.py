from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pptxforgekit.models.analysis import AnalysisResult


class IContentAnalyzer(ABC):
    @abstractmethod
    def analyze(self, input_path: Path) -> AnalysisResult:
        """Analyze documents at input_path (file or directory) and return structured result."""
        ...
