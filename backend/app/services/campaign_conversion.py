from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.product_knowledge import ROOTELLECT_PRODUCT_CATALOG
from app.core.config import get_settings
from app.models.entities import AnalyticsEvent, Campaign, CampaignEvent, Comment, Conversation, Lead, SocialEvent
from app.models.enums import ActionStatus, EventType, ProviderType, SendDecision
from app.schemas.ai import AIDecision
from app.services.action_engine import ActionContext, ActionEngine
from app.services.campaign_matcher import CampaignMatcher
from app.services.providers.base import SocialProvider

logger = structlog.get_logger(__name__)

ROOTELLECT_WHATSAPP_NUMBER = "918679508311"
ROOTELLECT_WHATSAPP_LINK = "https://wa.me/918679508311"


@dataclass(slots=True)
class CampaignPreview:
    campaign: Campaign | None
    matched_keyword: str | None
    public_reply: str
    dm_reply: str
    product_selected: str | None
    lead_score: int
    ai_intent: str


class CampaignConversionService:
    def __init__(self) -> None:
        self.matcher = CampaignMatcher()
        self.actions = ActionEngine()

    async def handle_comment(
        self,
        session: AsyncSession,
        provider: SocialProvider,
        event: SocialEvent,
        comment: Comment,
        campaign: Campaign,
        conversation: Conversation,
        lead: Lead,
    ) -> bool:
        if event.event_type != EventType.instagram_comment:
            return False

        platform = self.platform_for_event(event)
        comment_id = comment.provider_comment_id
        matched_keyword = self.matcher.matched_keyword(campaign, comment.normalized_text or comment.text)
        existing = await session.scalar(
            select(CampaignEvent).where(
                CampaignEvent.campaign_id == campaign.id,
                CampaignEvent.comment_id == comment_id,
            )
        )
        if existing:
            existing.status = "duplicate_skipped"
            await self._log(session, "duplicate_skipped", campaign, event, {"comment_id": comment_id})
            return True

        preview = self.preview(campaign, comment.text, platform=platform, post_id=comment.media_id)
        recent_dm = await self._has_recent_dm(session, campaign.id, lead.external_user_id)
        private_dm = preview.dm_reply if campaign.dm_enabled and not recent_dm else ""
        status = "campaign_matched"
        logs = ["campaign_matched", "keyword_matched"]
        if recent_dm:
            status = "duplicate_skipped"
            logs.append("duplicate_skipped")

        campaign_event = CampaignEvent(
            campaign_id=campaign.id,
            platform=platform,
            source_type="comment",
            user_id=lead.external_user_id,
            username=lead.username,
            comment_id=comment_id,
            matched_keyword=matched_keyword,
            user_text=comment.text,
            ai_intent=preview.ai_intent,
            lead_score=lead.score,
            status=status,
            metadata_json={
                "logs": logs,
                "post_id": comment.media_id,
                "public_reply_preview": preview.public_reply,
                "dm_preview": preview.dm_reply,
                "recent_dm_skipped": recent_dm,
            },
        )
        session.add(campaign_event)

        self._apply_lead_campaign_state(lead, campaign, comment.text, preview.lead_score)

        decision = AIDecision(
            intent="purchase_intent" if preview.lead_score >= 4 else "product_question",
            purchase_intent=0.8 if preview.lead_score >= 4 else 0.45,
            recommended_products=[campaign.product_name or preview.product_selected] if preview.product_selected else [],
            confidence=0.92,
            public_reply=preview.public_reply if campaign.public_reply_enabled else "",
            private_dm=private_dm,
            selected_product=campaign.product_name or preview.product_selected,
            user_intent=preview.ai_intent,
            reply_channel=event.event_type.value,
            used_knowledge_source="campaign",
            send_decision=SendDecision.send,
        )
        attempts = await self.actions.execute(
            session,
            provider,
            event,
            comment,
            decision,
            ActionContext(
                conversation=conversation,
                lead=lead,
                channel=event.event_type.value,
                allow_whatsapp_followup=False,
            ),
        )

        sent_actions = {attempt.action_type for attempt in attempts if attempt.status == ActionStatus.sent}
        failed = [attempt for attempt in attempts if attempt.status == ActionStatus.failed]
        if "reply_to_comment" in sent_actions:
            logs.append("comment_reply_sent")
            await self._log(session, "comment_reply_sent", campaign, event, {"comment_id": comment_id})
        if "send_private_reply" in sent_actions:
            logs.append("dm_sent")
            campaign_event.status = "dm_sent"
            lead.conversion_stage = "dm_sent"
            await self._log(session, "dm_sent", campaign, event, {"user_id": lead.external_user_id})
        if failed:
            logs.append("send_error")
            campaign_event.status = "send_error"
            await self._log(
                session,
                "send_error",
                campaign,
                event,
                {
                    "responses": [attempt.response_json for attempt in failed],
                    "errors": [attempt.error_message for attempt in failed],
                },
            )
            logger.error(
                "campaign send error",
                campaign_id=campaign.id,
                event_id=event.id,
                graph_api_response_body=[attempt.response_json for attempt in failed],
            )
        campaign_event.metadata_json = {**campaign_event.metadata_json, "logs": logs}
        campaign_event.lead_score = lead.score
        return True

    def preview(
        self,
        campaign: Campaign,
        text: str,
        *,
        platform: str = "instagram",
        post_id: str | None = None,
    ) -> CampaignPreview:
        matched_keyword = self.matcher.matched_keyword(campaign, text)
        product_selected = campaign.product_name or self._product_from_campaign(campaign)
        ai_intent = self._intent_for_text(text, product_selected)
        lead_score = self.score_text(text)
        values = self._template_values(campaign, product_selected)
        return CampaignPreview(
            campaign=campaign,
            matched_keyword=matched_keyword,
            public_reply=self._render(campaign.public_reply_template, values),
            dm_reply=self._render(campaign.dm_template or self._default_dm_template(product_selected), values),
            product_selected=product_selected,
            lead_score=lead_score,
            ai_intent=ai_intent,
        )

    @staticmethod
    def score_text(text: str) -> int:
        lowered = text.lower()
        score = 0
        if "price" in lowered:
            score += 1
        if "link" in lowered:
            score += 2
        if any(term in lowered for term in ("buy", "order", "how to take")):
            score += 3
        if any(term in lowered for term in ("stress", "sleep", "pcos", "pcod", "hot flash", "fatigue", "acne")):
            score += 2
        if "dosage" in lowered:
            score += 1
        if any(term in lowered for term in ("review", "reviews", "result", "results")):
            score += 2
        if score == 0:
            score -= 1
        return score

    @staticmethod
    def platform_for_event(event: SocialEvent) -> str:
        if event.provider == ProviderType.facebook_page_backed:
            return "facebook"
        if event.provider == ProviderType.whatsapp_cloud:
            return "whatsapp"
        return "instagram"

    async def _has_recent_dm(self, session: AsyncSession, campaign_id: str, user_id: str | None) -> bool:
        if not user_id:
            return False
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        existing = await session.scalar(
            select(CampaignEvent.id).where(
                CampaignEvent.campaign_id == campaign_id,
                CampaignEvent.user_id == user_id,
                CampaignEvent.status == "dm_sent",
                CampaignEvent.created_at >= cutoff,
            )
        )
        return bool(existing)

    def _apply_lead_campaign_state(self, lead: Lead, campaign: Campaign, text: str, score_delta: int) -> None:
        lead.platform = campaign.platform if campaign.platform != "both" else lead.source_channel
        lead.product_interest = campaign.product_name or self._product_from_campaign(campaign)
        lead.source_campaign_id = campaign.id
        lead.last_message = text
        lead.conversion_stage = "campaign_matched"
        lead.score = max(0, min(100, lead.score + score_delta))
        lead.intent_level = "high" if lead.score >= 6 else "medium" if lead.score >= 4 else "low"
        if lead.intent_level == "high":
            lead.lifecycle_stage = "hot"
        elif lead.intent_level == "medium" and lead.lifecycle_stage == "new":
            lead.lifecycle_stage = "qualified"
        tags = set(lead.tags or [])
        tags.add("campaign")
        if lead.product_interest:
            tags.add(lead.product_interest)
        lead.tags = sorted(tags)

    @staticmethod
    def _product_from_campaign(campaign: Campaign) -> str | None:
        if campaign.product_focus:
            return campaign.product_focus[0]
        return None

    @staticmethod
    def _template_values(campaign: Campaign, product_selected: str | None) -> dict[str, str]:
        product_link = campaign.product_link or ""
        if not product_link and product_selected in ROOTELLECT_PRODUCT_CATALOG:
            product_link = ROOTELLECT_PRODUCT_CATALOG[product_selected].url
        settings = get_settings()
        whatsapp_link = campaign.whatsapp_link or settings.rootellect_whatsapp_link or ROOTELLECT_WHATSAPP_LINK
        return {
            "product_link": product_link,
            "followup_link": campaign.followup_link or product_link,
            "whatsapp_link": whatsapp_link,
            "product_name": campaign.product_name or product_selected or "",
            "campaign_name": campaign.name,
        }

    @staticmethod
    def _render(template: str, values: dict[str, str]) -> str:
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", value)
        return rendered.strip()

    @staticmethod
    def _default_dm_template(product_selected: str | None) -> str:
        if product_selected == "Women Balance":
            return (
                "This sounds more like PMS + energy support. Women Balance fits better - it supports daily women's "
                "hormonal wellness, mood and energy. {{product_link}}"
            )
        if product_selected == "PCOS Support":
            return (
                "For PCOS/PCOD wellness, PCOS Support is the most relevant option. It's a non-hormonal formula "
                "designed to support cycle wellness, hormonal balance, skin concerns and metabolic health. {{product_link}}"
            )
        if product_selected == "Perimenopause Support":
            return (
                "If she's around 35+ or in the transition phase, Perimenopause Support is the closest fit. It's "
                "designed to support hot flashes, mood, sleep and hormonal transition comfort. {{product_link}}"
            )
        return (
            "Got it. This sounds more like stress + sleep quality support. Mind Calm is the closest fit - it's "
            "non-melatonin and designed to support calmness, relaxation and better sleep quality. {{product_link}}"
        )

    @staticmethod
    def _intent_for_text(text: str, product_selected: str | None) -> str:
        lowered = text.lower()
        if any(term in lowered for term in ("price", "link", "cost")):
            return "price_question"
        if any(term in lowered for term in ("buy", "order", "checkout")):
            return "buying_intent"
        if any(term in lowered for term in ("review", "result", "expensive", "work")):
            return "objection"
        if product_selected == "Mind Calm":
            return "stress_sleep"
        if product_selected == "Women Balance":
            return "pms_energy"
        if product_selected == "PCOS Support":
            return "pcos_pcod"
        if product_selected == "Perimenopause Support":
            return "perimenopause"
        return "unclear"

    async def _log(
        self,
        session: AsyncSession,
        event_name: str,
        campaign: Campaign,
        event: SocialEvent,
        properties: dict,
    ) -> None:
        session.add(
            AnalyticsEvent(
                event_name=event_name,
                entity_type="campaign",
                entity_id=campaign.id,
                properties={"social_event_id": event.id, **properties},
            )
        )
