from __future__ import annotations

from uuid import uuid4

from app.core.config import get_settings
from app.models.enums import EventType, ProviderType
from app.schemas.social import NormalizedEvent
from app.services.providers.base import ProviderActionResult


class MockMetaProvider:
    async def verify_webhook(self, mode: str | None, token: str | None, challenge: str | None) -> str:
        settings = get_settings()
        if mode == "subscribe" and token == settings.meta_verify_token and challenge:
            return challenge
        raise ValueError("Invalid webhook verification token")

    async def normalize_event(self, payload: dict) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        entries = payload.get("entry") or [payload]
        for entry in entries:
            changes = entry.get("changes") or []
            if not changes and "text" in entry:
                changes = [{"field": "comments", "value": entry}]
            for index, change in enumerate(changes):
                value = change.get("value") or {}
                field = change.get("field", "comments")
                event_type = EventType.instagram_comment
                if field in {"messages", "messaging"}:
                    event_type = EventType.instagram_dm
                event_id = str(
                    value.get("id")
                    or value.get("comment_id")
                    or value.get("message_id")
                    or f"mock-{entry.get('id', 'entry')}-{index}-{uuid4()}"
                )
                events.append(
                    NormalizedEvent(
                        provider=ProviderType.mock,
                        event_type=event_type,
                        provider_event_id=event_id,
                        actor_id=str((value.get("from") or {}).get("id") or value.get("user_id") or "mock-user"),
                        actor_username=(value.get("from") or {}).get("username") or value.get("username"),
                        text=value.get("text") or value.get("message") or "",
                        provider_comment_id=value.get("comment_id") or value.get("id"),
                        provider_message_id=value.get("message_id"),
                        media_id=value.get("media_id") or (value.get("media") or {}).get("id"),
                        payload=value,
                    )
                )
        return events

    async def reply_to_comment(self, comment_id: str, message: str) -> ProviderActionResult:
        return ProviderActionResult(ok=True, provider_action_id=f"mock-comment-{comment_id}", response={"message": message})

    async def send_private_reply(self, comment_id: str, message: str) -> ProviderActionResult:
        return ProviderActionResult(ok=True, provider_action_id=f"mock-private-{comment_id}", response={"message": message})

    async def send_dm(self, recipient_id: str, message: str) -> ProviderActionResult:
        return ProviderActionResult(ok=True, provider_action_id=f"mock-dm-{recipient_id}", response={"message": message})

    async def hide_comment(self, comment_id: str) -> ProviderActionResult:
        return ProviderActionResult(ok=True, provider_action_id=f"mock-hide-{comment_id}")

    async def like_comment(self, comment_id: str) -> ProviderActionResult:
        return ProviderActionResult(ok=True, provider_action_id=f"mock-like-{comment_id}")

    async def send_whatsapp_template(
        self, phone: str, template_name: str, variables: list[str] | None = None
    ) -> ProviderActionResult:
        return ProviderActionResult(
            ok=True,
            provider_action_id=f"mock-wa-{phone}",
            response={"template": template_name, "variables": variables or []},
        )

