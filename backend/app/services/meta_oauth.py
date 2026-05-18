from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_meta_oauth_scopes, get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.entities import InstagramAccount, ProviderCredential
from app.models.enums import ProviderType


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


class MetaOAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_state(self) -> str:
        payload = {"iat": int(time.time()), "nonce": _base64url(hashlib.sha256(str(time.time()).encode()).digest()[:16])}
        payload_text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        payload_b64 = _base64url(payload_text.encode("utf-8"))
        signature = hmac.new(
            self.settings.jwt_secret_key.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return f"{payload_b64}.{_base64url(signature)}"

    def verify_state(self, state: str) -> None:
        try:
            payload_b64, signature_b64 = state.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Meta OAuth state") from exc

        expected = hmac.new(
            self.settings.jwt_secret_key.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_b64 = _base64url(expected)
        if not hmac.compare_digest(expected_b64, signature_b64):
            raise HTTPException(status_code=400, detail="Invalid Meta OAuth state")

        padded = payload_b64 + ("=" * (-len(payload_b64) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")))
        if int(time.time()) - int(payload.get("iat", 0)) > 900:
            raise HTTPException(status_code=400, detail="Expired Meta OAuth state")

    def authorization_url(self) -> str:
        if not self.settings.meta_app_id or not self.settings.meta_oauth_redirect_uri:
            raise HTTPException(status_code=500, detail="Meta OAuth env vars are not configured")

        scopes = get_meta_oauth_scopes(self.settings)
        params = {
            "client_id": self.settings.meta_app_id,
            "redirect_uri": self.settings.meta_oauth_redirect_uri,
            "state": self.build_state(),
            "scope": ",".join(scopes),
            "response_type": "code",
        }
        return f"https://www.facebook.com/{self.settings.meta_graph_version}/dialog/oauth?{urlencode(params)}"

    async def connect_from_code(self, session: AsyncSession, code: str) -> dict:
        if not self.settings.meta_app_id or not self.settings.meta_oauth_redirect_uri:
            raise HTTPException(status_code=500, detail="Meta OAuth env vars are not configured")

        async with httpx.AsyncClient(timeout=30) as client:
            short_token = await self._exchange_code(client, code)
            long_token = await self._exchange_long_lived_token(client, short_token)
            user = await self._get_json(client, "me", long_token, fields="id,name,email")
            pages = await self._get_json(
                client,
                "me/accounts",
                long_token,
                fields="id,name,access_token,instagram_business_account{id,username,profile_picture_url}",
                limit=100,
            )

        connected_pages = []
        connected_instagram = []
        for page in pages.get("data", []):
            page_token = page.get("access_token")
            if not page_token:
                continue
            credential = await self._upsert_page_credential(session, page, user, page_token)
            connected_pages.append({"id": page.get("id"), "name": page.get("name")})

            instagram_account = page.get("instagram_business_account")
            if instagram_account:
                account = await self._upsert_instagram_account(session, credential, instagram_account)
                connected_instagram.append({"id": account.ig_user_id, "username": account.username})

        await session.commit()
        return {
            "facebook_pages": connected_pages,
            "instagram_accounts": connected_instagram,
            "message": "Facebook and Instagram connection saved.",
        }

    async def _exchange_code(self, client: httpx.AsyncClient, code: str) -> str:
        payload = await self._get_json(
            client,
            "oauth/access_token",
            None,
            client_id=self.settings.meta_app_id,
            client_secret=self.settings.meta_app_secret,
            redirect_uri=self.settings.meta_oauth_redirect_uri,
            code=code,
        )
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not token:
            raise HTTPException(status_code=400, detail={"meta_error": payload})
        return token

    async def _exchange_long_lived_token(self, client: httpx.AsyncClient, token: str) -> str:
        payload = await self._get_json(
            client,
            "oauth/access_token",
            None,
            grant_type="fb_exchange_token",
            client_id=self.settings.meta_app_id,
            client_secret=self.settings.meta_app_secret,
            fb_exchange_token=token,
        )
        return payload.get("access_token", token)

    async def _get_json(self, client: httpx.AsyncClient, path: str, token: str | None, **params) -> dict:
        if token:
            params["access_token"] = token
        url = f"https://graph.facebook.com/{self.settings.meta_graph_version}/{path}"
        response = await client.get(url, params=params)
        data = response.json()
        if not response.is_success:
            raise HTTPException(status_code=400, detail={"meta_error": data})
        return data

    async def _upsert_page_credential(
        self,
        session: AsyncSession,
        page: dict,
        user: dict,
        page_token: str,
    ) -> ProviderCredential:
        credential = await session.scalar(
            select(ProviderCredential).where(
                ProviderCredential.provider_type == ProviderType.facebook_page_backed,
                ProviderCredential.external_account_id == page.get("id"),
            )
        )
        if not credential:
            credential = ProviderCredential(
                provider_type=ProviderType.facebook_page_backed,
                account_name=page.get("name") or "Facebook Page",
                external_account_id=page.get("id"),
            )
            session.add(credential)

        credential.account_name = page.get("name") or credential.account_name
        credential.encrypted_access_token = encrypt_secret(page_token)
        credential.scopes = get_meta_oauth_scopes(self.settings)
        credential.is_active = True
        credential.metadata_json = {
            "facebook_page": {"id": page.get("id"), "name": page.get("name")},
            "facebook_user": {"id": user.get("id"), "name": user.get("name"), "email": user.get("email")},
            "instagram_business_account": page.get("instagram_business_account"),
        }
        await session.flush()
        return credential

    async def _upsert_instagram_account(
        self,
        session: AsyncSession,
        credential: ProviderCredential,
        instagram_account: dict,
    ) -> InstagramAccount:
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


async def get_active_page_access_token(session: AsyncSession) -> str | None:
    credential = await session.scalar(
        select(ProviderCredential)
        .where(
            ProviderCredential.provider_type == ProviderType.facebook_page_backed,
            ProviderCredential.is_active.is_(True),
            ProviderCredential.encrypted_access_token.is_not(None),
        )
        .order_by(ProviderCredential.updated_at.desc())
    )
    if not credential or not credential.encrypted_access_token:
        return None
    return decrypt_secret(credential.encrypted_access_token)
