from __future__ import annotations

from collections import defaultdict

import httpx
import pytest

from app.cvs.anonymizer import anonymize_cv
from app.cvs.generator import generate_dataset
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import (
    Budget,
    BudgetExceededError,
    ProviderConfigurationError,
    ProviderError,
    ProviderResponseError,
    ScoreSettings,
    parse_score_response,
)
from app.llm.cache import get_cached, make_cache_parts, store_cached
from app.llm.mock import MockProfile, MockProvider
from app.llm.openai_provider import OpenAICompatibleProvider
from app.llm.registry import build_provider


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(seed=2026, bases_per_role=6)


def _settings(model="test-model", mitigation="none", repeat=0) -> ScoreSettings:
    return ScoreSettings(
        model=model,
        temperature=0.2,
        provider="mock",
        prompt_version="screening-v1",
        mitigation=mitigation,
        repeat=repeat,
    )


def test_mock_is_deterministic(dataset):
    provider = MockProvider("Mock-Screen-A")
    variant = dataset[0].variants[0]
    first = provider.score(variant.text, "prompt", _settings("Mock-Screen-A"))
    second = provider.score(variant.text, "prompt", _settings("Mock-Screen-A"))
    assert first.score == second.score
    assert first.reason == second.reason
    assert first.raw["simulated"] is True


def test_mock_repeats_differ(dataset):
    provider = MockProvider("Mock-Screen-A", MockProfile(name="test", noise=0.2, bias_scale=0))
    variant = dataset[0].variants[0]
    scores = {
        provider.score(variant.text, "prompt", _settings("x", repeat=repeat)).score
        for repeat in range(4)
    }
    assert len(scores) == 4


def test_mock_tiers_are_ordered(dataset):
    provider = MockProvider("test", MockProfile(name="test", noise=0, bias_scale=0))
    by_tier: dict[str, list[float]] = defaultdict(list)
    for spec in dataset:
        for variant in spec.variants:
            result = provider.score(variant.text, "prompt", _settings("test"))
            by_tier[spec.tier].append(result.score)
    means = {tier: sum(values) / len(values) for tier, values in by_tier.items()}
    assert means["strong"] > means["average"] + 2.0
    assert means["average"] > means["weak"] + 1.0


def test_planted_gender_bias_is_exact_without_noise(dataset):
    provider = MockProvider(
        "test",
        MockProfile(
            name="test",
            noise=0,
            bias_scale=1.0,
            group_bias={"gender": {"woman": -0.5, "man": 0.0}, "name_origin": {}, "age": {}},
        ),
    )
    gender = {variant.group_name: variant for variant in dataset[0].variants_for("gender")}
    woman = provider.score(gender["woman"].text, "prompt", _settings("test"))
    man = provider.score(gender["man"].text, "prompt", _settings("test"))
    assert woman.score - man.score == pytest.approx(-0.5, abs=1e-9)


def test_mitigations_reduce_planted_gap(dataset):
    provider = MockProvider(
        "test",
        MockProfile(
            name="test",
            noise=0,
            bias_scale=1.0,
            group_bias={"gender": {"woman": -0.5, "man": 0.0}, "name_origin": {}, "age": {}},
        ),
    )
    gender = {variant.group_name: variant for variant in dataset[0].variants_for("gender")}
    baseline_gap = (
        provider.score(gender["woman"].text, "p1", _settings("test", "none")).score
        - provider.score(gender["man"].text, "p1", _settings("test", "none")).score
    )
    skills_gap = (
        provider.score(gender["woman"].text, "p2", _settings("test", "skills_only")).score
        - provider.score(gender["man"].text, "p2", _settings("test", "skills_only")).score
    )
    anon_woman = anonymize_cv(gender["woman"].text)
    anon_man = anonymize_cv(gender["man"].text)
    anon_gap = (
        provider.score(anon_woman, "p3", _settings("test", "anonymization")).score
        - provider.score(anon_man, "p3", _settings("test", "anonymization")).score
    )
    assert baseline_gap == pytest.approx(-0.5)
    assert abs(skills_gap) < abs(baseline_gap)
    assert anon_gap == pytest.approx(0.0)


def test_anonymized_variants_score_identically(dataset):
    provider = MockProvider("Mock-Screen-C")
    gender = dataset[3].variants_for("gender")
    scores = {
        provider.score(
            anonymize_cv(variant.text),
            "prompt",
            _settings("Mock-Screen-C", "combined", repeat=1),
        ).score
        for variant in gender
    }
    assert len(scores) == 1


