from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import Provider, ProviderConfigurationError
from app.llm.mock import MockProvider, simulated_model_names
from app.llm.openai_provider import OpenAICompatibleProvider

SUPPORTED_PROVIDERS = ("mock", "openai", "anthropic")


def default_models(provider: str, settings: Settings | None = None) -> list[str]:
    config = settings or get_settings()
    lowered = provider.lower()
    if lowered == "mock":
        return simulated_model_names()
    if lowered == "openai":
        return [config.openai_model]
    if lowered == "anthropic":
        return [config.anthropic_model]
    raise ProviderConfigurationError(f"Unsupported provider: {provider}")


def build_provider(
    provider_name: str | None = None,
    model_name: str | None = None,
    settings: Settings | None = None,
) -> Provider:
    config = settings or get_settings()
    name = (provider_name or config.llm_provider).lower()
    if name == "mock":
        return MockProvider(model_name or simulated_model_names()[0])
    if name == "openai":
        if not config.openai_api_key:
            raise ProviderConfigurationError(
                "OPENAI_API_KEY is not set. Use mock mode for a keyless demo."
            )
        return OpenAICompatibleProvider(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model=model_name or config.openai_model,
            input_price_per_mtok=config.openai_input_price_per_mtok,
            output_price_per_mtok=config.openai_output_price_per_mtok,
            max_retries=config.llm_max_retries,
            timeout_seconds=config.llm_timeout_seconds,
        )
    if name == "anthropic":
        if not config.anthropic_api_key:
            raise ProviderConfigurationError(
                "ANTHROPIC_API_KEY is not set. Use mock mode for a keyless demo."
            )
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            base_url=config.anthropic_base_url,
            model=model_name or config.anthropic_model,
            input_price_per_mtok=config.anthropic_input_price_per_mtok,
            output_price_per_mtok=config.anthropic_output_price_per_mtok,
            max_retries=config.llm_max_retries,
            timeout_seconds=config.llm_timeout_seconds,
            max_tokens=config.anthropic_max_tokens,
        )
    raise ProviderConfigurationError(f"Unsupported provider: {provider_name}")
