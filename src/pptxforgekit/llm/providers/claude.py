from __future__ import annotations

import logging
import os
from typing import Any

from pptxforgekit.exceptions import LLMProviderNotInstalledError
from pptxforgekit.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]
DEFAULT_MODEL = "claude-sonnet-4-6"


class ClaudeProvider(LLMProvider):
    """Anthropic Claude via the `anthropic` SDK with prompt caching."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            import anthropic as _anthropic
        except ImportError:
            raise LLMProviderNotInstalledError(
                "anthropic package not found. "
                "Install it: pip install 'pptxforgekit[llm-claude]'"
            )
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMProviderNotInstalledError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Get your key at https://console.anthropic.com/"
            )
        self._client = _anthropic.Anthropic(api_key=key)
        self._model = model
        logger.debug("ClaudeProvider ready: model=%s", model)

    @property
    def provider_name(self) -> str:
        return "claude"

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
        system: list[dict[str, Any]] = []
        if system_prompt:
            system = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},  # prompt caching
                }
            ]

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        usage = response.usage
        logger.debug(
            "Claude usage — input: %d, output: %d, cache_read: %s",
            usage.input_tokens,
            usage.output_tokens,
            getattr(usage, "cache_read_input_tokens", "n/a"),
        )
        return str(response.content[0].text)
