from __future__ import annotations

from typing import Any

from app.llm.base import ProviderResponseError, ScoreSettings
from app.llm.http_base import HTTPProvider


class AnthropicProvider(HTTPProvider):
    name = "anthropic"

    def _endpoint(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/messages"
        return f"{self.base_url}/v1/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _payload(self, cv_text: str, prompt: str, settings: ScoreSettings) -> dict[str, Any]:
        return {
            "model": settings.model or self.model,
            "max_tokens": self.max_tokens,
            "temperature": settings.temperature,
            "system": prompt,
            "messages": [{"role": "user", "content": cv_text}],
        }

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            blocks = data["content"]
        except (KeyError, TypeError) as exc:
            raise ProviderResponseError("Anthropic response is missing content") from exc
        if not isinstance(blocks, list):
            raise ProviderResponseError("Anthropic content must be a list")
        text_parts = [
            block.get("text", "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        content = "".join(text_parts).strip()
        if not content:
            raise ProviderResponseError("Anthropic response has no text block")
        return content

    def _extract_usage(self, data: dict[str, Any]) -> tuple[int, int] | None:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            return input_tokens, output_tokens
        return None
