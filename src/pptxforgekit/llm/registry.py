from __future__ import annotations

from typing import Any

from pptxforgekit.exceptions import LLMError
from pptxforgekit.llm.provider import LLMProvider

PROVIDER_NAMES = ["claude", "gpt", "gemini", "ollama"]

# Default models per provider
DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-sonnet-4-6",
    "gpt":    "gpt-4o",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.2",
}

# All known models per provider (shown in --help)
KNOWN_MODELS: dict[str, list[str]] = {
    "claude": ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "gpt":    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-3.5-flash"],
    "ollama": ["llama3.2", "llama3.1:70b", "mistral", "qwen2.5", "phi4"],
}


def build_provider(provider: str, model: str | None = None, **kwargs: Any) -> LLMProvider:
    """Instantiate an LLMProvider by name.

    Args:
        provider: One of ``claude``, ``gpt``, ``gemini``, ``ollama``.
        model:    Model ID string. Uses provider default when None.
        **kwargs: Forwarded to the provider constructor (e.g. api_key, base_url).
    """
    provider = provider.lower().strip()
    resolved_model = model or DEFAULT_MODELS.get(provider, "")

    if provider == "claude":
        from pptxforgekit.llm.providers.claude import ClaudeProvider
        return ClaudeProvider(model=resolved_model, **kwargs)

    if provider == "gpt":
        from pptxforgekit.llm.providers.openai_p import OpenAIProvider
        return OpenAIProvider(model=resolved_model, **kwargs)

    if provider == "gemini":
        from pptxforgekit.llm.providers.gemini import GeminiProvider
        return GeminiProvider(model=resolved_model, **kwargs)

    if provider == "ollama":
        from pptxforgekit.llm.providers.ollama import OllamaProvider
        return OllamaProvider(model=resolved_model, **kwargs)

    raise LLMError(
        f"Unknown LLM provider '{provider}'. "
        f"Choose one of: {', '.join(PROVIDER_NAMES)}"
    )
