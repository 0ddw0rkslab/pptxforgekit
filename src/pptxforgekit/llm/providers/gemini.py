from __future__ import annotations

import logging
import os
from typing import Any

from pptxforgekit.exceptions import LLMProviderNotInstalledError, RateLimitError
from pptxforgekit.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-3.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]
DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider(LLMProvider):
    """Google Gemini via the `google-genai` SDK.

    Free tier available at https://aistudio.google.com/
    No credit card required for gemini-2.0-flash.
    """

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError:
            raise LLMProviderNotInstalledError(
                "google-genai package not found. "
                "Install it: pip install 'pptxforgekit[llm-gemini]'"
            )
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise LLMProviderNotInstalledError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        self._client = genai.Client(api_key=key)
        self._types = genai_types
        self._model = model
        logger.debug("GeminiProvider ready: model=%s", model)

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        config_kwargs: dict[str, Any] = {}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        config = self._types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=config,
            )
        except Exception as exc:
            exc_str = str(exc)
            # 429 quota / rate-limit → RateLimitError with backoff hint
            if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                import re as _re
                retry_match = _re.search(r"retryDelay.*?(\d+)s", exc_str)
                retry_after = float(retry_match.group(1)) if retry_match else None
                raise RateLimitError(
                    f"Gemini rate limit: {exc_str[:200]}", retry_after=retry_after
                ) from exc
            # 503 service unavailable — exponential backoff (retry_after=None → caller decides)
            if "503" in exc_str or "UNAVAILABLE" in exc_str:
                raise RateLimitError(
                    f"Gemini service unavailable (503): {exc_str[:200]}", retry_after=None
                ) from exc
            raise

        logger.debug(
            "Gemini usage - input: %s, output: %s",
            getattr(response.usage_metadata, "prompt_token_count", "n/a"),
            getattr(response.usage_metadata, "candidates_token_count", "n/a"),
        )
        return str(response.text)
