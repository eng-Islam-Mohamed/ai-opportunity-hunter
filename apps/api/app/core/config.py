from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "AI Opportunity Hunter"
    api_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    database_url: str = "sqlite+aiosqlite:///./opportunity_hunter.db"
    log_level: str = "INFO"
    execution_backend: Literal["direct", "celery_worker"] = "direct"

    llm_provider: Literal["fixture", "openrouter"] = "fixture"
    llm_api_key: SecretStr | None = None
    llm_base_url: AnyHttpUrl = AnyHttpUrl("https://openrouter.ai/api/v1")
    llm_model_analysis: str = "deepseek/deepseek-v4-pro"
    llm_model_extraction: str = "deepseek/deepseek-v4-pro"
    llm_model_copy: str = "deepseek/deepseek-v4-pro"
    enable_llm_analysis: bool = False
    llm_timeout_seconds: float = Field(default=90, gt=0, le=300)

    discovery_provider: str = "fixture"
    audit_provider: str = "fixture"
    sheets_provider: str = "fixture"
    google_maps_api_key: SecretStr | None = None
    google_service_account_json: SecretStr | None = None
    google_oauth_client_secrets_file: str | None = None
    google_oauth_token_file: str = ".secrets/google-oauth-token.json"
    google_oauth_client_secrets_json: SecretStr | None = None
    google_oauth_token_json: SecretStr | None = None
    google_sheets_user_email: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    export_directory: str = "artifacts/exports"
    backend_internal_token: SecretStr | None = None
    app_auth_secret: SecretStr | None = None
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    allowed_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @model_validator(mode="after")
    def validate_enabled_features(self) -> Settings:
        if self.enable_llm_analysis and self.llm_provider == "openrouter" and not self.llm_api_key:
            raise ValueError("LLM_API_KEY is required when OpenRouter analysis is enabled")
        if self.app_env == "production" and not self.backend_internal_token:
            raise ValueError("BACKEND_INTERNAL_TOKEN is required in production")
        if self.app_env == "production" and not self.app_auth_secret:
            raise ValueError("APP_AUTH_SECRET is required in production")
        return self

    def host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
