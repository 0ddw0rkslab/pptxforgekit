from __future__ import annotations

import logging
import os

from presentation_tool.exceptions import LLMProviderNotInstalledError
from presentation_tool.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

# Common models — Ollama supports any locally pulled model.
# Run `ollama list` to see what's available on your machine.
KNOWN_MODELS = [
    "llama3.2",
    "llama3.1:70b",
    "mistral",
    "qwen2.5",
    "phi4",
    "gemma2",
    "deepseek-r1",
]
DEFAULT_MODEL = "llama3.2"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    """Ollama local LLM via its OpenAI-compatible API.

    Completely free — no API key required.
    Install Ollama: https://ollama.com/
    Pull a model: ollama pull llama3.2
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMProviderNotInstalledError(
                "openai package not found (used as Ollama client). "
                "Install it: pip install 'presentation-tool[llm-ollama]'"
            )
        url = base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        url = url.rstrip("/")
        if not url.endswith("/v1"):
            url = url + "/v1"

        # Ollama's OpenAI-compatible endpoint accepts any non-empty string as api_key
        self._client = OpenAI(api_key="ollama", base_url=url)
        self._model = model
        logger.debug("OllamaProvider ready: model=%s, base_url=%s", model, url)

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @property
    def supported_models(self) -> list[str]:
        # Open-ended — depends on what user has pulled locally
        return KNOWN_MODELS

    def complete(
        self,
        user_prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs: dict = {"model": self._model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
