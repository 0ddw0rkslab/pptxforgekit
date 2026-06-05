from __future__ import annotations

from abc import ABC, abstractmethod

from presentation_tool.models.outline import StorylineOutline
from presentation_tool.models.schema import PresentationSchema
from presentation_tool.models.theme import ThemeConfig


class ISlideSchemaGenerator(ABC):
    @abstractmethod
    def generate(self, outline: StorylineOutline, theme: ThemeConfig) -> PresentationSchema:
        """Convert a StorylineOutline into a fully-positioned PresentationSchema."""
        ...
