from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ModerationAction, SendDecision

ROOTELLECT_PRODUCTS = [
    "Mind Calm",
    "PCOS Support",
    "Women Multivitamin 18+",
    "Women Multivitamin 40+",
    "ACV Moringa",
    "Menopause Prime Support",
    "Menopause Bone & Joint Support",
    "Preworkout",
    "D3 & Calcium",
]


class RetrievedContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    category: str
    content: str
    score: float = 0.0
    source: str = "knowledge_base"


class AIDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal[
        "product_question",
        "price_question",
        "shipping_question",
        "refund_question",
        "purchase_intent",
        "complaint",
        "praise",
        "spam",
        "abuse",
        "medical_risk",
        "general",
    ] = "general"
    sentiment: Literal["positive", "neutral", "negative", "mixed"] = "neutral"
    urgency: Literal["low", "medium", "high"] = "low"
    purchase_intent: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_products: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_flags: list[str] = Field(default_factory=list)
    moderation_action: ModerationAction = ModerationAction.allow
    public_reply: str = ""
    private_dm: str = ""
    whatsapp_followup: str | None = None
    lead_score_delta: int = 0
    escalation_reason: str | None = None
    send_decision: SendDecision = SendDecision.queue_for_review


class ThreadMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str
    body: str
    channel: str = "instagram"


class AIRequestContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    username: str | None = None
    channel: str = "instagram"
    media_id: str | None = None
    retrieved_context: list[RetrievedContext] = Field(default_factory=list)
    thread_history: list[ThreadMessage] = Field(default_factory=list)
    lead_score: int = 0
    lifecycle_stage: str = "new"
    matched_campaigns: list[str] = Field(default_factory=list)
    campaign_product_focus: list[str] = Field(default_factory=list)
    allow_public_reply: bool = True
    allow_dm: bool = True
    allow_whatsapp_followup: bool = False
    wellness_segment: str | None = None


class ModerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ModerationAction
    flags: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    notes: str | None = None
