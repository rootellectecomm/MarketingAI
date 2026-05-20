from __future__ import annotations

from datetime import timedelta

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.services.event_processor import process_webhook_payload
from app.services.funnel_runner import FunnelRunner
from app.services.retention_jobs import RetentionJobRunner


async def process_webhook_job(ctx, log_id: str, payload: dict, channel: str) -> None:
    await process_webhook_payload(log_id, payload, channel)


async def process_due_funnel_steps(ctx) -> None:
    await FunnelRunner().process_due_steps()


async def process_conversation_recovery(ctx) -> None:
    await RetentionJobRunner().recover_stale_conversations()


async def process_retention_touchpoints(ctx) -> None:
    await RetentionJobRunner().process_touchpoints()


class WorkerSettings:
    functions = [
        process_webhook_job,
        process_due_funnel_steps,
        process_conversation_recovery,
        process_retention_touchpoints,
    ]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 50
    job_timeout = 180
    max_tries = 3
    retry_jobs = True
    cron_jobs = [
        cron(process_due_funnel_steps, minute={0, 15, 30, 45}),
        cron(process_conversation_recovery, hour={9, 15, 21}, minute=0),
        cron(process_retention_touchpoints, hour=10, minute=30),
    ]
