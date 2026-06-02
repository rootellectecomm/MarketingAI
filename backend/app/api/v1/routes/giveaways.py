from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import (
    AutomationEventLog,
    GiveawayAutomation,
    GiveawayContent,
    GiveawayParticipant,
    GlobalGiveawaySetting,
)
from app.schemas.giveaway import (
    GiveawayAnalytics,
    GiveawayCreate,
    GiveawayDrawResult,
    GiveawayParticipantRead,
    GiveawayRead,
    GiveawaySettingPayload,
    GiveawaySettingRead,
    GiveawayUpdate,
)
from app.services.giveaway_processor import GiveawayProcessor

router = APIRouter(prefix="/giveaways", tags=["giveaways"], dependencies=[Depends(get_current_user)])


async def _read_giveaway(session: AsyncSession, automation: GiveawayAutomation) -> GiveawayRead:
    content = await session.scalar(select(GiveawayContent).where(GiveawayContent.automation_id == automation.id))
    participant_count = await session.scalar(
        select(func.count()).select_from(GiveawayParticipant).where(GiveawayParticipant.automation_id == automation.id)
    )
    reward_sent_count = await session.scalar(
        select(func.count())
        .select_from(GiveawayParticipant)
        .where(GiveawayParticipant.automation_id == automation.id, GiveawayParticipant.reward_sent.is_(True))
    )
    data = GiveawayRead.model_validate(automation).model_dump()
    data["content"] = content
    data["participant_count"] = int(participant_count or 0)
    data["reward_sent_count"] = int(reward_sent_count or 0)
    return GiveawayRead.model_validate(data)


@router.get("", response_model=list[GiveawayRead])
async def list_giveaways(session: AsyncSession = Depends(get_session)) -> list[GiveawayRead]:
    automations = (
        await session.scalars(select(GiveawayAutomation).order_by(GiveawayAutomation.created_at.desc()))
    ).all()
    return [await _read_giveaway(session, automation) for automation in automations]


@router.post("", response_model=GiveawayRead)
async def create_giveaway(payload: GiveawayCreate, session: AsyncSession = Depends(get_session)) -> GiveawayRead:
    content_payload = payload.content
    automation_data = payload.model_dump(exclude={"content"})
    automation = GiveawayAutomation(**automation_data)
    session.add(automation)
    await session.flush()
    session.add(GiveawayContent(automation_id=automation.id, **content_payload.model_dump()))
    await session.commit()
    await session.refresh(automation)
    return await _read_giveaway(session, automation)


