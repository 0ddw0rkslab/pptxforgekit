from __future__ import annotations

import logging
import os

from typing import Any

from pptxforgekit.exceptions import LLMProviderNotInstalledError
from pptxforgekit.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "o1",
    "o3-mini",
]
DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT via the `openai` SDK."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMProviderNotInstalledError(
                "openai package not found. "
                "Install it: pip install 'pptxforgekit[llm-openai]'"
            )
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key and not base_url:
            raise LLMProviderNotInstalledError(
                "OPENAI_API_KEY environment variable is not set. "
                "Get your key at https://platform.openai.com/api-keys"
            )
        self._client = OpenAI(api_key=key or "none", base_url=base_url)
        self._model = model
        logger.debug("OpenAIProvider ready: model=%s", model)

    @property
    def provider_name(self) -> str:
        return "gpt"

    @property
    def model(self) -> str:
        return self._model

    @property
    def supported_models(self) -> list[str]:
        return SUPPORTED_MODELS

    def complete(
        self,
        user_prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 4096,
        }
        # o1/o3 don't support json_object response format
        if json_mode and not self._model.startswith("o"):
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        logger.debug(
            "OpenAI usage — input: %d, output: %d",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return response.choices[0].message.content or ""
