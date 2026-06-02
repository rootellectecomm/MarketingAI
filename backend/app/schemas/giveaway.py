from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TriggerType = Literal["any_comment", "keyword_match", "exact_phrase"]


class GiveawayContentPayload(BaseModel):
    content_type: str = "coupon"
    coupon_code: str | None = None
    message_text: str | None = None
    image_url: str | None = None
    carousel_slides: list[dict[str, Any]] = Field(default_factory=list)
    cta_label: str | None = None
    cta_url: str | None = None
    expires_at: datetime | None = None
    unique_coupon_enabled: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class GiveawayCreate(BaseModel):
    name: str
    status: str = "draft"
    media_id: str | None = None
    media_permalink: str | None = None
    trigger_type: TriggerType = "keyword_match"
    trigger_keywords: list[str] = Field(default_factory=list)
    public_reply_text: str = "Thanks for joining. Please check your DM."
    public_reply_variations: list[str] = Field(default_factory=list)
    dm_message_text: str = "You're in. Follow Rootellect and reply I have followed to receive your reward."
    follow_button_text: str = "I have followed"
    reply_limit: int = 500
    cooldown_hours: int = 24
    exclusion_keywords: list[str] = Field(default_factory=list)
    brand_signature: str | None = "Rootellect"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    content: GiveawayContentPayload = Field(default_factory=GiveawayContentPayload)


class GiveawayUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    media_id: str | None = None
    media_permalink: str | None = None
    trigger_type: TriggerType | None = None
    trigger_keywords: list[str] | None = None
    public_reply_text: str | None = None
    public_reply_variations: list[str] | None = None
    dm_message_text: str | None = None
    follow_button_text: str | None = None
    reply_limit: int | None = None
    cooldown_hours: int | None = None
    exclusion_keywords: list[str] | None = None
    brand_signature: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, Any] | None = None
    content: GiveawayContentPayload | None = None


class GiveawayContentRead(GiveawayContentPayload):
    id: str
    automation_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GiveawayRead(BaseModel):
    id: str
    name: str
    status: str
    media_id: str | None
    media_permalink: str | None
    trigger_type: str
    trigger_keywords: list[str]
    public_reply_text: str
    public_reply_variations: list[str]
    dm_message_text: str
    follow_button_text: str
    reply_limit: int
    cooldown_hours: int
    exclusion_keywords: list[str]
    brand_signature: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    content: GiveawayContentRead | None = None
    participant_count: int = 0
    reward_sent_count: int = 0

    model_config = {"from_attributes": True}


class GiveawayParticipantRead(BaseModel):
    id: str
    automation_id: str
    instagram_user_id: str
    instagram_username: str | None
    comment_text: str
    trigger_matched: str | None
    status: str
    reward_sent: bool
    error_message: str | None
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class GiveawaySettingPayload(BaseModel):
    default_public_reply_text: str = "Thanks for joining. Please check your DM."
    public_reply_variations: list[str] = Field(default_factory=list)
    comment_reply_limit: int = 500
    exclusion_keywords: list[str] = Field(default_factory=list)
    cooldown_hours: int = 24
    fallback_dm_text: str = "Thanks for joining the giveaway."
    brand_signature: str = "Rootellect"
    opt_out_keywords: list[str] = Field(default_factory=lambda: ["stop", "unsubscribe"])
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class GiveawaySettingRead(GiveawaySettingPayload):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GiveawayAnalytics(BaseModel):
    total_comments_captured: int
    valid_participants: int
    excluded_comments: int
    dms_sent: int
    rewards_claimed: int
    conversion_rate: float
    top_trigger_keywords: list[dict[str, int | str]]
    post_performance: list[dict[str, int | str | None]]


class GiveawayDrawResult(BaseModel):
    automation_id: str
    winner_ids: list[str]
    message: str
