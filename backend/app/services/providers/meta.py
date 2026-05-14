from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.models.enums import EventType, ProviderType
from app.schemas.social import NormalizedEvent
from app.services.providers.base import ProviderActionResult
from app.services.providers.mock import MockMetaProvider


class InstagramProfessionalProvider(MockMetaProvider):
    provider_type = ProviderType.instagram_professional

    def __init__(self, access_token: str | None = None) -> None:
        self.settings = get_settings()
        self.access_token = access_token

    async def normalize_event(self, payload: dict) -> list[NormalizedEvent]:
        events = await super().normalize_event(payload)
        return [event.model_copy(update={"provider": self.provider_type}) for event in events]

    async def reply_to_comment(self, comment_id: str, message: str) -> ProviderActionResult:
        return await self._post_graph(f"{comment_id}/replies", {"message": message})

    async def send_private_reply(self, comment_id: str, message: str) -> ProviderActionResult:
        return await self._post_graph("me/messages", {"recipient": {"comment_id": comment_id}, "message": {"text": message}})

    async def send_dm(self, recipient_id: str, message: str) -> ProviderActionResult:
        return await self._post_graph("me/messages", {"recipient": {"id": recipient_id}, "message": {"text": message}})

    async def hide_comment(self, comment_id: str) -> ProviderActionResult:
        return await self._post_graph(comment_id, {"hide": True})

    async def like_comment(self, comment_id: str) -> ProviderActionResult:
        return await self._post_graph(f"{comment_id}/likes", {})

    async def _post_graph(self, path: str, payload: dict) -> ProviderActionResult:
        if not self.access_token:
            return ProviderActionResult(ok=False, error="Missing Instagram access token")
        url = f"https://graph.instagram.com/{self.settings.meta_graph_version}/{path}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {self.access_token}"})
            data = response.json() if response.content else {}
            return ProviderActionResult(
                ok=response.is_success,
                provider_action_id=str(data.get("id") or data.get("message_id") or ""),
                status_code=response.status_code,
                response=data,
                error=None if response.is_success else str(data),
            )
        except httpx.HTTPError as exc:
            return ProviderActionResult(ok=False, error=str(exc))


class FacebookPageBackedProvider(InstagramProfessionalProvider):
    provider_type = ProviderType.facebook_page_backed

    async def normalize_event(self, payload: dict) -> list[NormalizedEvent]:
        events = await super().normalize_event(payload)
        normalized: list[NormalizedEvent] = []
        for event in events:
            event_type = event.event_type
            if event.payload.get("item") == "comment":
                event_type = EventType.instagram_comment
            normalized.append(event.model_copy(update={"provider": self.provider_type, "event_type": event_type}))
        return normalized

    async def _post_graph(self, path: str, payload: dict) -> ProviderActionResult:
        if not self.access_token:
            return ProviderActionResult(ok=False, error="Missing Page access token")
        url = f"https://graph.facebook.com/{self.settings.meta_graph_version}/{path}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {self.access_token}"})
            data = response.json() if response.content else {}
            return ProviderActionResult(
                ok=response.is_success,
                provider_action_id=str(data.get("id") or data.get("message_id") or ""),
                status_code=response.status_code,
                response=data,
                error=None if response.is_success else str(data),
            )
        except httpx.HTTPError as exc:
            return ProviderActionResult(ok=False, error=str(exc))


class WhatsAppCloudProvider(MockMetaProvider):
    def __init__(self, access_token: str | None = None) -> None:
        self.settings = get_settings()
        self.access_token = access_token or self.settings.whatsapp_access_token

    async def normalize_event(self, payload: dict) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value") or {}
                for message in value.get("messages", []):
                    text = (message.get("text") or {}).get("body") or ""
                    events.append(
                        NormalizedEvent(
                            provider=ProviderType.whatsapp_cloud,
                            event_type=EventType.whatsapp_message,
                            provider_event_id=message.get("id", ""),
                            actor_id=message.get("from"),
                            actor_username=message.get("from"),
                            text=text,
                            provider_message_id=message.get("id"),
                            payload=message,
                        )
                    )
        return events

    async def send_whatsapp_template(
        self, phone: str, template_name: str, variables: list[str] | None = None
    ) -> ProviderActionResult:
        if not self.access_token or not self.settings.whatsapp_phone_number_id:
            return ProviderActionResult(ok=False, error="Missing WhatsApp credentials")
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": value} for value in (variables or [])],
                    }
                ],
            },
        }
        url = (
            f"https://graph.facebook.com/{self.settings.meta_graph_version}/"
            f"{self.settings.whatsapp_phone_number_id}/messages"
        )
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {self.access_token}"})
            data = response.json() if response.content else {}
            return ProviderActionResult(
                ok=response.is_success,
                provider_action_id=str((data.get("messages") or [{}])[0].get("id", "")),
                status_code=response.status_code,
                response=data,
                error=None if response.is_success else str(data),
            )
        except httpx.HTTPError as exc:
            return ProviderActionResult(ok=False, error=str(exc))

