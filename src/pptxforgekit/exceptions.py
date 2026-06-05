from __future__ import annotations


class PresentationToolError(Exception):
    pass


class ThemeLoadError(PresentationToolError):
    pass


class AnalysisError(PresentationToolError):
    pass


class PlanningError(PresentationToolError):
    pass


class SchemaGenerationError(PresentationToolError):
    pass


class RenderError(PresentationToolError):
    pass


class ChartBuildError(PresentationToolError):
    pass


class AssetError(PresentationToolError):
    pass


class ReviewError(PresentationToolError):
    pass


class ExportError(PresentationToolError):
    pass


class LLMError(PresentationToolError):
    pass


class LLMProviderNotInstalledError(LLMError):
    pass


class RateLimitError(LLMError):
    """Raised when the provider returns a 429 / quota-exceeded response."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
