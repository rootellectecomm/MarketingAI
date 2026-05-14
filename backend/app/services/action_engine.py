from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import InMemoryTokenBucket
from app.models.entities import ActionAttempt, Comment, SocialEvent
from app.models.enums import ActionStatus, ModerationAction, SendDecision
from app.schemas.ai import AIDecision
from app.services.providers.base import SocialProvider


class ActionEngine:
    def __init__(self) -> None:
        self.rate_bucket = InMemoryTokenBucket(capacity=40, refill_window_seconds=60)

    async def execute(
        self,
        session: AsyncSession,
        provider: SocialProvider,
        event: SocialEvent,
        comment: Comment | None,
        decision: AIDecision,
    ) -> list[ActionAttempt]:
        attempts: list[ActionAttempt] = []
        if comment and decision.moderation_action == ModerationAction.hide:
            attempts.append(await self._run_comment_action(session, provider, event, comment, "hide_comment", decision))

        if decision.send_decision != SendDecision.send:
            return attempts

        if not self.rate_bucket.allow(f"{event.provider}:{event.actor_id or 'unknown'}"):
            attempts.append(
                ActionAttempt(
                    social_event_id=event.id,
                    action_type="rate_limited",
                    provider=event.provider,
                    idempotency_key=f"{event.provider_event_id}:rate_limited",
                    status=ActionStatus.skipped,
                    request_json={"reason": "provider or actor rate limit"},
                )
            )
            session.add(attempts[-1])
            return attempts

        if comment and decision.public_reply:
            attempts.append(
                await self._run_comment_action(session, provider, event, comment, "reply_to_comment", decision)
            )
            comment.replied = attempts[-1].status == ActionStatus.sent

        if comment and decision.private_dm:
            attempts.append(
                await self._run_comment_action(session, provider, event, comment, "send_private_reply", decision)
            )
            comment.private_replied = attempts[-1].status == ActionStatus.sent
        elif event.actor_id and decision.private_dm:
            attempts.append(await self._run_dm_action(session, provider, event, event.actor_id, decision))

        return attempts

    async def _run_comment_action(
        self,
        session: AsyncSession,
        provider: SocialProvider,
        event: SocialEvent,
        comment: Comment,
        action_type: str,
        decision: AIDecision,
    ) -> ActionAttempt:
        idempotency_key = f"{event.provider_event_id}:{action_type}"
        existing = await session.scalar(select(ActionAttempt).where(ActionAttempt.idempotency_key == idempotency_key))
        if existing:
            return existing

        message = decision.public_reply if action_type == "reply_to_comment" else decision.private_dm
        attempt = ActionAttempt(
            social_event_id=event.id,
            action_type=action_type,
            provider=event.provider,
            idempotency_key=idempotency_key,
            status=ActionStatus.pending,
            request_json={"comment_id": comment.provider_comment_id, "message": message},
            attempts=1,
        )
        if action_type == "hide_comment":
            result = await provider.hide_comment(comment.provider_comment_id)
            comment.hidden = result.ok
        elif action_type == "send_private_reply":
            result = await provider.send_private_reply(comment.provider_comment_id, message)
        else:
            result = await provider.reply_to_comment(comment.provider_comment_id, message)
        attempt.status = ActionStatus.sent if result.ok else ActionStatus.failed
        attempt.response_json = result.response
        attempt.error_message = result.error
        session.add(attempt)
        return attempt

    async def _run_dm_action(
        self,
        session: AsyncSession,
        provider: SocialProvider,
        event: SocialEvent,
        recipient_id: str,
        decision: AIDecision,
    ) -> ActionAttempt:
        idempotency_key = f"{event.provider_event_id}:send_dm"
        existing = await session.scalar(select(ActionAttempt).where(ActionAttempt.idempotency_key == idempotency_key))
        if existing:
            return existing

        attempt = ActionAttempt(
            social_event_id=event.id,
            action_type="send_dm",
            provider=event.provider,
            idempotency_key=idempotency_key,
            request_json={"recipient_id": recipient_id, "message": decision.private_dm},
            attempts=1,
        )
        result = await provider.send_dm(recipient_id, decision.private_dm)
        attempt.status = ActionStatus.sent if result.ok else ActionStatus.failed
        attempt.response_json = result.response
        attempt.error_message = result.error
        session.add(attempt)
        return attempt

