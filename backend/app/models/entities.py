from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin
from app.models.enums import ActionStatus, EventStatus, EventType, ModerationAction, ProviderType, UserRole


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="Rootellect Admin")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), default=UserRole.admin)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "auth_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProviderCredential(Base, IdMixin, TimestampMixin):
    __tablename__ = "provider_credentials"

    provider_type: Mapped[ProviderType] = mapped_column(Enum(ProviderType, native_enum=False), index=True)
    account_name: Mapped[str] = mapped_column(String(255))
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class InstagramAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "instagram_accounts"

    provider_credential_id: Mapped[str | None] = mapped_column(ForeignKey("provider_credentials.id"))
    ig_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    auth_path: Mapped[str] = mapped_column(String(64), default="mock")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WhatsAppAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "whatsapp_accounts"

    provider_credential_id: Mapped[str | None] = mapped_column(ForeignKey("provider_credentials.id"))
    phone_number_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    waba_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WebhookLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "webhook_logs"

    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType, native_enum=False), index=True)
    event_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus, native_enum=False), default=EventStatus.received)
    request_headers: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_webhook_provider_event_id", "provider", "event_id", unique=False),)


class SocialEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "social_events"

    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType, native_enum=False), index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False), index=True)
    provider_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    actor_username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus, native_enum=False), default=EventStatus.queued)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    webhook_log_id: Mapped[str | None] = mapped_column(ForeignKey("webhook_logs.id"), nullable=True)


class Comment(Base, IdMixin, TimestampMixin):
    __tablename__ = "comments"

    social_event_id: Mapped[str | None] = mapped_column(ForeignKey("social_events.id"), nullable=True)
    provider_comment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    media_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(32), default="en")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    private_replied: Mapped[bool] = mapped_column(Boolean, default=False)
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)


class Conversation(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversations"

    external_user_id: Mapped[str] = mapped_column(String(255), index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    messages: Mapped[list[Message]] = relationship(back_populates="conversation")


class Message(Base, IdMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AiLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "ai_logs"

    social_event_id: Mapped[str | None] = mapped_column(ForeignKey("social_events.id"), nullable=True)
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64), default="v1")
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class IntentAnalysis(Base, IdMixin, TimestampMixin):
    __tablename__ = "intent_analysis"

    social_event_id: Mapped[str | None] = mapped_column(ForeignKey("social_events.id"), nullable=True)
    intent: Mapped[str] = mapped_column(String(128), index=True)
    sentiment: Mapped[str] = mapped_column(String(64), index=True)
    urgency: Mapped[str] = mapped_column(String(64), index=True)
    purchase_intent: Mapped[float] = mapped_column(Float, default=0)
    recommended_products: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    safety_flags: Mapped[list[str]] = mapped_column(JSON, default=list)


class Lead(Base, IdMixin, TimestampMixin):
    __tablename__ = "leads"

    external_user_id: Mapped[str] = mapped_column(String(255), index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_channel: Mapped[str] = mapped_column(String(64), default="instagram")
    lifecycle_stage: Mapped[str] = mapped_column(String(64), default="new")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_leads_external_channel", "external_user_id", "source_channel"),)


class LeadScore(Base, IdMixin, TimestampMixin):
    __tablename__ = "lead_scores"

    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    score_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Campaign(Base, IdMixin, TimestampMixin):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(64), default="draft", index=True)
    product_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    keyword_triggers: Mapped[list[str]] = mapped_column(JSON, default=list)
    public_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    dm_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_followup_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ModerationLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "moderation_logs"

    social_event_id: Mapped[str | None] = mapped_column(ForeignKey("social_events.id"), nullable=True)
    comment_id: Mapped[str | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    action: Mapped[ModerationAction] = mapped_column(Enum(ModerationAction, native_enum=False))
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnalyticsEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "analytics"

    event_name: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    value: Mapped[float] = mapped_column(Float, default=1)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)


class DailyMetric(Base, IdMixin, TimestampMixin):
    __tablename__ = "daily_metrics"

    metric_date: Mapped[str] = mapped_column(String(10), index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[float] = mapped_column(Float, default=0)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)


class KnowledgeDocument(Base, IdMixin, TimestampMixin):
    __tablename__ = "knowledge_base"

    title: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeChunk(Base, IdMixin, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_base.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ProductEmbedding(Base, IdMixin, TimestampMixin):
    __tablename__ = "product_embeddings"

    product_name: Mapped[str] = mapped_column(String(255), index=True)
    embedding_id: Mapped[str] = mapped_column(String(255), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ActionAttempt(Base, IdMixin, TimestampMixin):
    __tablename__ = "action_attempts"

    social_event_id: Mapped[str | None] = mapped_column(ForeignKey("social_events.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType, native_enum=False), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus, native_enum=False), default=ActionStatus.pending)
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Funnel(Base, IdMixin, TimestampMixin):
    __tablename__ = "funnels"

    name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class FunnelStep(Base, IdMixin, TimestampMixin):
    __tablename__ = "funnel_steps"

    funnel_id: Mapped[str] = mapped_column(ForeignKey("funnels.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, default=0)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    delay_hours: Mapped[int] = mapped_column(Integer, default=0)
    message_template: Mapped[str] = mapped_column(Text)
    min_lead_score: Mapped[int] = mapped_column(Integer, default=0)
    max_lead_score: Mapped[int] = mapped_column(Integer, default=100)
    lifecycle_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class LeadFunnelState(Base, IdMixin, TimestampMixin):
    __tablename__ = "lead_funnel_states"

    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    funnel_id: Mapped[str] = mapped_column(ForeignKey("funnels.id", ondelete="CASCADE"), index=True)
    current_step_order: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_lead_funnel_unique", "lead_id", "funnel_id", unique=True),)


class Order(Base, IdMixin, TimestampMixin):
    __tablename__ = "orders"

    external_order_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), default="shopify", index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class CartAbandonment(Base, IdMixin, TimestampMixin):
    __tablename__ = "cart_abandonments"

    external_cart_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), default="shopify", index=True)
    status: Mapped[str] = mapped_column(String(64), default="abandoned", index=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

