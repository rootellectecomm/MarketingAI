from __future__ import annotations

from datetime import UTC, datetime
from random import sample

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    ActionAttempt,
    AutomationEventLog,
    Comment,
    GiveawayAutomation,
    GiveawayContent,
    GiveawayParticipant,
    Lead,
    SocialEvent,
)
from app.models.enums import ActionStatus, EventType
from app.services.meta_oauth import get_active_page_access_token
from app.services.normalization import normalize_comment_text
from app.services.provider_factory import get_instagram_provider


class GiveawayProcessor:
    async def handle_comment(
        self,
        session: AsyncSession,
        event: SocialEvent,
        comment: Comment | None,
        lead: Lead,
    ) -> bool:
        if not comment or event.event_type != EventType.instagram_comment:
            return False

        automation, trigger = await self._match_automation(session, comment)
        if not automation:
            return False

        existing = await session.scalar(
            select(GiveawayParticipant).where(
                GiveawayParticipant.automation_id == automation.id,
                GiveawayParticipant.instagram_user_id == (event.actor_id or comment.username or "unknown"),
            )
        )
        if existing:
            await self._log(session, automation.id, existing.id, "duplicate_comment", "skipped", comment.text)
            return True

        if await self._reply_limit_reached(session, automation):
            await self._log(session, automation.id, None, "reply_limit_reached", "skipped", str(automation.reply_limit))
            return True

        participant = GiveawayParticipant(
            automation_id=automation.id,
            comment_id=comment.id,
            social_event_id=event.id,
            lead_id=lead.id,
            instagram_user_id=event.actor_id or comment.username or "unknown",
            instagram_username=comment.username,
            comment_text=comment.text,
            trigger_matched=trigger,
            status="commented",
            tags=["giveaway", automation.name],
        )
        session.add(participant)
        await session.flush()

        provider = get_instagram_provider(access_token=await get_active_page_access_token(session))
        public_reply = self._public_reply(automation)
        public_attempt = await self._run_comment_action(
            session,
            event,
            provider,
            comment,
            "giveaway_public_reply",
            public_reply,
        )
        if public_attempt.status == ActionStatus.sent:
            participant.status = "public_reply_sent"
            comment.replied = True

        dm_text = self._entry_dm(automation)
        dm_attempt = await self._run_comment_action(
            session,
            event,
            provider,
            comment,
            "giveaway_dm_follow_card",
            dm_text,
        )
        if dm_attempt.status == ActionStatus.sent:
            participant.status = "dm_sent"
            comment.private_replied = True
        else:
            participant.error_message = dm_attempt.error_message

        await self._log(
            session,
            automation.id,
            participant.id,
            "participant_processed",
            participant.status,
            f"trigger={trigger}",
        )
        return True

    async def handle_follow_confirmation(self, session: AsyncSession, event: SocialEvent) -> bool:
        if event.event_type != EventType.instagram_dm:
            return False

        text = normalize_comment_text(str(event.payload.get("text") or event.payload.get("message") or "")).lower()
        if not text:
            return False

        result = await session.execute(
            select(GiveawayParticipant, GiveawayAutomation)
            .join(GiveawayAutomation, GiveawayAutomation.id == GiveawayParticipant.automation_id)
            .where(
                GiveawayParticipant.instagram_user_id == (event.actor_id or ""),
                GiveawayAutomation.status == "active",
                GiveawayParticipant.reward_sent.is_(False),
            )
            .order_by(GiveawayParticipant.created_at.desc())
        )
        for participant, automation in result.all():
            if automation.follow_button_text.lower() not in text:
                continue
            participant.status = "follow_confirmed"
            provider = get_instagram_provider(access_token=await get_active_page_access_token(session))
            reward = await self._reward_message(session, automation)
            attempt = await self._run_dm_action(session, event, provider, event.actor_id or participant.instagram_user_id, reward)
            if attempt.status == ActionStatus.sent:
                participant.status = "reward_sent"
                participant.reward_sent = True
            else:
                participant.error_message = attempt.error_message
            await self._log(session, automation.id, participant.id, "reward_delivery", participant.status, attempt.error_message)
            return True
        return False

    async def draw_winners(self, session: AsyncSession, automation_id: str, count: int = 1) -> list[GiveawayParticipant]:
        participants = list(
            (
                await session.scalars(
                    select(GiveawayParticipant).where(
                        GiveawayParticipant.automation_id == automation_id,
                        GiveawayParticipant.status.in_(["dm_sent", "follow_confirmed", "reward_sent"]),
                    )
                )
            ).all()
        )
        if not participants:
            return []
        winners = sample(participants, k=min(count, len(participants)))
        for winner in winners:
            tags = set(winner.tags or [])
            tags.add("winner")
            winner.tags = sorted(tags)
            await self._log(session, automation_id, winner.id, "winner_selected", "ok", winner.instagram_username)
        return winners

    async def _match_automation(self, session: AsyncSession, comment: Comment) -> tuple[GiveawayAutomation | None, str | None]:
        now = datetime.now(UTC)
        candidates = (
            await session.scalars(
                select(GiveawayAutomation).where(
                    GiveawayAutomation.status == "active",
                    GiveawayAutomation.media_id == comment.media_id,
                )
            )
        ).all()
        normalized = normalize_comment_text(comment.text).lower()
        for automation in candidates:
            if automation.starts_at and automation.starts_at > now:
                continue
            if automation.ends_at and automation.ends_at < now:
                continue
            exclusions = [item.lower() for item in automation.exclusion_keywords or []]
            if any(keyword and keyword in normalized for keyword in exclusions):
                await self._log(session, automation.id, None, "excluded_comment", "skipped", comment.text)
                continue
            matched = self._trigger_match(automation, normalized)
            if matched:
                return automation, matched
        return None, None

    @staticmethod
    def _trigger_match(automation: GiveawayAutomation, normalized_text: str) -> str | None:
        triggers = [normalize_comment_text(item).lower() for item in automation.trigger_keywords or [] if item]
        if automation.trigger_type == "any_comment":
            return "any_comment"
        if automation.trigger_type == "exact_phrase":
            return next((trigger for trigger in triggers if trigger == normalized_text), None)
        return next((trigger for trigger in triggers if trigger in normalized_text), None)

    async def _reply_limit_reached(self, session: AsyncSession, automation: GiveawayAutomation) -> bool:
        count = await session.scalar(
            select(func.count())
            .select_from(GiveawayParticipant)
            .where(
                GiveawayParticipant.automation_id == automation.id,
                GiveawayParticipant.status.in_(["public_reply_sent", "dm_sent", "follow_confirmed", "reward_sent"]),
            )
        )
        return int(count or 0) >= automation.reply_limit

    @staticmethod
    def _public_reply(automation: GiveawayAutomation) -> str:
        if automation.public_reply_variations:
            return automation.public_reply_variations[0]
        return automation.public_reply_text

    @staticmethod
    def _entry_dm(automation: GiveawayAutomation) -> str:
        signature = f"\n\n- {automation.brand_signature}" if automation.brand_signature else ""
        return f"{automation.dm_message_text}\n\nReply: {automation.follow_button_text}{signature}"

    async def _reward_message(self, session: AsyncSession, automation: GiveawayAutomation) -> str:
        content = await session.scalar(select(GiveawayContent).where(GiveawayContent.automation_id == automation.id))
        if not content:
            return "Thanks for confirming. Your giveaway reward will be shared soon."
        parts = [content.message_text or "Thanks for confirming. Here is your giveaway reward."]
        if content.coupon_code:
            parts.append(f"Coupon code: {content.coupon_code}")
        if content.cta_url:
            label = content.cta_label or "Open reward"
            parts.append(f"{label}: {content.cta_url}")
        if content.image_url:
            parts.append(f"Image: {content.image_url}")
        for index, slide in enumerate(content.carousel_slides or [], start=1):
            parts.append(f"Slide {index}: {slide.get('text') or slide.get('url') or slide}")
        return "\n\n".join(parts)

    async def _run_comment_action(self, session, event, provider, comment, action_type: str, message: str) -> ActionAttempt:
        idempotency_key = f"{event.provider_event_id}:{action_type}"
        existing = await session.scalar(select(ActionAttempt).where(ActionAttempt.idempotency_key == idempotency_key))
        if existing and existing.status == ActionStatus.sent:
            return existing

        attempt = existing or ActionAttempt(
            social_event_id=event.id,
            action_type=action_type,
            provider=event.provider,
            idempotency_key=idempotency_key,
            attempts=0,
        )
        attempt.request_json = {"comment_id": comment.provider_comment_id, "message": message}
        attempt.attempts += 1
        if action_type == "giveaway_public_reply":
            result = await provider.reply_to_comment(comment.provider_comment_id, message)
        else:
            result = await provider.send_private_reply(comment.provider_comment_id, message)
        attempt.status = ActionStatus.sent if result.ok else ActionStatus.failed
        attempt.response_json = result.response
        attempt.error_message = result.error
        if not existing:
            session.add(attempt)
        return attempt

    async def _run_dm_action(self, session, event, provider, recipient_id: str, message: str) -> ActionAttempt:
        idempotency_key = f"{event.provider_event_id}:giveaway_reward_dm"
        existing = await session.scalar(select(ActionAttempt).where(ActionAttempt.idempotency_key == idempotency_key))
        if existing and existing.status == ActionStatus.sent:
            return existing

        attempt = existing or ActionAttempt(
            social_event_id=event.id,
            action_type="giveaway_reward_dm",
            provider=event.provider,
            idempotency_key=idempotency_key,
            attempts=0,
        )
        attempt.request_json = {"recipient_id": recipient_id, "message": message}
        attempt.attempts += 1
        result = await provider.send_dm(recipient_id, message)
        attempt.status = ActionStatus.sent if result.ok else ActionStatus.failed
        attempt.response_json = result.response
        attempt.error_message = result.error
        if not existing:
            session.add(attempt)
        return attempt

    async def _log(
        self,
        session: AsyncSession,
        automation_id: str | None,
        participant_id: str | None,
        event_name: str,
        status: str,
        message: str | None = None,
    ) -> None:
        session.add(
            AutomationEventLog(
                automation_id=automation_id,
                participant_id=participant_id,
                event_name=event_name,
                status=status,
                message=message,
            )
        )
