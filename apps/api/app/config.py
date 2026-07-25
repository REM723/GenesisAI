from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env. See .env.example."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"
    log_level: str = "INFO"

    database_url: str = "postgresql://genesis:genesis@localhost:5432/genesis"
    redis_url: str = "redis://localhost:6379/0"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # Auth (§7)
    jwt_secret: str = "change-me"  # noqa: S105 - dev default; real secret via env
    jwt_access_ttl: int = 900  # seconds
    jwt_refresh_ttl: int = 1209600  # seconds

    # AES-GCM key for provider API keys (FR-14): base64-encoded 32 bytes.
    genesis_encryption_key: str = ""


@lru_cache
def get_settings() -> Settings:
    # ponytail: lru_cache memoises settings parsing, not a live connection — DI-safe.
    return Settings()
