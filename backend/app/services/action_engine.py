from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import InMemoryTokenBucket
from app.models.entities import ActionAttempt, Comment, Conversation, Lead, Message, SocialEvent
from app.models.enums import ActionStatus, ModerationAction, SendDecision
from app.schemas.ai import AIDecision
from app.services.provider_factory import get_whatsapp_provider
from app.services.providers.base import SocialProvider


@dataclass(slots=True)
class ActionContext:
    conversation: Conversation | None = None
    lead: Lead | None = None
    channel: str = "instagram"
    allow_whatsapp_followup: bool = False


class ActionEngine:
    def __init__(self) -> None:
        self.rate_bucket = InMemoryTokenBucket(capacity=40, refill_window_seconds=60)
        self.settings = get_settings()

    async def execute(
        self,
        session: AsyncSession,
        provider: SocialProvider,
        event: SocialEvent,
        comment: Comment | None,
        decision: AIDecision,
        context: ActionContext | None = None,
    ) -> list[ActionAttempt]:
        context = context or ActionContext()
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
            if comment.replied:
                await self._persist_outbound(session, context, decision.public_reply, "instagram_comment")

        if comment and decision.private_dm:
            attempts.append(
                await self._run_comment_action(session, provider, event, comment, "send_private_reply", decision)
            )
            comment.private_replied = attempts[-1].status == ActionStatus.sent
            if comment.private_replied:
                await self._persist_outbound(session, context, decision.private_dm, "instagram_dm")
        elif event.actor_id and decision.private_dm:
            attempts.append(await self._run_dm_action(session, provider, event, event.actor_id, decision))
            if attempts[-1].status == ActionStatus.sent:
                await self._persist_outbound(session, context, decision.private_dm, "instagram_dm")

        if context.allow_whatsapp_followup and decision.whatsapp_followup and context.lead:
            wa_attempt = await self._run_whatsapp_followup(session, event, context.lead, decision.whatsapp_followup)
            if wa_attempt:
                attempts.append(wa_attempt)

        return attempts

    async def _persist_outbound(
        self,
        session: AsyncSession,
        context: ActionContext,
        body: str,
        channel: str,
    ) -> None:
        if not context.conversation or not body:
            return
        session.add(
            Message(
                conversation_id=context.conversation.id,
                direction="outbound",
                body=body,
                channel=channel,
                metadata_json={"automated": True},
            )
        )

    async def _run_whatsapp_followup(
        self,
        session: AsyncSession,
        event: SocialEvent,
        lead: Lead,
        message: str,
    ) -> ActionAttempt | None:
        if not lead.phone:
            return None

        idempotency_key = f"{event.provider_event_id}:whatsapp_followup"
        existing = await session.scalar(select(ActionAttempt).where(ActionAttempt.idempotency_key == idempotency_key))
        if existing:
            return existing

        wa_provider = get_whatsapp_provider()
        attempt = ActionAttempt(
            social_event_id=event.id,
            action_type="send_whatsapp_text",
            provider=event.provider,
            idempotency_key=idempotency_key,
            request_json={"phone": lead.phone, "message": message},
            attempts=1,
        )

        if lead.whatsapp_opt_in:
            result = await wa_provider.send_whatsapp_text(lead.phone, message)
        else:
            result = await wa_provider.send_whatsapp_template(
                lead.phone,
                self.settings.whatsapp_opt_in_template_name,
                [message[:200]],
            )
            if result.ok:
                lead.whatsapp_opt_in = True

        attempt.status = ActionStatus.sent if result.ok else ActionStatus.failed
        attempt.response_json = result.response
        attempt.error_message = result.error
        session.add(attempt)
        return attempt

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
        if existing and existing.status == ActionStatus.sent:
            return existing

        message = decision.public_reply if action_type == "reply_to_comment" else decision.private_dm
        attempt = existing or ActionAttempt(
            social_event_id=event.id,
            action_type=action_type,
            provider=event.provider,
            idempotency_key=idempotency_key,
            attempts=0,
        )
        attempt.social_event_id = event.id
        attempt.status = ActionStatus.pending
        attempt.request_json = {"comment_id": comment.provider_comment_id, "message": message}
        attempt.attempts += 1
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
        if not existing:
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
        if existing and existing.status == ActionStatus.sent:
            return existing

        attempt = existing or ActionAttempt(
            social_event_id=event.id,
            action_type="send_dm",
            provider=event.provider,
            idempotency_key=idempotency_key,
            attempts=0,
        )
        attempt.social_event_id = event.id
        attempt.request_json = {"recipient_id": recipient_id, "message": decision.private_dm}
        attempt.attempts += 1
        result = await provider.send_dm(recipient_id, decision.private_dm)
        attempt.status = ActionStatus.sent if result.ok else ActionStatus.failed
        attempt.response_json = result.response
        attempt.error_message = result.error
        if not existing:
            session.add(attempt)
        return attempt
