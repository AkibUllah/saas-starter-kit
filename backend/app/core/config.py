"""Application settings, loaded from environment variables prefixed ``APP_``."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    app_name: str = "SaaS Starter Kit"
    secret_key: str = Field(min_length=16, default="dev-only-secret-key-change-me-0123456789abcdef")
    database_url: str = "sqlite+aiosqlite:///./saas.db"
    redis_url: str | None = None
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    api_prefix: str = "/api/v1"

    access_token_minutes: int = 15
    refresh_token_days: int = 30
    email_token_hours: int = 24
    invite_token_days: int = 7
    cookie_secure: bool = False
    cookie_domain: str | None = None

    login_rate_limit: int = 10  # attempts per window per IP
    login_rate_window_seconds: int = 300
    api_rate_limit: int = 600  # authenticated requests per minute per principal
    api_rate_window_seconds: int = 60

    billing_webhook_secret: str = "mock-webhook-secret"
    trial_days: int = 14

    log_json: bool = True
    log_level: str = "INFO"

    @field_validator("secret_key")
    @classmethod
    def _no_default_in_production(cls, v: str, info):  # type: ignore[no-untyped-def]
        if (
            info.data.get("env") == "production"
            and v == "dev-only-secret-key-change-me-0123456789abcdef"
        ):
            raise ValueError("APP_SECRET_KEY must be set in production")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
