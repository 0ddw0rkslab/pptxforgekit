from __future__ import annotations

import logging
import os

from pptxforgekit.exceptions import LLMProviderNotInstalledError
from pptxforgekit.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-thinking-exp",
]
DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiProvider(LLMProvider):
    """Google Gemini via the `google-generativeai` SDK.

    Free tier available at https://aistudio.google.com/
    No credit card required for gemini-2.0-flash.
    """

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise LLMProviderNotInstalledError(
                "google-generativeai package not found. "
                "Install it: pip install 'pptxforgekit[llm-gemini]'"
            )
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise LLMProviderNotInstalledError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        genai.configure(api_key=key)
        self._genai = genai
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
        gen_config_kwargs: dict = {}
        if json_mode:
            gen_config_kwargs["response_mime_type"] = "application/json"

        model = self._genai.GenerativeModel(
            self._model,
            system_instruction=system_prompt or None,
            generation_config=(
                self._genai.types.GenerationConfig(**gen_config_kwargs)
                if gen_config_kwargs
                else None
            ),
        )
        response = model.generate_content(user_prompt)
        logger.debug(
            "Gemini usage — input: %s, output: %s",
            getattr(response.usage_metadata, "prompt_token_count", "n/a"),
            getattr(response.usage_metadata, "candidates_token_count", "n/a"),
        )
        return response.text
