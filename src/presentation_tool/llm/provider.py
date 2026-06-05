from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, ValidationError

from presentation_tool.exceptions import LLMError

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class LLMProvider(ABC):
    """Common interface for all LLM backends."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """Canonical model IDs for this provider (empty = open-ended, e.g. Ollama)."""
        ...

    @abstractmethod
    def complete(
        self,
        user_prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        """Send prompt(s) and return the raw text response."""
        ...

    # ── shared helpers ────────────────────────────────────────────────────────

    def complete_json(
        self,
        user_prompt: str,
        system_prompt: str,
        model_class: type[BaseModel],
        max_retries: int = 3,
    ) -> BaseModel:
        """Call complete(), parse JSON, validate with Pydantic. Retries on failure."""
        last_exc: Exception | None = None
        current_prompt = user_prompt

        for attempt in range(1, max_retries + 1):
            raw = self.complete(current_prompt, system_prompt, json_mode=True)
            logger.debug("[%s] attempt %d raw response: %.200s", self.provider_name, attempt, raw)
            try:
                json_str = _extract_json(raw)
                return model_class.model_validate_json(json_str)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                logger.warning(
                    "[%s] attempt %d/%d failed: %s",
                    self.provider_name, attempt, max_retries, exc,
                )
                if attempt < max_retries:
                    current_prompt = (
                        f"Your previous response had this error:\n{exc}\n\n"
                        f"Fix it and return ONLY valid JSON matching the schema. "
                        f"Original task:\n{user_prompt}"
                    )

        raise LLMError(
            f"[{self.provider_name}] Failed to produce valid JSON after {max_retries} "
            f"attempts. Last error: {last_exc}"
        )


def _extract_json(text: str) -> str:
    """Strip markdown fences and return the innermost JSON object."""
    text = text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    # Find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1]
    return text
