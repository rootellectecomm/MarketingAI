from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Conversation, Message, User, WhatsAppContact
from app.services.live_agent import LiveAgentService
from app.services.provider_factory import get_whatsapp_provider

router = APIRouter(prefix="/conversations", tags=["conversations"], dependencies=[Depends(get_current_user)])

WHATSAPP_CHANNEL = "whatsapp_message"
SERVICE_WINDOW = timedelta(hours=24)


class ReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class HandoverRequest(BaseModel):
    active: bool


def _phone(conversation: Conversation) -> str:
    return "".join(ch for ch in str(conversation.external_user_id or "") if ch.isdigit())


async def _contacts_by_phone(session: AsyncSession, phones: list[str]) -> dict[str, WhatsAppContact]:
    if not phones:
        return {}
    rows = await session.scalars(select(WhatsAppContact).where(WhatsAppContact.phone.in_(phones)))
    return {row.phone: row for row in rows}


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _window(contact: WhatsAppContact | None, now: datetime) -> dict:
    last = _aware(contact.last_inbound_at) if contact else None
    open_ = bool(last and now - last < SERVICE_WINDOW)
    return {
        "reply_window_open": open_,
        "reply_window_closes_at": (last + SERVICE_WINDOW).isoformat() if last else None,
    }


async def _whatsapp_conversation(session: AsyncSession, conversation_id: str) -> tuple[Conversation, WhatsAppContact]:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.channel != WHATSAPP_CHANNEL:
        raise HTTPException(status_code=400, detail="Team replies are only available for WhatsApp chats")
    phone = _phone(conversation)
    contact = await session.scalar(select(WhatsAppContact).where(WhatsAppContact.phone == phone))
    if contact is None:
        contact = WhatsAppContact(phone=phone, transactional_opt_in_source="inbound_message")
        session.add(contact)
        await session.flush()
    return conversation, contact


@router.get("")
async def list_conversations(session: AsyncSession = Depends(get_session), limit: int = 50) -> list[dict]:
    result = await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()).limit(min(limit, 200)))
    conversations = result.scalars().all()
    live_agent = LiveAgentService()
    now = datetime.now(UTC)
    contacts = await _contacts_by_phone(
        session, [_phone(item) for item in conversations if item.channel == WHATSAPP_CHANNEL]
    )
    rows = []
    for item in conversations:
        row = {
            "id": item.id,
            "external_user_id": item.external_user_id,
            "username": item.username,
            "channel": item.channel,
            "last_message_at": item.last_message_at,
            "is_open": item.is_open,
        }
        if item.channel == WHATSAPP_CHANNEL:
            contact = contacts.get(_phone(item))
            row["customer_name"] = contact.first_name if contact else None
            row["live_agent"] = live_agent.public_state(contact, now)
            row.update(_window(contact, now))
        rows.append(row)
    return rows


@router.get("/{conversation_id}/messages")
async def list_messages(conversation_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).limit(200)
    )
    return [
        {
            "id": item.id,
            "direction": item.direction,
            "body": item.body,
            "channel": item.channel,
            "created_at": item.created_at,
            "sent_by": (item.metadata_json or {}).get("agent") if item.direction == "outbound" else None,
            "automated": bool((item.metadata_json or {}).get("automated")) if item.direction == "outbound" else None,
        }
        for item in result.scalars().all()
    ]


@router.post("/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: str,
    body: ReplyRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Send a message from a team member. Pauses the bot for this customer while the team chats."""
    conversation, contact = await _whatsapp_conversation(session, conversation_id)
    now = datetime.now(UTC)
    if not _window(contact, now)["reply_window_open"]:
        raise HTTPException(
            status_code=409,
            detail="WhatsApp only allows free replies within 24 hours of the customer's last message. "
            "Wait for the customer to message again, or send an approved template.",
        )
    text = body.text.strip()
    provider = await get_whatsapp_provider(session)
    result = await provider.send_whatsapp_text(contact.phone, text)
    if not result.ok:
        raise HTTPException(status_code=502, detail=f"WhatsApp did not accept the message: {result.error or 'unknown error'}")
    agent = user.full_name or user.email
    session.add(
        Message(
            conversation_id=conversation.id,
            provider_message_id=result.provider_action_id or None,
            direction="outbound",
            body=text,
            channel=WHATSAPP_CHANNEL,
            metadata_json={"automated": False, "agent": agent, "live_agent": "team_reply"},
        )
    )
    conversation.last_message_at = now
    live_agent = LiveAgentService()
    live_agent.record_team_reply(contact, agent, now)
    await session.commit()
    return {"ok": True, "live_agent": live_agent.public_state(contact, now)}


@router.post("/{conversation_id}/handover")
async def set_handover(
    conversation_id: str,
    body: HandoverRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """``active: true`` pauses the bot for this customer; ``false`` hands the chat back to the bot."""
    _, contact = await _whatsapp_conversation(session, conversation_id)
    live_agent = LiveAgentService()
    now = datetime.now(UTC)
    if body.active:
        live_agent.pause_bot(contact, user.full_name or user.email, now)
    else:
        live_agent.resume_bot(contact, now)
    await session.commit()
    return {"ok": True, "live_agent": live_agent.public_state(contact, now)}
