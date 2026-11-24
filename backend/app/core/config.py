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
    redis_url: str | None = None
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None
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
    whatsapp_app_secret: str | None = None
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
    # WhatsApp chats are 1:1 with someone who messaged us first: a short helpful
    # answer beats silence. Medical/safety escalations are never auto-sent.
    ai_min_autosend_confidence_whatsapp: float = 0.65
    ai_low_confidence_escalation_threshold: float = 0.62

    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_opt_in_template_name: str = "rootellect_followup"
    rootellect_whatsapp_number: str = "918679008311"
    rootellect_whatsapp_link: str = "https://wa.me/918679008311"
    # "selected_posts": Instagram comments only get automatic replies/DMs on posts
    # you picked (a campaign targeting the post, or a giveaway). "all_posts": old behaviour.
    instagram_comment_scope: str = "selected_posts"

    shopify_webhook_secret: str | None = None
    shopify_store_domain: str | None = None

    # rootellect.com order events -> WhatsApp order notifications
    rootellect_events_secret: str | None = None
    rootellect_site_url: str = "https://www.rootellect.com"
    whatsapp_business_account_id: str | None = None
    whatsapp_template_language: str = "en"
    whatsapp_order_notifications_enabled: bool = True
    # Scheduled sends wait for this local window (IST by default); order and
    # COD confirmations are sent immediately because the customer just acted.
    whatsapp_send_timezone: str = "Asia/Kolkata"
    whatsapp_quiet_hours_start: int = 21
    whatsapp_quiet_hours_end: int = 9
    cron_secret: str | None = None
    # Scheduled messages this late are dropped instead of sent (a cart reminder
    # hours after the visit reads as spam). Checkout reminders use the shorter limit.
    whatsapp_stale_after_hours: int = 6
    whatsapp_checkout_stale_after_minutes: int = 60
    # Follow-ups (tips, reviews, reorders, cart reminders) are never sent for
    # TEST-* orders created by scripts/send_test_order_events.py.
    whatsapp_skip_test_order_followups: bool = True
    whatsapp_test_order_prefix: str = "TEST-"
    # Run due scheduled sends whenever a WhatsApp webhook arrives (at most this often).
    # Keeps reminders flowing on Vercel even when no external cron is configured.
    whatsapp_opportunistic_dispatch_minutes: int = 10

    # Live-agent handover (WhatsApp). Team phones: comma-separated, with country code.
    live_agent_enabled: bool = True
    # Default team alert number; LIVE_AGENT_TEAM_PHONES on the backend overrides it.
    live_agent_team_phones: str | None = "919818422865"
    live_agent_alert_template: str | None = "rootellect_team_alert_v1"
    live_agent_hours_start: int = 10
    live_agent_hours_end: int = 19
    # Python weekday numbers: 0 = Monday ... 6 = Sunday.
    live_agent_days: str = "0,1,2,3,4,5"
    live_agent_idle_hours: int = 24
    live_agent_realert_minutes: int = 60
    frontend_url: str | None = "https://marketing-ai-gamma-virid.vercel.app"

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


def redis_enabled(settings: Settings | None = None) -> bool:
    """Local ARQ Redis is development-only. Production uses Upstash REST instead."""
    settings = settings or get_settings()
    if settings.environment != "local":
        return False
    url = (settings.redis_url or "").strip()
    if not url:
        return False
    host = urlparse(url).hostname or ""
    if host in {"localhost", "127.0.0.1", "redis"}:
        return True
    return bool(url)


def upstash_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    url = (settings.upstash_redis_rest_url or "").strip()
    token = (settings.upstash_redis_rest_token or "").strip()
    return bool(url and token)


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
