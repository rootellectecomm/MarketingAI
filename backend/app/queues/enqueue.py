from __future__ import annotations

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def enqueue_webhook_job(log_id: str, payload: dict, channel: str) -> str | None:
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job("process_webhook_job", log_id, payload, channel)
        return job.job_id if job else None
    except Exception as exc:
        logger.exception("arq_enqueue_failed", log_id=log_id, channel=channel, error=str(exc))
        return None
