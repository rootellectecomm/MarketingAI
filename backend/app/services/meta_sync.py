from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.models.entities import Comment, InstagramAccount, Lead, ProviderCredential
from app.models.enums import ProviderType
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
        media_limit: int = 8,
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
        media_seen = 0

        async with httpx.AsyncClient(timeout=30) as client:
            media = await self._get_json(
                client,
                f"{account.ig_user_id}/media",
                access_token,
                fields="id,caption,media_type,permalink,timestamp,comments_count",
                limit=max(1, min(media_limit, 25)),
            )
            for media_item in media.get("data", []):
                media_seen += 1
                comments = await self._get_json(
                    client,
                    f"{media_item.get('id')}/comments",
                    access_token,
                    fields="id,text,username,timestamp,like_count",
                    limit=max(1, min(comments_per_media, 50)),
                )
                for comment in comments.get("data", []):
                    was_created = await self._upsert_comment(session, media_item, comment)
                    await self._upsert_lead(session, comment)
                    if was_created:
                        synced += 1
                    else:
                        updated += 1

        await session.commit()
        return {
            "instagram_account": {"id": account.ig_user_id, "username": account.username},
            "media_seen": media_seen,
            "comments_created": synced,
            "comments_updated": updated,
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