def test_parse_score_response_accepts_valid_json_and_fences():
    assert parse_score_response('{"score": 7.5, "reason": "Solid evidence"}') == (
        7.5,
        "Solid evidence",
    )
    fenced = '```json\n{"score": 4, "reason": "Limited evidence"}\n```'
    assert parse_score_response(fenced) == (4.0, "Limited evidence")


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        '{"score": 11, "reason": "too high"}',
        '{"score": -1, "reason": "too low"}',
        '{"score": true, "reason": "boolean"}',
        '{"score": "7", "reason": "string score"}',
        '{"score": NaN, "reason": "not finite"}',
        '{"score": 7}',
        '{"score": 7, "reason": ""}',
        '["not", "an", "object"]',
    ],
)
def test_parse_score_response_rejects_invalid(payload):
    with pytest.raises(ProviderResponseError):
        parse_score_response(payload)


def test_openai_compatible_stubbed_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        body = request.read().decode()
        seen["body"] = body
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"score": 8.1, "reason": "Strong fit"}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        input_price_per_mtok=1.0,
        output_price_per_mtok=2.0,
        client=client,
        sleep_fn=lambda _: None,
    )
    result = provider.score("cv", "prompt", _settings("test-model"))
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert "test-model" in seen["body"]
    assert result.score == 8.1
    assert result.cost_usd == pytest.approx(100 / 1e6 + 40 / 1e6)


def test_anthropic_stubbed_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": '{"score": 6.4, "reason": "Mixed"}'}],
                "usage": {"input_tokens": 120, "output_tokens": 30},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(
        api_key="anthropic-key",
        base_url="https://api.anthropic.test",
        model="claude-test",
        input_price_per_mtok=0.8,
        output_price_per_mtok=4.0,
        client=client,
        sleep_fn=lambda _: None,
    )
    result = provider.score("cv", "prompt", _settings("claude-test"))
    assert seen["url"] == "https://api.anthropic.test/v1/messages"
    assert seen["key"] == "anthropic-key"
    assert seen["version"] == "2023-06-01"
    assert result.score == 6.4
    assert result.raw["model"] == "claude-test"


def test_real_provider_retries_malformed_then_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        content = "not json" if calls["count"] == 1 else '{"score": 5, "reason": "ok"}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        api_key="key",
        base_url="https://example.test/v1",
        model="m",
        input_price_per_mtok=1,
        output_price_per_mtok=1,
        client=client,
        max_retries=2,
        sleep_fn=lambda _: None,
    )
    result = provider.score("cv", "prompt", _settings("m"))
    assert result.score == 5.0
    assert calls["count"] == 2


def test_real_provider_fails_after_retries():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        api_key="key",
        base_url="https://example.test/v1",
        model="m",
        input_price_per_mtok=1,
        output_price_per_mtok=1,
        client=client,
        max_retries=2,
        sleep_fn=lambda _: None,
    )
    with pytest.raises(ProviderError):
        provider.score("cv", "prompt", _settings("m"))
    assert calls["count"] == 3


def test_real_provider_retries_http_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(500, json={"error": "boom"})
        content = '{"score": 7, "reason": "ok"}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        api_key="key",
        base_url="https://example.test/v1",
        model="m",
        input_price_per_mtok=1,
        output_price_per_mtok=1,
        client=client,
        max_retries=2,
        sleep_fn=lambda _: None,
    )
    assert provider.score("cv", "prompt", _settings("m")).score == 7.0
    assert calls["count"] == 2


def test_registry_requires_api_key(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(ProviderConfigurationError):
        build_provider("openai")
    get_settings.cache_clear()
    assert build_provider("mock").name == "mock"


def test_registry_builds_real_provider(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "abc")
    get_settings.cache_clear()
    provider = build_provider("openai", "gpt-test")
    assert provider.name == "openai"
    provider.close()
    get_settings.cache_clear()


def test_cache_roundtrip_and_key_parts(clean_db, db):
    key1, variant_key, prompt_hash = make_cache_parts(
        "mock", "m", "screening-v1", "cv text", "prompt", 0, 0.2
    )
    key2, _, _ = make_cache_parts("mock", "m", "screening-v1", "cv text", "prompt", 0, 0.2)
    key3, _, _ = make_cache_parts("mock", "m", "screening-v1", "cv text", "prompt", 1, 0.2)
    assert key1 == key2
    assert key1 != key3
    assert get_cached(db, key1) is None
    from app.llm.base import ProviderResult

    store_cached(
        db,
        cache_key=key1,
        variant_key=variant_key,
        prompt_hash=prompt_hash,
        provider="mock",
        model="m",
        prompt_version="screening-v1",
        repeat=0,
        result=ProviderResult(score=7.0, reason="cached", latency_ms=3, cost_usd=0.0),
    )
    db.flush()
    cached = get_cached(db, key1)
    assert cached is not None
    assert cached.score == 7.0


def test_budget_guard():
    budget = Budget(cap_usd=1.0)
    budget.ensure_can_spend(0.5)
    budget.charge(0.5)
    with pytest.raises(BudgetExceededError):
        budget.ensure_can_spend(0.6)
    budget.ensure_can_spend(0.5)
    assert budget.remaining == pytest.approx(0.5)
