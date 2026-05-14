from __future__ import annotations

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.services.event_processor import process_webhook_payload


async def process_webhook_job(ctx, log_id: str, payload: dict, channel: str) -> None:
    await process_webhook_payload(log_id, payload, channel)


class WorkerSettings:
    functions = [process_webhook_job]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 50
    job_timeout = 120

