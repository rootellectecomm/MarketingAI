import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import AnyHttpUrl
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

    admin_email: str = "admin@rootellect.com"
    admin_password: str = "ChangeMe123!"
    reset_admin_secret: str = "rootellect-reset-secret"

    meta_verify_token: str = "rootellect-webhook-token"
    meta_app_id: str | None = None
    meta_app_secret: str = "replace-meta-app-secret"
    meta_graph_version: str = "v25.0"
    meta_oauth_redirect_uri: str | None = None
    meta_connect_success_url: str | None = None
    meta_login_config_id: str | None = None
    meta_oauth_scopes: str = (
        "pages_show_list,"
        "pages_read_engagement,"
        "pages_manage_metadata,"
        "pages_manage_engagement,"
        "business_management,"
        "instagram_basic,"
        "instagram_manage_comments,"
        "instagram_manage_messages"
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

    shopify_webhook_secret: str | None = None
    shopify_store_domain: str | None = None

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _origin_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def get_cors_origins(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    origins: list[str] = []

    value = settings.backend_cors_origins
    if value:
        origins.extend(origin.strip() for origin in str(value).split(",") if origin.strip())
    else:
        origins.append("http://localhost:3000")

    for candidate in (_origin_from_url(settings.meta_connect_success_url), _origin_from_url(settings.public_base_url)):
        if candidate and candidate not in origins:
            origins.append(candidate)

    return origins


def get_cors_origin_regex(settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    if settings.environment == "production" or os.getenv("VERCEL"):
        return r"https://.*\.vercel\.app$"
    return None


def get_meta_oauth_scopes(settings: Settings | None = None) -> list[str]:
    value = (settings or get_settings()).meta_oauth_scopes
    if not value:
        return []
    return [scope.strip() for scope in str(value).split(",") if scope.strip()]
