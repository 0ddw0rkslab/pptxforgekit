from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod

from pydantic import BaseModel, ValidationError

from pptxforgekit.exceptions import LLMError, RateLimitError

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
        rate_limit_retries: int = 5,
        rate_limit_backoff: float = 15.0,
    ) -> BaseModel:
        """Call complete(), parse JSON, validate with Pydantic.

        Retries independently on JSON parse errors (max_retries) and on
        rate-limit / server-overload errors (rate_limit_retries) with
        exponential backoff starting at rate_limit_backoff seconds.
        """
        last_parse_exc: Exception | None = None
        current_prompt = user_prompt
        json_attempts = 0
        rl_attempts = 0

        while json_attempts < max_retries:
            try:
                raw = self.complete(current_prompt, system_prompt, json_mode=True)
            except RateLimitError as exc:
                rl_attempts += 1
                if rl_attempts > rate_limit_retries:
                    raise
                wait = (
                    exc.retry_after
                    if exc.retry_after is not None
                    else rate_limit_backoff * (2 ** (rl_attempts - 1))
                )
                logger.warning(
                    "[%s] rate limit hit (attempt %d/%d) - waiting %.0fs before retry",
                    self.provider_name, rl_attempts, rate_limit_retries, wait,
                )
                time.sleep(wait)
                continue  # retry the same prompt without incrementing json_attempts

            json_attempts += 1
            logger.debug("[%s] json attempt %d raw response: %.200s", self.provider_name, json_attempts, raw)
            try:
                json_str = _extract_json(raw)
                return model_class.model_validate_json(json_str)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_parse_exc = exc
                logger.warning(
                    "[%s] json attempt %d/%d failed: %s",
                    self.provider_name, json_attempts, max_retries, exc,
                )
                if json_attempts < max_retries:
                    current_prompt = (
                        f"Your previous response had this error:\n{exc}\n\n"
                        f"Fix it and return ONLY valid JSON matching the schema. "
                        f"Original task:\n{user_prompt}"
                    )

        raise LLMError(
            f"[{self.provider_name}] Failed to produce valid JSON after {max_retries} "
            f"attempts. Last error: {last_parse_exc}"
        )


def _extract_json(text: str) -> str:
    """Strip markdown fences and return the first complete JSON object."""
    text = text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()

    start = text.find("{")
    if start == -1:
        return text

    # Walk forward counting balanced braces to find the true end of the object.
    # Using rfind("{") risks capturing trailing text that also contains "}"
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # Fallback: return everything from start (likely malformed JSON — let pydantic report it)
    return text[start:]
