from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.social import NormalizedEvent


@dataclass(slots=True)
class ProviderActionResult:
    ok: bool
    provider_action_id: str | None = None
    status_code: int | None = None
    response: dict = field(default_factory=dict)
    error: str | None = None


class SocialProvider(Protocol):
    async def verify_webhook(self, mode: str | None, token: str | None, challenge: str | None) -> str:
        ...

    async def normalize_event(self, payload: dict) -> list[NormalizedEvent]:
        ...

    async def reply_to_comment(self, comment_id: str, message: str) -> ProviderActionResult:
        ...

    async def send_private_reply(self, comment_id: str, message: str) -> ProviderActionResult:
        ...

    async def send_dm(self, recipient_id: str, message: str) -> ProviderActionResult:
        ...

    async def hide_comment(self, comment_id: str) -> ProviderActionResult:
        ...

    async def like_comment(self, comment_id: str) -> ProviderActionResult:
        ...

    async def send_whatsapp_template(
        self, phone: str, template_name: str, variables: list[str] | None = None
    ) -> ProviderActionResult:
        ...