@router.patch("/{automation_id}", response_model=GiveawayRead)
async def update_giveaway(
    automation_id: str,
    payload: GiveawayUpdate,
    session: AsyncSession = Depends(get_session),
) -> GiveawayRead:
    automation = await session.get(GiveawayAutomation, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Giveaway automation not found")

    data = payload.model_dump(exclude_unset=True, exclude={"content"})
    for key, value in data.items():
        setattr(automation, key, value)

    if payload.content:
        content = await session.scalar(select(GiveawayContent).where(GiveawayContent.automation_id == automation.id))
        if not content:
            content = GiveawayContent(automation_id=automation.id)
            session.add(content)
        for key, value in payload.content.model_dump(exclude_unset=True).items():
            setattr(content, key, value)

    await session.commit()
    await session.refresh(automation)
    return await _read_giveaway(session, automation)


@router.get("/{automation_id}/participants", response_model=list[GiveawayParticipantRead])
async def list_participants(
    automation_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[GiveawayParticipantRead]:
    result = await session.scalars(
        select(GiveawayParticipant)
        .where(GiveawayParticipant.automation_id == automation_id)
        .order_by(GiveawayParticipant.created_at.desc())
    )
    return [GiveawayParticipantRead.model_validate(item) for item in result.all()]


@router.post("/{automation_id}/draw", response_model=GiveawayDrawResult)
async def draw_winners(
    automation_id: str,
    count: int = 1,
    session: AsyncSession = Depends(get_session),
) -> GiveawayDrawResult:
    automation = await session.get(GiveawayAutomation, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Giveaway automation not found")
    winners = await GiveawayProcessor().draw_winners(session, automation_id, count=count)
    await session.commit()
    return GiveawayDrawResult(
        automation_id=automation_id,
        winner_ids=[winner.id for winner in winners],
        message=f"Selected {len(winners)} winner(s).",
    )


@router.get("/settings/global", response_model=GiveawaySettingRead)
async def get_global_settings(session: AsyncSession = Depends(get_session)) -> GiveawaySettingRead:
    settings = await session.scalar(select(GlobalGiveawaySetting).order_by(GlobalGiveawaySetting.created_at.desc()))
    if not settings:
        settings = GlobalGiveawaySetting()
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return GiveawaySettingRead.model_validate(settings)


@router.patch("/settings/global", response_model=GiveawaySettingRead)
async def update_global_settings(
    payload: GiveawaySettingPayload,
    session: AsyncSession = Depends(get_session),
) -> GiveawaySettingRead:
    settings = await session.scalar(select(GlobalGiveawaySetting).order_by(GlobalGiveawaySetting.created_at.desc()))
    if not settings:
        settings = GlobalGiveawaySetting()
        session.add(settings)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    await session.commit()
    await session.refresh(settings)
    return GiveawaySettingRead.model_validate(settings)


@router.get("/analytics/summary", response_model=GiveawayAnalytics)
async def giveaway_analytics(session: AsyncSession = Depends(get_session)) -> GiveawayAnalytics:
    participants = list((await session.scalars(select(GiveawayParticipant))).all())
    logs = list((await session.scalars(select(AutomationEventLog).where(AutomationEventLog.automation_type == "giveaway"))).all())
    rewards = [participant for participant in participants if participant.reward_sent]
    trigger_counts = Counter(participant.trigger_matched or "unknown" for participant in participants)
    post_counts = Counter(participant.automation_id for participant in participants)
    excluded = len([log for log in logs if log.event_name == "excluded_comment"])
    dms_sent = len(
        [participant for participant in participants if participant.status in {"dm_sent", "follow_confirmed", "reward_sent"}]
    )
    total = len(participants)
    return GiveawayAnalytics(
        total_comments_captured=total + excluded,
        valid_participants=total,
        excluded_comments=excluded,
        dms_sent=dms_sent,
        rewards_claimed=len(rewards),
        conversion_rate=round((len(rewards) / total) * 100, 2) if total else 0,
        top_trigger_keywords=[{"keyword": key, "count": value} for key, value in trigger_counts.most_common(8)],
        post_performance=[{"automation_id": key, "participants": value} for key, value in post_counts.most_common(8)],
    )


@router.get("/templates/rootellect")
async def rootellect_templates() -> list[dict]:
    return [
        {
            "name": "Mind Calm giveaway",
            "trigger_keywords": ["calm", "sleep", "stress", "overthinking"],
            "public_reply_text": "Thanks for joining. Please check your DM.",
            "dm_message_text": "You're in. Follow Rootellect and reply I have followed to receive your Mind Calm wellness guide.",
            "content": {
                "content_type": "coupon",
                "coupon_code": "MINDCALM10",
                "message_text": "Here is your Mind Calm sleep routine and launch coupon.",
                "cta_label": "Open sleep routine",
                "cta_url": "https://rootellect.com",
            },
        },
        {
            "name": "Women Balance giveaway",
            "trigger_keywords": ["hormones", "pms", "energy", "balance"],
            "public_reply_text": "Thanks for joining. Please check your DM.",
            "dm_message_text": "You're in. Follow Rootellect and reply I have followed to receive your women wellness checklist.",
            "content": {
                "content_type": "coupon",
                "coupon_code": "BALANCE10",
                "message_text": "Here is your women wellness checklist and Rootellect coupon.",
                "cta_label": "Open checklist",
                "cta_url": "https://rootellect.com",
            },
        },
    ]
