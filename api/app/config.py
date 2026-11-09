from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "fairscreen.db"


def _bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    fairscreen_env: str = "dev"
    database_url: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    fairscreen_seed: int = 2026
    fairscreen_repeats: int = 3
    fairscreen_shortlist_cutoff: float = 7.0
    fairscreen_budget_usd: float = 5.0
    fairscreen_bootstrap: int = 10_000
    fairscreen_permutation: int = 10_000
    fairscreen_cache_enabled: bool = True

    llm_provider: str = "mock"
    llm_temperature: float = 0.2
    llm_max_retries: int = 3
    llm_timeout_seconds: float = 60.0

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_input_price_per_mtok: float = 0.15
    openai_output_price_per_mtok: float = 0.60

    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_model: str = "claude-3-5-haiku-latest"
    anthropic_input_price_per_mtok: float = 0.80
    anthropic_output_price_per_mtok: float = 4.00
    anthropic_max_tokens: int = 400

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def resolved_database_url(self) -> str:
        raw = self.database_url or f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
        if raw.startswith("sqlite:///./"):
            relative = raw.removeprefix("sqlite:///./")
            return f"sqlite:///{(REPO_ROOT / relative).as_posix()}"
        return raw

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_simulated(self) -> bool:
        return self.llm_provider.lower() == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
