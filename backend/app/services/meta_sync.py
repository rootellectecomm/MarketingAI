from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.models.entities import Campaign, Comment, InstagramAccount, Lead, ProviderCredential
from app.models.enums import EventType, ProviderType
from app.schemas.social import NormalizedEvent
from app.services.campaign_matcher import instagram_shortcode
from app.services.event_processor import EventProcessor
from app.services.normalization import detect_language, normalize_comment_text


def _parse_meta_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class MetaSyncService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def sync_recent_comments(
        self,
        session: AsyncSession,
        media_limit: int = 25,
        comments_per_media: int = 25,
    ) -> dict:
        account = await session.scalar(
            select(InstagramAccount).where(InstagramAccount.is_active.is_(True)).order_by(InstagramAccount.updated_at.desc())
        )
        if not account:
            account = await self._repair_instagram_account_from_saved_pages(session)
        if not account:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No connected Instagram account found. Facebook may be connected, but Meta did not return a Page-linked "
                    "Instagram Professional account. Make sure your Instagram is Professional/Creator, linked to the same "
                    "Facebook Page you selected during authorization, then reconnect Facebook & Instagram."
                ),
            )

        credential = None
        if account.provider_credential_id:
            credential = await session.get(ProviderCredential, account.provider_credential_id)
        if not credential or not credential.encrypted_access_token:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No active Facebook Page token found. Reconnect Facebook & Instagram and make sure you select the Page "
                    "linked to the Instagram professional account during Meta authorization."
                ),
            )

        access_token = decrypt_secret(credential.encrypted_access_token)
        synced = 0
        updated = 0
        automation_processed = 0
        automation_skipped = 0
        media_seen = 0
        processor = EventProcessor()

        async with httpx.AsyncClient(timeout=30) as client:
            media = await self._get_json(
                client,
                f"{account.ig_user_id}/media",
                access_token,
                fields="id,caption,media_type,permalink,timestamp,comments_count",
                limit=max(1, min(media_limit, 50)),
            )
            for media_item in media.get("data", []):
                media_seen += 1
                await self._attach_media_id_to_targeted_campaigns(session, media_item)
                comments = await self._get_json(
                    client,
                    f"{media_item.get('id')}/comments",
                    access_token,
                    fields="id,text,username,timestamp,like_count",
                    limit=max(1, min(comments_per_media, 50)),
                )
                for comment in comments.get("data", []):
                    existing = await self._find_comment(session, comment)
                    should_process = existing is None or not (existing.replied and existing.private_replied)
                    if should_process:
                        await processor.process(
                            session,
                            self._normalized_comment_event(media_item, comment),
                            webhook_log_id=None,
                            force=True,
                        )
                    processed_comment = await self._find_comment(session, comment)
                    if processed_comment and media_item.get("permalink"):
                        processed_comment.permalink = str(media_item.get("permalink"))
                    was_created = existing is None and processed_comment is not None
                    if was_created:
                        synced += 1
                    else:
                        updated += 1
                    if processed_comment and (processed_comment.replied or processed_comment.private_replied):
                        automation_processed += 1
                    else:
                        automation_skipped += 1

        await session.commit()
        return {
            "instagram_account": {"id": account.ig_user_id, "username": account.username},
            "media_seen": media_seen,
            "comments_created": synced,
            "comments_updated": updated,
            "automation_processed": automation_processed,
            "automation_skipped": automation_skipped,
        }

    async def _get_json(self, client: httpx.AsyncClient, path: str, access_token: str, **params) -> dict:
        params["access_token"] = access_token
        url = f"https://graph.facebook.com/{self.settings.meta_graph_version}/{path}"
        response = await client.get(url, params=params)
        data = response.json() if response.content else {}
        if not response.is_success:
            raise HTTPException(status_code=400, detail={"meta_error": data})
        return data

    async def _repair_instagram_account_from_saved_pages(self, session: AsyncSession) -> InstagramAccount | None:
        credentials = (
            await session.scalars(
                select(ProviderCredential)
                .where(
                    ProviderCredential.provider_type == ProviderType.facebook_page_backed,
                    ProviderCredential.is_active.is_(True),
                    ProviderCredential.encrypted_access_token.is_not(None),
                )
                .order_by(ProviderCredential.updated_at.desc())
            )
        ).all()
        if not credentials:
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            for credential in credentials:
                if not credential.external_account_id or not credential.encrypted_access_token:
                    continue
                access_token = decrypt_secret(credential.encrypted_access_token)
                page = await self._get_json(
                    client,
                    credential.external_account_id,
                    access_token,
                    fields=(
                        "id,name,"
                        "instagram_business_account{id,username,profile_picture_url},"
                        "connected_instagram_account{id,username,profile_picture_url}"
                    ),
                )
                instagram_account = page.get("instagram_business_account") or page.get("connected_instagram_account")
                if not instagram_account or not instagram_account.get("id"):
                    continue

                account = await session.scalar(
                    select(InstagramAccount).where(InstagramAccount.ig_user_id == str(instagram_account.get("id")))
                )
                if not account:
                    account = InstagramAccount(
                        provider_credential_id=credential.id,
                        ig_user_id=str(instagram_account.get("id")),
                        username=instagram_account.get("username") or "instagram",
                        auth_path=ProviderType.facebook_page_backed.value,
                    )
                    session.add(account)

                account.provider_credential_id = credential.id
                account.username = instagram_account.get("username") or account.username
                account.auth_path = ProviderType.facebook_page_backed.value
                account.is_active = True
                await session.flush()
                return account

        return None

    async def _find_comment(self, session: AsyncSession, comment: dict) -> Comment | None:
        comment_id = str(comment.get("id") or "")
        if not comment_id:
            return None
        return await session.scalar(select(Comment).where(Comment.provider_comment_id == comment_id))

    async def _attach_media_id_to_targeted_campaigns(self, session: AsyncSession, media_item: dict) -> None:
        media_id = str(media_item.get("id") or "")
        permalink = str(media_item.get("permalink") or "")
        shortcode = instagram_shortcode(permalink)
        if not media_id or not shortcode:
            return

        campaigns = (
            await session.scalars(
                select(Campaign).where(
                    Campaign.status == "active",
                    Campaign.metadata_json.is_not(None),
                )
            )
        ).all()
        for campaign in campaigns:
            metadata = dict(campaign.metadata_json or {})
            target_shortcodes = {str(item) for item in metadata.get("target_media_shortcodes", []) if item}
            if shortcode not in target_shortcodes:
                continue

            target_ids = [str(item) for item in metadata.get("target_media_ids", []) if item]
            if media_id not in target_ids:
                metadata["target_media_ids"] = [*target_ids, media_id]
                campaign.metadata_json = metadata

    def _normalized_comment_event(self, media_item: dict, comment: dict) -> NormalizedEvent:
        comment_id = str(comment.get("id") or "")
        username = comment.get("username")
        return NormalizedEvent(
            provider=ProviderType.facebook_page_backed,
            event_type=EventType.instagram_comment,
            provider_event_id=comment_id,
            actor_id=str((comment.get("from") or {}).get("id") or username or comment_id),
            actor_username=username,
            text=comment.get("text") or "",
            provider_comment_id=comment_id,
            media_id=str(media_item.get("id") or ""),
            timestamp=_parse_meta_timestamp(comment.get("timestamp")),
            payload={
                **comment,
                "media_id": str(media_item.get("id") or ""),
                "media_permalink": media_item.get("permalink"),
                "source": "meta_sync",
            },
        )

    async def _upsert_comment(self, session: AsyncSession, media_item: dict, comment: dict) -> bool:
        comment_id = str(comment.get("id") or "")
        if not comment_id:
            return False

        text = comment.get("text") or ""
        created_at = _parse_meta_timestamp(comment.get("timestamp"))
        existing = await session.scalar(select(Comment).where(Comment.provider_comment_id == comment_id))
        if existing:
            existing.media_id = str(media_item.get("id") or existing.media_id or "")
            existing.username = comment.get("username") or existing.username
            existing.text = text
            existing.normalized_text = normalize_comment_text(text)
            existing.language = detect_language(text)
            existing.permalink = media_item.get("permalink") or existing.permalink
            return False

        comment_values = {
            "provider_comment_id": comment_id,
            "media_id": str(media_item.get("id") or ""),
            "username": comment.get("username"),
            "text": text,
            "normalized_text": normalize_comment_text(text),
            "language": detect_language(text),
            "permalink": media_item.get("permalink"),
        }
        if created_at:
            comment_values["created_at"] = created_at

        session.add(
            Comment(
                **comment_values,
            )
        )
        return True

    async def _upsert_lead(self, session: AsyncSession, comment: dict) -> None:
        username = comment.get("username")
        external_user_id = str(comment.get("from", {}).get("id") or username or comment.get("id") or "")
        if not external_user_id:
            return

        lead = await session.scalar(
            select(Lead).where(Lead.external_user_id == external_user_id, Lead.source_channel == "instagram")
        )
        if lead:
            lead.username = username or lead.username
            lead.score = max(lead.score, 1)
            if "synced" not in lead.tags:
                lead.tags = [*lead.tags, "synced"]
            return

        session.add(
            Lead(
                external_user_id=external_user_id,
                username=username,
                source_channel="instagram",
                lifecycle_stage="new",
                score=1,
                tags=["instagram", "synced"],
                metadata_json={"source": "meta_sync", "first_comment_id": comment.get("id")},
            )
        )
