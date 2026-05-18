from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Rootellect AI Automation"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    backend_cors_origins: str = "http://localhost:3000"
    public_base_url: AnyHttpUrl | None = None

    database_url: str = "postgresql+asyncpg://rootellect:rootellect@localhost:5432/rootellect"
    redis_url: str = "redis://localhost:6379/0"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "rootellect_knowledge"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    encryption_secret: str = "change-me-32-byte-secret"

    admin_email: str = "admin@rootellect.local"
    admin_password: str = "ChangeMe123!"

    meta_verify_token: str = "rootellect-webhook-token"
    meta_app_id: str | None = None
    meta_app_secret: str = "replace-meta-app-secret"
    meta_graph_version: str = "v25.0"
    meta_oauth_redirect_uri: str | None = None
    meta_connect_success_url: str | None = None
    meta_oauth_scopes: list[str] = Field(
        default_factory=lambda: [
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_metadata",
            "pages_manage_engagement",
            "instagram_basic",
            "instagram_manage_comments",
            "instagram_manage_messages",
        ]
    )
    provider_mode: Literal["mock", "instagram_professional", "facebook_page_backed"] = "mock"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    ai_min_autosend_confidence: float = 0.78
    ai_low_confidence_escalation_threshold: float = 0.62

    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_opt_in_template_name: str = "rootellect_followup"

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @field_validator("meta_oauth_scopes", mode="before")
    @classmethod
    def split_meta_scopes(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [scope.strip() for scope in value.split(",") if scope.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_cors_origins(settings: Settings | None = None) -> list[str]:
    value = (settings or get_settings()).backend_cors_origins
    return [origin.strip() for origin in value.split(",") if origin.strip()]
