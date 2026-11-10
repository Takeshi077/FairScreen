from __future__ import annotations

from typing import Any

from app.llm.base import ProviderResponseError, ScoreSettings
from app.llm.http_base import HTTPProvider


class GeminiProvider(HTTPProvider):
    """Google Gemini provider via the generateContent REST endpoint.

    Auth: ``x-goog-api-key`` request header (no Bearer prefix required).
    Docs: https://ai.google.dev/api/generate-content
    """

    name = "gemini"

    def _endpoint(self) -> str:
        model = self.model
        base = self.base_url.rstrip("/")
        return f"{base}/models/{model}:generateContent"

    def _headers(self) -> dict[str, str]:
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _payload(self, cv_text: str, prompt: str, settings: ScoreSettings) -> dict[str, Any]:
        full_text = f"{prompt}\n\n{cv_text}"
        return {
            "contents": [{"parts": [{"text": full_text}]}],
            "generationConfig": {
                "temperature": settings.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            candidates = data["candidates"]
            content = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError("Gemini response is missing text content") from exc
        if not isinstance(content, str):
            raise ProviderResponseError("Gemini text content must be a string")
        return content

    def _extract_usage(self, data: dict[str, Any]) -> tuple[int, int] | None:
        meta = data.get("usageMetadata")
        if not isinstance(meta, dict):
            return None
        prompt_tokens = meta.get("promptTokenCount")
        output_tokens = meta.get("candidatesTokenCount")
        if isinstance(prompt_tokens, int) and isinstance(output_tokens, int):
            return prompt_tokens, output_tokens
        return None
