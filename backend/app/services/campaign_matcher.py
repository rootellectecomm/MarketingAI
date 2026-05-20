from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Campaign
from app.services.normalization import normalize_comment_text


class CampaignMatcher:
    async def match_active(self, session: AsyncSession, text: str) -> list[Campaign]:
        normalized = normalize_comment_text(text).lower()
        if not normalized:
            return []

        result = await session.execute(select(Campaign).where(Campaign.status == "active"))
        campaigns = list(result.scalars().all())
        matched: list[Campaign] = []
        for campaign in campaigns:
            triggers = [t.lower().strip() for t in (campaign.keyword_triggers or []) if t.strip()]
            if any(trigger in normalized for trigger in triggers):
                matched.append(campaign)
        return matched

    @staticmethod
    def product_focus(campaigns: list[Campaign]) -> list[str]:
        products: list[str] = []
        for campaign in campaigns:
            for product in campaign.product_focus or []:
                if product not in products:
                    products.append(product)
        return products

    @staticmethod
    def allows_public_reply(campaigns: list[Campaign]) -> bool:
        return not campaigns or any(c.public_reply_enabled for c in campaigns)

    @staticmethod
    def allows_dm(campaigns: list[Campaign]) -> bool:
        return not campaigns or any(c.dm_enabled for c in campaigns)

    @staticmethod
    def allows_whatsapp_followup(campaigns: list[Campaign]) -> bool:
        return bool(campaigns) and any(c.whatsapp_followup_enabled for c in campaigns)
