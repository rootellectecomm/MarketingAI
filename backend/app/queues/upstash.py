from __future__ import annotations

import asyncio
import json
import uuid
from functools import lru_cache

import structlog

from app.core.config import get_settings, upstash_enabled
from app.services.event_processor import process_webhook_payload

logger = structlog.get_logger(__name__)
QUEUE_KEY = "rootellect:webhook:jobs"


@lru_cache
def get_upstash_client():
    settings = get_settings()
    if not upstash_enabled(settings):
        return None
    from upstash_redis import Redis

    return Redis(url=settings.upstash_redis_rest_url, token=settings.upstash_redis_rest_token)


def clear_upstash_client_cache() -> None:
    get_upstash_client.cache_clear()


async def enqueue_upstash_webhook_job(log_id: str, payload: dict, channel: str) -> str | None:
    client = get_upstash_client()
    if client is None:
        return None

    job_id = str(uuid.uuid4())
    job = json.dumps({"job_id": job_id, "log_id": log_id, "payload": payload, "channel": channel})
    try:
        await asyncio.to_thread(client.rpush, QUEUE_KEY, job)
        logger.info("upstash_webhook_enqueued", job_id=job_id, log_id=log_id, channel=channel)
        return job_id
    except Exception as exc:
        logger.warning("queue_enqueue_failed", log_id=log_id, channel=channel, backend="upstash", error=str(exc))
        return None


async def drain_upstash_webhook_jobs(max_jobs: int = 10) -> int:
    client = get_upstash_client()
    if client is None:
        return 0

    processed = 0
    for _ in range(max_jobs):
        raw_job = await asyncio.to_thread(client.lpop, QUEUE_KEY)
        if not raw_job:
            break
        try:
            job = json.loads(raw_job)
            await process_webhook_payload(
                job["log_id"],
                job["payload"],
                job["channel"],
            )
            processed += 1
        except Exception as exc:
            logger.exception(
                "upstash_webhook_job_failed",
                error=str(exc),
                raw_job=raw_job,
            )
    return processed
