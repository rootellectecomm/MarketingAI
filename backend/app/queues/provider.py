from __future__ import annotations

from typing import Literal

import structlog

from app.core.config import get_settings, redis_enabled, upstash_enabled

logger = structlog.get_logger(__name__)

QueueProvider = Literal["upstash", "local_redis", "inline"]
_logged_provider: QueueProvider | None = None


def get_queue_provider() -> QueueProvider:
    settings = get_settings()
    if upstash_enabled(settings):
        return "upstash"
    if redis_enabled(settings):
        return "local_redis"
    return "inline"


def log_queue_provider_selected() -> QueueProvider:
    global _logged_provider
    provider = get_queue_provider()
    if _logged_provider != provider:
        logger.info("redis provider selected", provider=provider, environment=get_settings().environment)
        _logged_provider = provider
    return provider


def reset_queue_provider_log() -> None:
    global _logged_provider
    _logged_provider = None
