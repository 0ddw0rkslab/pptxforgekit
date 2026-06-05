from __future__ import annotations

from abc import ABC, abstractmethod

from pptxforgekit.models.analysis import AnalysisResult
from pptxforgekit.models.outline import StorylineOutline


class IStorylinePlanner(ABC):
    @abstractmethod
    def plan(self, analysis: AnalysisResult, presentation_type: str) -> StorylineOutline:
        """Convert an AnalysisResult into a StorylineOutline for the given presentation type."""
        ...
