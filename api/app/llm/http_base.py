from __future__ import annotations

import time
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

import httpx

from app.llm.base import (
    Provider,
    ProviderError,
    ProviderResponseError,
    ProviderResult,
    ScoreSettings,
    estimate_tokens,
    parse_score_response,
)


class HTTPProvider(Provider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        input_price_per_mtok: float,
        output_price_per_mtok: float,
        max_retries: int = 3,
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        max_tokens: int = 400,
    ) -> None:
        if not api_key:
            raise ProviderError("An API key is required for this provider")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.input_price_per_mtok = input_price_per_mtok
        self.output_price_per_mtok = output_price_per_mtok
        self.max_retries = max(0, max_retries)
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self._sleep = sleep_fn
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_seconds)

    @abstractmethod
    def _endpoint(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _payload(self, cv_text: str, prompt: str, settings: ScoreSettings) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _extract_content(self, data: dict[str, Any]) -> str:
        raise NotImplementedError

    def _extract_usage(self, data: dict[str, Any]) -> tuple[int, int] | None:
        return None

    def _post(self, cv_text: str, prompt: str, settings: ScoreSettings) -> dict[str, Any]:
        response = self.client.post(
            self._endpoint(),
            headers=self._headers(),
            json=self._payload(cv_text, prompt, settings),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError(f"Response is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ProviderResponseError("Provider response must be a JSON object")
        return data

    def score(self, cv_text: str, prompt: str, settings: ScoreSettings) -> ProviderResult:
        model = settings.model or self.model
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                data = self._post(cv_text, prompt, settings)
                content = self._extract_content(data)
                score, reason = parse_score_response(content)
                latency_ms = int((time.perf_counter() - started) * 1000)
                usage = self._extract_usage(data)
                if usage:
                    input_tokens, output_tokens = usage
                else:
                    input_tokens = estimate_tokens(prompt) + estimate_tokens(cv_text)
                    output_tokens = estimate_tokens(content)
                cost = (
                    input_tokens / 1_000_000 * self.input_price_per_mtok
                    + output_tokens / 1_000_000 * self.output_price_per_mtok
                )
                return ProviderResult(
                    score=score,
                    reason=reason,
                    latency_ms=latency_ms,
                    cost_usd=round(cost, 8),
                    raw={
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                )
            except (httpx.HTTPError, ProviderResponseError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                self._sleep(min(8.0, 0.5 * (2**attempt)))
        raise ProviderError(
            f"{self.name} failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error

    def estimate_cost(self, cv_text: str, prompt: str, settings: ScoreSettings) -> float:
        input_tokens = estimate_tokens(prompt) + estimate_tokens(cv_text)
        output_tokens = 120
        return (
            input_tokens / 1_000_000 * self.input_price_per_mtok
            + output_tokens / 1_000_000 * self.output_price_per_mtok
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
