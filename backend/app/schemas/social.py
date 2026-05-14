from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EventType, ProviderType


class NormalizedEvent(BaseModel):
    provider: ProviderType
    event_type: EventType
    provider_event_id: str
    actor_id: str | None = None
    actor_username: str | None = None
    text: str | None = None
    provider_comment_id: str | None = None
    provider_message_id: str | None = None
    media_id: str | None = None
    timestamp: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CommentRead(BaseModel):
    id: str
    provider_comment_id: str
    media_id: str | None
    username: str | None
    text: str
    normalized_text: str
    hidden: bool
    replied: bool
    private_replied: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookLogRead(BaseModel):
    id: str
    provider: ProviderType
    event_id: str | None
    signature_valid: bool
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderStatus(BaseModel):
    provider_mode: str
    instagram_ready: bool
    whatsapp_ready: bool
    openai_ready: bool
    chroma_collection: str
