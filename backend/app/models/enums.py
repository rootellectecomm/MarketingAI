from enum import StrEnum


class UserRole(StrEnum):
    owner = "owner"
    admin = "admin"
    agent = "agent"


class ProviderType(StrEnum):
    instagram_professional = "instagram_professional"
    facebook_page_backed = "facebook_page_backed"
    whatsapp_cloud = "whatsapp_cloud"
    mock = "mock"


class EventType(StrEnum):
    instagram_comment = "instagram_comment"
    instagram_mention = "instagram_mention"
    instagram_dm = "instagram_dm"
    whatsapp_message = "whatsapp_message"
    whatsapp_status = "whatsapp_status"


class EventStatus(StrEnum):
    received = "received"
    queued = "queued"
    processing = "processing"
    processed = "processed"
    duplicate = "duplicate"
    failed = "failed"


class ModerationAction(StrEnum):
    allow = "allow"
    hide = "hide"
    escalate = "escalate"
    block = "block"


class SendDecision(StrEnum):
    send = "send"
    queue_for_review = "queue_for_review"
    suppress = "suppress"
    escalate = "escalate"


class ActionStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    skipped = "skipped"
    failed = "failed"
    retrying = "retrying"

