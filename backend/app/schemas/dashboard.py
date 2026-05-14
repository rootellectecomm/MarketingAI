from datetime import datetime

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: int | float | str
    delta: float = 0


class DashboardMetrics(BaseModel):
    comments: int
    leads: int
    automated_actions: int
    escalations: int
    avg_ai_confidence: float
    sentiment: dict[str, int]
    latest_activity: list[dict]


class AILogRead(BaseModel):
    id: str
    model: str
    prompt_version: str
    output_json: dict
    confidence: float
    blocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ModerationLogRead(BaseModel):
    id: str
    action: str
    flags: list[str]
    confidence: float
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

