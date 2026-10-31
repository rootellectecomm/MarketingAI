"""Dashboard API for WhatsApp order notifications, consent and offer broadcasts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Order, WhatsAppContact, WhatsAppNotification
from app.services.whatsapp_orders import WhatsAppOrderService, normalize_phone
from app.services.whatsapp_templates import TEMPLATES

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"], dependencies=[Depends(get_current_user)])


def _notification_out(row: WhatsAppNotification) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "template": row.template_name,
        "category": row.category,
        "phone": f"+{row.phone[:4]}••••{row.phone[-3:]}" if len(row.phone) > 7 else row.phone,
        "order": row.order_external_id,
        "status": row.status,
        "scheduled_for": row.scheduled_for,
        "sent_at": row.sent_at,
        "delivered_at": row.delivered_at,
        "read_at": row.read_at,
        "attempts": row.attempts,
        "error": row.error,
    }


@router.get("/notifications")
async def list_notifications(
    session: AsyncSession = Depends(get_session),
    status: str | None = None,
    order: str | None = None,
    kind: str | None = None,
    limit: int = Query(default=100, le=500),
) -> dict:
    stmt = select(WhatsAppNotification).order_by(WhatsAppNotification.scheduled_for.desc()).limit(limit)
    if status:
        stmt = stmt.where(WhatsAppNotification.status == status)
    if order:
        stmt = stmt.where(WhatsAppNotification.order_external_id == order)
    if kind:
        stmt = stmt.where(WhatsAppNotification.kind == kind)
    rows = (await session.execute(stmt)).scalars().all()
    totals = dict(
        (await session.execute(select(WhatsAppNotification.status, func.count()).group_by(WhatsAppNotification.status))).all()
    )
    return {"items": [_notification_out(row) for row in rows], "totals": totals}


@router.get("/cod-responses")
async def cod_responses(session: AsyncSession = Depends(get_session), limit: int = Query(default=100, le=500)) -> dict:
    """COD orders and whether the customer confirmed, cancelled or hasn't replied yet."""
    rows = (
        await session.execute(
            select(Order).where(Order.source == "rootellect").order_by(Order.created_at.desc()).limit(limit * 3)
        )
    ).scalars().all()
    items = []
    for order in rows:
        meta = order.metadata_json or {}
        if meta.get("payment_method") != "cod":
            continue
        items.append(
            {
                "order": order.external_order_id,
                "status": order.status,
                "cod_status": meta.get("cod_status", "awaiting_reply"),
                "responded_at": meta.get("cod_responded_at"),
                "total": order.total_amount,
                "created_at": order.created_at,
            }
        )
        if len(items) >= limit:
            break
    return {"items": items}


@router.get("/templates")
async def list_templates() -> dict:
    return {
        "items": [
            {"kind": t.kind, "name": t.name, "category": t.category, "consent": t.consent, "body": t.body}
            for t in TEMPLATES.values()
        ]
    }


class OptInRequest(BaseModel):
    phone: str
    marketing: bool = True
    source: str = Field(min_length=3, max_length=64, description="Where consent was collected, e.g. 'instagram_dm_2026_11'")
    first_name: str | None = None


@router.post("/contacts/opt-in")
async def record_opt_in(body: OptInRequest, session: AsyncSession = Depends(get_session)) -> dict:
    """Record consent collected outside WhatsApp. Only use with real proof of opt-in."""
    phone = normalize_phone(body.phone)
    if not phone:
        raise HTTPException(status_code=422, detail="Invalid phone number")
    service = WhatsAppOrderService()
    contact = await service.upsert_contact(session, phone, first_name=body.first_name, transactional_source=body.source)
    if body.marketing:
        service.set_marketing_opt_in(contact, body.source)
    else:
        contact.marketing_opt_in = False
    await session.commit()
    return {"ok": True, "phone": phone, "marketing_opt_in": contact.marketing_opt_in}


class BroadcastRequest(BaseModel):
    template_name: str = Field(min_length=1, max_length=255, description="An APPROVED marketing template in WhatsApp Manager")
    language: str | None = None
    body_params: list[str] = Field(
        default_factory=list, description="Same values for every recipient. Use '{first_name}' to personalise."
    )
    button_params: list[dict] = Field(default_factory=list)
    scheduled_for: datetime | None = None
    max_recipients: int = Field(default=1000, ge=1, le=10000)
    dry_run: bool = True


@router.post("/broadcasts")
async def create_broadcast(body: BroadcastRequest, session: AsyncSession = Depends(get_session)) -> dict:
    """Queue an offer to every marketing-opted-in contact. Defaults to a dry run that only counts recipients."""
    contacts = (
        await session.execute(
            select(WhatsAppContact)
            .where(WhatsAppContact.marketing_opt_in.is_(True), WhatsAppContact.opted_out_at.is_(None))
            .limit(body.max_recipients)
        )
    ).scalars().all()
    if body.dry_run:
        return {"ok": True, "dry_run": True, "recipients": len(contacts)}

    service = WhatsAppOrderService()
    broadcast_id = uuid.uuid4().hex[:12]
    when = body.scheduled_for or datetime.now(UTC)
    when = service.next_send_time(when if when.tzinfo else when.replace(tzinfo=UTC))
    queued = 0
    for contact in contacts:
        first = (contact.first_name or "there").split(" ")[0][:40]
        params = [value.replace("{first_name}", first) for value in body.body_params]
        created = await service.queue(
            session,
            key=f"broadcast:{broadcast_id}:{contact.phone}",
            kind="broadcast",
            phone=contact.phone,
            body_params=params,
            button_params=body.button_params,
            scheduled_for=when,
            template_name=body.template_name,
            category="marketing",
            metadata={"broadcast_id": broadcast_id, **({"language": body.language} if body.language else {})},
        )
        queued += 1 if created else 0
    await session.commit()
    return {"ok": True, "broadcast_id": broadcast_id, "queued": queued, "scheduled_for": when}


@router.post("/dispatch")
async def dispatch_now(session: AsyncSession = Depends(get_session)) -> dict:
    counts = await WhatsAppOrderService().dispatch_due(session, limit=40)
    await session.commit()
    return {"ok": True, **counts}
