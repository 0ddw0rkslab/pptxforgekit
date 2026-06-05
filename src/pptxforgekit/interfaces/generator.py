from __future__ import annotations

from abc import ABC, abstractmethod

from pptxforgekit.models.outline import StorylineOutline
from pptxforgekit.models.schema import PresentationSchema
from pptxforgekit.models.theme import ThemeConfig


class ISlideSchemaGenerator(ABC):
    @abstractmethod
    def generate(self, outline: StorylineOutline, theme: ThemeConfig) -> PresentationSchema:
        """Convert a StorylineOutline into a fully-positioned PresentationSchema."""
        ...
