"""
Application configuration loaded from environment variables.

All secrets and API keys are sourced from environment variables or .env file.
Never hardcode sensitive values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root if present
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


def _env_str(name: str, default: str | None = None) -> str:
    val = os.environ.get(name)
    if val is None:
        if default is None:
            raise ValueError(f"Required environment variable '{name}' is not set")
        return default
    return val


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # All API keys are optional — app falls back to demo/seed mode when unset.
    # The demo mode with 3 seed cards works with no keys at all.
    openai_api_key: str = field(default_factory=lambda: _env_str("OPENAI_API_KEY", ""))
    supabase_url: str = field(default_factory=lambda: _env_str("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: _env_str("SUPABASE_KEY", ""))
    newsapi_key: str = field(default_factory=lambda: _env_str("NEWSAPI_KEY", ""))
    guardian_api_key: str = field(default_factory=lambda: _env_str("GUARDIAN_API_KEY", ""))
    hf_api_token: str = field(default_factory=lambda: _env_str("HF_API_TOKEN", ""))
    tavily_api_key: str = field(default_factory=lambda: _env_str("TAVILY_API_KEY", ""))

    # LangSmith
    langchain_api_key: str = field(default_factory=lambda: _env_str("LANGCHAIN_API_KEY", ""))
    langchain_tracing: bool = os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langchain_project: str = _env_str("LANGCHAIN_PROJECT", "locallens")

    # Streamlit
    streamlit_port: int = _env_int("STREAMLIT_SERVER_PORT", 8501)

    # Auth
    locallens_username: str = field(default_factory=lambda: _env_str("LOCALLENS_USERNAME", "admin"))
    locallens_password: str = field(default_factory=lambda: _env_str("LOCALLENS_PASSWORD", "locallens"))

    # Logging
    log_level: str = _env_str("LOG_LEVEL", "INFO")

    # App constants
    default_locale: str = "san-diego-ca"
    cache_hours: int = 6
    similarity_threshold: float = 0.35
    embedding_dim: int = 1024  # BGE-M3 dimension

    # Supported locales (city-slug: display name)
    supported_locales: tuple[tuple[str, str], ...] = (
        ("san-diego-ca", "San Diego, CA"),
        ("los-angeles-ca", "Los Angeles, CA"),
        ("san-francisco-ca", "San Francisco, CA"),
        ("new-york-ny", "New York, NY"),
        ("chicago-il", "Chicago, IL"),
        ("austin-tx", "Austin, TX"),
        ("seattle-wa", "Seattle, WA"),
        ("miami-fl", "Miami, FL"),
        ("denver-co", "Denver, CO"),
        ("portland-or", "Portland, OR"),
    )


settings = Settings()

# Export singleton for convenience
__all__ = ["settings", "Settings"]
