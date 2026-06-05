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
