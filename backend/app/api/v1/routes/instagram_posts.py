"""Pick which Instagram posts get automatic comment replies and DMs.

A post is automated when an active campaign targets it (its permalink in
``target_media_urls`` / its id in ``target_media_ids``) or an active giveaway
runs on it. With ``INSTAGRAM_COMMENT_SCOPE=selected_posts`` (the default),
comments on every other post are stored but get no reply and no DM.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.v1.routes.campaigns import _normalize_campaign_metadata
from app.core.config import get_settings
from app.database.session import get_session
from app.models.entities import Campaign, GiveawayAutomation
from app.services.campaign_matcher import instagram_shortcode
from app.services.meta_sync import MetaSyncService

router = APIRouter(prefix="/instagram/posts", tags=["instagram posts"], dependencies=[Depends(get_current_user)])


class PostAutomationUpdate(BaseModel):
    media_id: str = Field(min_length=1, max_length=255)
    permalink: str = Field(min_length=1, max_length=2000)
    campaign_id: str = Field(min_length=1, max_length=64)
    enabled: bool


def campaign_targets_post(campaign: Campaign, media_id: str, permalink: str | None) -> bool:
    metadata = campaign.metadata_json or {}
    target_ids = {str(i) for i in metadata.get("target_media_ids", [])}
    if media_id and (media_id == str(campaign.post_id or "") or media_id in target_ids):
        return True
    shortcode = instagram_shortcode(permalink)
    return bool(shortcode and shortcode in {str(i) for i in metadata.get("target_media_shortcodes", [])})


def set_post_target(campaign: Campaign, media_id: str, permalink: str, enabled: bool) -> None:
    """Add or remove one post from a campaign's targets (assigns a new dict so JSON changes persist)."""
    metadata = dict(campaign.metadata_json or {})
    shortcode = instagram_shortcode(permalink)
    urls = [str(u) for u in metadata.get("target_media_urls", []) if u]
    ids = [str(i) for i in metadata.get("target_media_ids", []) if i]
    urls = [u for u in urls if instagram_shortcode(u) != shortcode]
    ids = [i for i in ids if i != media_id]
    if enabled:
        urls.append(permalink)
        ids.append(media_id)
    elif str(campaign.post_id or "") == media_id:
        campaign.post_id = None
    metadata["target_media_urls"] = urls
    metadata = _normalize_campaign_metadata(metadata)
    metadata["target_media_ids"] = ids
    campaign.metadata_json = metadata


@router.get("")
async def list_posts(
    limit: int = Query(default=24, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> dict:
    media = await MetaSyncService().list_recent_media(session, limit=limit)
    campaigns = (await session.scalars(select(Campaign).where(Campaign.status.in_(["active", "draft", "paused"])))).all()
    giveaways = (await session.scalars(select(GiveawayAutomation).where(GiveawayAutomation.status == "active"))).all()

    posts = []
    for item in media:
        media_id = str(item["id"])
        permalink = item.get("permalink")
        shortcode = instagram_shortcode(permalink)
        linked = [
            {"id": c.id, "name": c.name, "status": c.status, "keywords": c.keyword_triggers or []}
            for c in campaigns
            if campaign_targets_post(c, media_id, permalink)
        ]
        giveaway = next(
            (
                g.name
                for g in giveaways
                if g.media_id == media_id or (shortcode and instagram_shortcode(g.media_permalink) == shortcode)
            ),
            None,
        )
        posts.append(
            {
                "id": media_id,
                "caption": (item.get("caption") or "")[:300],
                "media_type": item.get("media_type"),
                "thumbnail_url": item.get("thumbnail_url") or item.get("media_url"),
                "permalink": permalink,
                "timestamp": item.get("timestamp"),
                "comments_count": item.get("comments_count") or 0,
                "campaigns": linked,
                "giveaway": giveaway,
                "automated": any(c["status"] == "active" for c in linked) or bool(giveaway),
            }
        )
    return {
        "scope": get_settings().instagram_comment_scope,
        "campaigns": [{"id": c.id, "name": c.name, "status": c.status} for c in campaigns],
        "posts": posts,
    }


@router.post("/automation")
async def update_post_automation(payload: PostAutomationUpdate, session: AsyncSession = Depends(get_session)) -> dict:
    if not instagram_shortcode(payload.permalink):
        raise HTTPException(status_code=422, detail="permalink must be an instagram.com post or reel link")
    campaign = await session.get(Campaign, payload.campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    set_post_target(campaign, payload.media_id, payload.permalink, payload.enabled)
    await session.commit()
    return {
        "ok": True,
        "campaign_id": campaign.id,
        "automated": campaign_targets_post(campaign, payload.media_id, payload.permalink),
        "campaign_active": campaign.status == "active",
    }
