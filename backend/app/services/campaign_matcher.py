from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Campaign
from app.services.normalization import normalize_comment_text


def instagram_shortcode(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"instagram\.com/(?:p|reel|tv)/([^/?#]+)/?", value)
    if match:
        return match.group(1).strip()
    return None


class CampaignMatcher:
    async def match_active(
        self,
        session: AsyncSession,
        text: str,
        media_id: str | None = None,
        media_permalink: str | None = None,
    ) -> list[Campaign]:
        normalized = normalize_comment_text(text).lower()
        if not normalized:
            return []

        result = await session.execute(select(Campaign).where(Campaign.status == "active"))
        campaigns = list(result.scalars().all())
        matched: list[Campaign] = []
        for campaign in campaigns:
            triggers = [t.lower().strip() for t in (campaign.keyword_triggers or []) if t.strip()]
            keyword_match = not triggers or any(trigger in normalized for trigger in triggers)
            if keyword_match and self._matches_media_target(campaign, media_id, media_permalink):
                matched.append(campaign)
        return matched

    @staticmethod
    def _matches_media_target(campaign: Campaign, media_id: str | None, media_permalink: str | None) -> bool:
        metadata = campaign.metadata_json or {}
        target_ids = {str(item) for item in metadata.get("target_media_ids", []) if item}
        target_shortcodes = {str(item) for item in metadata.get("target_media_shortcodes", []) if item}

        if not target_ids and not target_shortcodes:
            return True
        if media_id and str(media_id) in target_ids:
            return True

        shortcode = instagram_shortcode(media_permalink)
        return bool(shortcode and shortcode in target_shortcodes)

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
