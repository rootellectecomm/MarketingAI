from datetime import datetime

from pydantic import BaseModel, Field


class LeadRead(BaseModel):
    id: str
    external_user_id: str
    username: str | None
    source_channel: str
    platform: str = "instagram"
    lifecycle_stage: str
    phone: str | None
    product_interest: str | None = None
    intent_level: str = "low"
    last_message: str | None = None
    source_campaign_id: str | None = None
    conversion_stage: str = "new"
    whatsapp_opt_in: bool
    score: int
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    lifecycle_stage: str | None = None
    phone: str | None = None
    whatsapp_opt_in: bool | None = None
    tags: list[str] | None = None


class CampaignCreate(BaseModel):
    name: str
    status: str = "draft"
    platform: str = "both"
    post_id: str | None = None
    product_key: str | None = None
    product_name: str | None = None
    product_link: str | None = None
    followup_link: str | None = None
    whatsapp_link: str | None = None
    product_focus: list[str] = Field(default_factory=list)
    keyword_triggers: list[str] = Field(default_factory=list)
    public_reply_template: str = "Sent you the details in DM."
    dm_template: str = ""
    ai_prompt_override: str | None = None
    public_reply_enabled: bool = True
    dm_enabled: bool = True
    whatsapp_followup_enabled: bool = False
    ai_followup_enabled: bool = True
    metadata_json: dict = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    platform: str | None = None
    post_id: str | None = None
    product_key: str | None = None
    product_name: str | None = None
    product_link: str | None = None
    followup_link: str | None = None
    whatsapp_link: str | None = None
    product_focus: list[str] | None = None
    keyword_triggers: list[str] | None = None
    public_reply_template: str | None = None
    dm_template: str | None = None
    ai_prompt_override: str | None = None
    public_reply_enabled: bool | None = None
    dm_enabled: bool | None = None
    whatsapp_followup_enabled: bool | None = None
    ai_followup_enabled: bool | None = None
    metadata_json: dict | None = None


class CampaignRead(CampaignCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignEventRead(BaseModel):
    id: str
    campaign_id: str
    platform: str
    source_type: str
    user_id: str | None
    username: str | None
    comment_id: str | None
    message_id: str | None
    matched_keyword: str | None
    user_text: str
    ai_intent: str | None
    lead_score: int
    status: str
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignTestRequest(BaseModel):
    text: str
    platform: str = "instagram"
    post_id: str | None = None


class CampaignTestResult(BaseModel):
    matched_campaign: CampaignRead | None = None
    matched_keyword: str | None = None
    public_reply_preview: str = ""
    dm_preview: str = ""
    product_selected: str | None = None
    lead_score: int = 0
    ai_intent: str = "unclear"

class KnowledgeCreate(BaseModel):
    title: str
    category: str = "general"
    content: str
    source: str = "admin"


class KnowledgeRead(KnowledgeCreate):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
