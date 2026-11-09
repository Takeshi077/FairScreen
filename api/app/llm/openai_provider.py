from __future__ import annotations

from typing import Any

from app.llm.base import ProviderResponseError, ScoreSettings
from app.llm.http_base import HTTPProvider


class OpenAICompatibleProvider(HTTPProvider):
    name = "openai"

    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, cv_text: str, prompt: str, settings: ScoreSettings) -> dict[str, Any]:
        return {
            "model": settings.model or self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": cv_text},
            ],
            "temperature": settings.temperature,
            "max_tokens": self.max_tokens,
        }

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            choices = data["choices"]
            content = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError("OpenAI response is missing message content") from exc
        if not isinstance(content, str):
            raise ProviderResponseError("OpenAI message content must be a string")
        return content

    def _extract_usage(self, data: dict[str, Any]) -> tuple[int, int] | None:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
            return prompt_tokens, completion_tokens
        return None
