from datetime import datetime

from pydantic import BaseModel, Field


class LeadRead(BaseModel):
    id: str
    external_user_id: str
    username: str | None
    source_channel: str
    lifecycle_stage: str
    phone: str | None
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
    product_focus: list[str] = Field(default_factory=list)
    keyword_triggers: list[str] = Field(default_factory=list)
    public_reply_enabled: bool = True
    dm_enabled: bool = True
    whatsapp_followup_enabled: bool = False
    metadata_json: dict = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    product_focus: list[str] | None = None
    keyword_triggers: list[str] | None = None
    public_reply_enabled: bool | None = None
    dm_enabled: bool | None = None
    whatsapp_followup_enabled: bool | None = None
    metadata_json: dict | None = None


class CampaignRead(CampaignCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}

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

