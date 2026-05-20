from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import OpenAIDecisionClient
from app.ai.prompting import PROMPT_VERSION
from app.ai.rag import RAGKnowledgeBase
from app.database.session import get_sessionmaker
from app.models.entities import (
    AiLog,
    AnalyticsEvent,
    Campaign,
    Comment,
    Conversation,
    IntentAnalysis,
    Lead,
    LeadScore,
    Message,
    ModerationLog,
    SocialEvent,
    WebhookLog,
)
from app.models.enums import EventStatus, EventType, ModerationAction, SendDecision
from app.moderation.engine import ModerationEngine
from app.schemas.ai import AIRequestContext, ThreadMessage
from app.schemas.social import NormalizedEvent
from app.services.action_engine import ActionContext, ActionEngine
from app.services.campaign_matcher import CampaignMatcher
from app.services.lead_scoring import LeadScoringService
from app.services.meta_oauth import get_active_page_access_token
from app.services.normalization import detect_language, normalize_comment_text
from app.services.phone_utils import extract_phone
from app.services.provider_factory import get_instagram_provider, get_whatsapp_provider
from app.services.retention_jobs import RetentionJobRunner
from app.services.wellness_segments import detect_wellness_segment


class EventProcessor:
    def __init__(self) -> None:
        self.moderation = ModerationEngine()
        self.rag = RAGKnowledgeBase()
        self.ai = OpenAIDecisionClient()
        self.leads = LeadScoringService()
        self.actions = ActionEngine()
        self.campaigns = CampaignMatcher()

    async def process(
        self,
        session: AsyncSession,
        normalized: NormalizedEvent,
        webhook_log_id: str | None = None,
        force: bool = False,
    ) -> None:
        existing = await session.scalar(
            select(SocialEvent).where(SocialEvent.provider_event_id == normalized.provider_event_id)
        )
        if existing and not force:
            existing.status = EventStatus.duplicate
            return

        event = existing or SocialEvent(
            provider=normalized.provider,
            event_type=normalized.event_type,
            provider_event_id=normalized.provider_event_id,
            actor_id=normalized.actor_id,
            actor_username=normalized.actor_username,
            payload=normalized.payload,
            webhook_log_id=webhook_log_id,
        )
        event.provider = normalized.provider
        event.event_type = normalized.event_type
        event.actor_id = normalized.actor_id
        event.actor_username = normalized.actor_username
        event.status = EventStatus.processing
        event.payload = normalized.payload
        event.webhook_log_id = webhook_log_id or event.webhook_log_id
        if not existing:
            session.add(event)
        await session.flush()

        text = normalize_comment_text(normalized.text or "")
        comment: Comment | None = None
        if normalized.event_type == EventType.instagram_comment:
            provider_comment_id = normalized.provider_comment_id or normalized.provider_event_id
            comment = await session.scalar(select(Comment).where(Comment.provider_comment_id == provider_comment_id))
            if comment:
                comment.social_event_id = comment.social_event_id or event.id
                comment.media_id = normalized.media_id or comment.media_id
                comment.username = normalized.actor_username or comment.username
                comment.text = normalized.text or comment.text
                comment.normalized_text = text
                comment.language = detect_language(text)
            else:
                comment = Comment(
                    social_event_id=event.id,
                    provider_comment_id=provider_comment_id,
                    media_id=normalized.media_id,
                    username=normalized.actor_username,
                    text=normalized.text or "",
                    normalized_text=text,
                    language=detect_language(text),
                )
                session.add(comment)
            await session.flush()

        conversation = await self._upsert_conversation(session, normalized)
        if normalized.event_type in {EventType.instagram_dm, EventType.whatsapp_message} and normalized.text:
            session.add(
                Message(
                    conversation_id=conversation.id,
                    provider_message_id=normalized.provider_message_id,
                    direction="inbound",
                    body=normalized.text,
                    channel=normalized.event_type.value,
                    metadata_json=normalized.payload,
                )
            )

        matched_campaigns = await self.campaigns.match_active(
            session,
            text,
            media_id=normalized.media_id,
            media_permalink=normalized.payload.get("media_permalink") or normalized.payload.get("permalink"),
        )
        lead = await self._upsert_lead(session, normalized)
        phone = extract_phone(text)
        if phone:
            lead.phone = phone
            lead.whatsapp_opt_in = True

        thread_history = await self._load_thread_history(session, conversation.id)
        moderation = self.moderation.evaluate(text)
        retrieved = await self.rag.retrieve(text)
        decision, latency_ms, ai_input = await self.ai.generate_decision(
            AIRequestContext(
                text=text,
                username=normalized.actor_username,
                channel=normalized.event_type.value,
                media_id=normalized.media_id,
                retrieved_context=retrieved,
                thread_history=thread_history,
                lead_score=lead.score,
                lifecycle_stage=lead.lifecycle_stage,
                matched_campaigns=[c.name for c in matched_campaigns],
                campaign_product_focus=self.campaigns.product_focus(matched_campaigns),
                allow_public_reply=self.campaigns.allows_public_reply(matched_campaigns),
                allow_dm=self.campaigns.allows_dm(matched_campaigns),
                allow_whatsapp_followup=self.campaigns.allows_whatsapp_followup(matched_campaigns),
                wellness_segment=detect_wellness_segment(text),
            )
        )

        decision = self._apply_campaign_gates(decision, matched_campaigns)

        if moderation.action != ModerationAction.allow:
            decision.moderation_action = moderation.action
            decision.safety_flags = sorted(set(decision.safety_flags + moderation.flags))
            if moderation.action == ModerationAction.hide:
                decision.send_decision = SendDecision.suppress
            elif moderation.action == ModerationAction.block:
                decision.send_decision = SendDecision.suppress
            else:
                decision.send_decision = SendDecision.escalate
            decision.escalation_reason = moderation.notes or decision.escalation_reason

        session.add(
            ModerationLog(
                social_event_id=event.id,
                comment_id=comment.id if comment else None,
                action=decision.moderation_action,
                flags=decision.safety_flags,
                confidence=moderation.confidence,
                notes=moderation.notes,
            )
        )
        session.add(
            AiLog(
                social_event_id=event.id,
                model=self.ai.settings.openai_model,
                prompt_version=PROMPT_VERSION,
                input_json=ai_input,
                output_json=decision.model_dump(mode="json"),
                latency_ms=latency_ms,
                confidence=decision.confidence,
                blocked=decision.send_decision != SendDecision.send,
            )
        )
        session.add(
            IntentAnalysis(
                social_event_id=event.id,
                intent=decision.intent,
                sentiment=decision.sentiment,
                urgency=decision.urgency,
                purchase_intent=decision.purchase_intent,
                recommended_products=decision.recommended_products,
                confidence=decision.confidence,
                safety_flags=decision.safety_flags,
            )
        )

        repeat_engagements = await session.scalar(
            select(func.count()).select_from(SocialEvent).where(SocialEvent.actor_id == normalized.actor_id)
        )
        score_delta = self.leads.score_delta(decision, int(repeat_engagements or 0))
        lead.score = max(0, min(100, lead.score + score_delta))
        session.add(LeadScore(lead_id=lead.id, score_delta=score_delta, reason=decision.intent))
        await RetentionJobRunner().enroll_new_leads(session, lead)

        page_access_token = await get_active_page_access_token(session)
        provider = (
            get_whatsapp_provider()
            if normalized.event_type == EventType.whatsapp_message
            else get_instagram_provider(access_token=page_access_token)
        )
        await self.actions.execute(
            session,
            provider,
            event,
            comment,
            decision,
            ActionContext(
                conversation=conversation,
                lead=lead,
                channel=normalized.event_type.value,
                allow_whatsapp_followup=self.campaigns.allows_whatsapp_followup(matched_campaigns)
                or bool(decision.whatsapp_followup),
            ),
        )

        session.add(
            AnalyticsEvent(
                event_name="social_event_processed",
                entity_type="social_event",
                entity_id=event.id,
                properties={
                    "intent": decision.intent,
                    "sentiment": decision.sentiment,
                    "send_decision": decision.send_decision,
                    "campaigns": [c.name for c in matched_campaigns],
                },
            )
        )
        event.status = EventStatus.processed

    def _apply_campaign_gates(self, decision, matched_campaigns: list[Campaign]):
        if matched_campaigns and not self.campaigns.allows_public_reply(matched_campaigns):
            decision.public_reply = ""
        if matched_campaigns and not self.campaigns.allows_dm(matched_campaigns):
            decision.private_dm = ""
        if matched_campaigns and self.campaigns.allows_whatsapp_followup(matched_campaigns) and not decision.whatsapp_followup:
            decision.whatsapp_followup = (
                "Hi — continuing from Instagram. Happy to share calm, science-backed guidance "
                "on what may suit you. What would you like help with today?"
            )
        return decision

    async def _load_thread_history(self, session: AsyncSession, conversation_id: str) -> list[ThreadMessage]:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(12)
        )
        messages = list(reversed(result.scalars().all()))
        return [
            ThreadMessage(direction=item.direction, body=item.body, channel=item.channel) for item in messages
        ]

    async def _upsert_conversation(self, session: AsyncSession, normalized: NormalizedEvent) -> Conversation:
        external_user_id = normalized.actor_id or normalized.actor_username or "unknown"
        channel = normalized.event_type.value
        conversation = await session.scalar(
            select(Conversation).where(
                Conversation.external_user_id == external_user_id,
                Conversation.channel == channel,
            )
        )
        if conversation:
            conversation.last_message_at = datetime.now(UTC)
            return conversation
        conversation = Conversation(
            external_user_id=external_user_id,
            username=normalized.actor_username,
            channel=channel,
            last_message_at=datetime.now(UTC),
        )
        session.add(conversation)
        await session.flush()
        return conversation

    async def _upsert_lead(self, session: AsyncSession, normalized: NormalizedEvent) -> Lead:
        external_user_id = normalized.actor_id or normalized.actor_username or "unknown"
        source_channel = "whatsapp" if normalized.event_type == EventType.whatsapp_message else "instagram"
        lead = await session.scalar(
            select(Lead).where(Lead.external_user_id == external_user_id, Lead.source_channel == source_channel)
        )
        if lead:
            lead.username = normalized.actor_username or lead.username
            return lead
        lead = Lead(
            external_user_id=external_user_id,
            username=normalized.actor_username,
            source_channel=source_channel,
            score=0,
            tags=[source_channel],
        )
        session.add(lead)
        await session.flush()
        return lead


async def process_webhook_payload(log_id: str, payload: dict, channel: str) -> None:
    processor = EventProcessor()
    provider = get_whatsapp_provider() if channel == "whatsapp" else get_instagram_provider()
    async with get_sessionmaker()() as session:
        log = await session.get(WebhookLog, log_id)
        try:
            events = await provider.normalize_event(payload)
            if log:
                log.status = EventStatus.queued
            for event in events:
                await processor.process(session, event, webhook_log_id=log_id)
            if log:
                log.status = EventStatus.processed
            await session.commit()
        except Exception as exc:
            if log:
                log.status = EventStatus.failed
                log.error_message = str(exc)
            await session.commit()
            raise
