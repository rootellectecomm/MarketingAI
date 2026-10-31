"""WhatsApp order notifications for rootellect.com.

Flow:
1. rootellect.com posts signed order events (``/webhooks/rootellect/events``).
2. ``handle_event`` records the order and queues one ``WhatsAppNotification``
   per message, keyed so a repeated event never sends twice.
3. Order and COD confirmations are dispatched inline, straight away. Everything
   else is sent by ``dispatch_due`` from the scheduled job, inside the local
   send window (9:00-21:00 IST by default).
4. Inbound WhatsApp webhooks update delivery status, the 24-hour service
   window, STOP/START consent and COD confirm/cancel taps.

Consent is checked at send time, not at queue time, so a STOP that arrives
after a reminder was scheduled still wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.entities import Lead, Order, WhatsAppContact, WhatsAppNotification
from app.services.provider_factory import get_whatsapp_provider
from app.services.whatsapp_templates import WhatsAppTemplate, get_template

logger = structlog.get_logger(__name__)

STOP_KEYWORDS = {"stop", "unsubscribe", "stop all", "opt out", "optout"}
START_KEYWORDS = {"start", "subscribe", "join", "resume"}
COD_CONFIRM = "COD_CONFIRM"
COD_CANCEL = "COD_CANCEL"
MAX_ATTEMPTS = 3
# Meta error codes that will not succeed on retry.
PERMANENT_ERROR_CODES = {131026, 131050, 131051, 132000, 132001, 132005, 132007, 132012, 132015, 132016, 133010}
PENDING_STATUSES = ("scheduled", "retrying")
SHIPMENT_KINDS = {
    "shipped": "order_shipped",
    "out_for_delivery": "out_for_delivery",
    "delivered": "order_delivered",
    "delivery_failed": "delivery_failed",
}


class EventValidationError(ValueError):
    """The event payload is missing something we need."""


@dataclass
class EventResult:
    queued: list[str] = field(default_factory=list)
    sent: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"queued": self.queued, "sent": self.sent, "skipped": self.skipped}


def normalize_phone(raw: str | None) -> str | None:
    """Return WhatsApp ``wa_id`` digits (country code, no plus). Assumes India for 10-digit numbers."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return f"91{digits}"
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return digits
    if str(raw).strip().startswith("+") and 10 <= len(digits) <= 15:
        return digits
    return None


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _money(value: object) -> str:
    try:
        amount = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "0"
    rupees = round(amount)
    # Indian grouping: 1,23,456
    text = str(abs(rupees))
    if len(text) > 3:
        head, tail = text[:-3], text[-3:]
        head = ",".join(re.findall(r"\d{1,2}", head[::-1]))[::-1]
        text = f"{head},{tail}"
    return f"-{text}" if rupees < 0 else text


def _first_name(value: str | None) -> str:
    name = (value or "").strip().split(" ")[0]
    return name[:40] if name else "there"


def _product_label(lines: list[dict]) -> str:
    titles: list[str] = []
    for line in lines:
        title = str(line.get("title") or "").strip()
        if title and title not in titles:
            titles.append(title)
    if not titles:
        return "Rootellect order"
    if len(titles) == 1:
        label = titles[0]
        return label if label.lower().startswith("rootellect") else f"Rootellect {label}"
    if len(titles) == 2:
        return f"{titles[0]} and {titles[1]}"
    return "Rootellect products"


class WhatsAppOrderService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.tz = ZoneInfo(self.settings.whatsapp_send_timezone)

    # ------------------------------------------------------------------ timing
    def in_quiet_hours(self, when: datetime) -> bool:
        local = when.astimezone(self.tz)
        start, end = self.settings.whatsapp_quiet_hours_start, self.settings.whatsapp_quiet_hours_end
        if start == end:
            return False
        if start > end:
            return local.hour >= start or local.hour < end
        return start <= local.hour < end

    def next_send_time(self, when: datetime) -> datetime:
        """``when`` itself, or the next moment the send window opens."""
        if not self.in_quiet_hours(when):
            return when
        local = when.astimezone(self.tz)
        opening = datetime.combine(local.date(), time(self.settings.whatsapp_quiet_hours_end), tzinfo=self.tz)
        if opening <= local:
            opening += timedelta(days=1)
        return opening.astimezone(UTC)

    def at_local_time(self, base: datetime, days: int, hour: int, minute: int = 0) -> datetime:
        local_day = (base.astimezone(self.tz) + timedelta(days=days)).date()
        return datetime.combine(local_day, time(hour, minute), tzinfo=self.tz).astimezone(UTC)

    # ----------------------------------------------------------------- records
    async def get_contact(self, session: AsyncSession, phone: str) -> WhatsAppContact | None:
        return await session.scalar(select(WhatsAppContact).where(WhatsAppContact.phone == phone))

    async def upsert_contact(
        self,
        session: AsyncSession,
        phone: str,
        *,
        first_name: str | None = None,
        email: str | None = None,
        transactional_source: str | None = None,
    ) -> WhatsAppContact:
        contact = await self.get_contact(session, phone)
        if contact is None:
            contact = WhatsAppContact(
                phone=phone,
                first_name=first_name,
                email=email,
                transactional_opt_in=True,
                transactional_opt_in_source=transactional_source,
                marketing_opt_in=False,
                metadata_json={},
            )
            session.add(contact)
            await session.flush()
            return contact
        contact.first_name = first_name or contact.first_name
        contact.email = email or contact.email
        return contact

    def set_marketing_opt_in(self, contact: WhatsAppContact, source: str, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        contact.marketing_opt_in = True
        contact.marketing_opt_in_at = now
        contact.marketing_opt_in_source = source
        contact.transactional_opt_in = True
        contact.opted_out_at = None

    async def _upsert_order(self, session: AsyncSession, data: dict, phone: str) -> Order:
        number = str(data.get("order_number") or "").strip()
        order = await session.scalar(
            select(Order).where(Order.external_order_id == number, Order.source == "rootellect")
        )
        lines = [line for line in (data.get("lines") or []) if isinstance(line, dict)]
        meta_update = {
            "payment_method": "cod" if str(data.get("payment_method") or "").lower() == "cod" else "prepaid",
            "first_name": _first_name((data.get("customer") or {}).get("first_name")),
            "track_code": str(data.get("track_code") or number),
            "review_token": data.get("review_token"),
        }
        if order is None:
            order = Order(
                external_order_id=number,
                source="rootellect",
                status="confirmed",
                total_amount=float(data.get("total") or 0),
                currency=str(data.get("currency") or "INR"),
                customer_email=(data.get("customer") or {}).get("email"),
                customer_phone=phone,
                line_items=lines,
                metadata_json={k: v for k, v in meta_update.items() if v is not None},
            )
            session.add(order)
            await session.flush()
            return order
        order.total_amount = float(data.get("total") or order.total_amount or 0)
        order.customer_phone = phone or order.customer_phone
        if lines:
            order.line_items = lines
        order.metadata_json = {**(order.metadata_json or {}), **{k: v for k, v in meta_update.items() if v is not None}}
        return order

    async def queue(
        self,
        session: AsyncSession,
        *,
        key: str,
        kind: str,
        phone: str,
        body_params: list[str],
        button_params: list[dict] | None = None,
        scheduled_for: datetime,
        order_external_id: str | None = None,
        template_name: str | None = None,
        category: str | None = None,
        metadata: dict | None = None,
    ) -> WhatsAppNotification | None:
        existing = await session.scalar(select(WhatsAppNotification).where(WhatsAppNotification.idempotency_key == key))
        if existing is not None:
            return None
        template = get_template(kind) if template_name is None else None
        notification = WhatsAppNotification(
            idempotency_key=key,
            phone=phone,
            kind=kind,
            template_name=template_name or template.name,  # type: ignore[union-attr]
            category=(category or template.category).lower(),  # type: ignore[union-attr]
            order_external_id=order_external_id,
            body_params=[str(value) for value in body_params],
            button_params=button_params or [],
            status="scheduled",
            scheduled_for=scheduled_for,
            attempts=0,
            metadata_json=metadata or {},
        )
        session.add(notification)
        await session.flush()
        return notification

    async def _cancel_pending(self, session: AsyncSession, order_number: str, kinds: set[str] | None = None) -> int:
        rows = (
            await session.execute(
                select(WhatsAppNotification).where(
                    WhatsAppNotification.order_external_id == order_number,
                    WhatsAppNotification.status.in_(PENDING_STATUSES),
                )
            )
        ).scalars().all()
        count = 0
        for row in rows:
            if kinds is None or row.kind in kinds:
                row.status = "cancelled"
                count += 1
        return count

    # ------------------------------------------------------------------ events
    async def handle_event(self, session: AsyncSession, event: dict, now: datetime | None = None) -> EventResult:
        now = now or datetime.now(UTC)
        event_type = str(event.get("type") or "")
        result = EventResult()
        if not self.settings.whatsapp_order_notifications_enabled:
            result.skipped.append("notifications_disabled")
            return result

        if event_type == "checkout.abandoned":
            await self._handle_abandoned(session, event.get("checkout") or {}, now, result)
            return result

        order_data = event.get("order") or {}
        number = str(order_data.get("order_number") or "").strip()
        if not number:
            raise EventValidationError("order.order_number is required")
        customer = order_data.get("customer") or {}
        phone = normalize_phone(customer.get("phone"))
        if not phone:
            result.skipped.append("no_valid_phone")
            return result

        contact = await self.upsert_contact(
            session,
            phone,
            first_name=customer.get("first_name"),
            email=customer.get("email"),
            transactional_source="rootellect_checkout",
        )
        if customer.get("whatsapp_marketing_opt_in") is True and not contact.marketing_opt_in:
            self.set_marketing_opt_in(contact, "rootellect_checkout", now)
        order = await self._upsert_order(session, order_data, phone)
        meta = order.metadata_json or {}
        name = meta.get("first_name") or _first_name(contact.first_name)

        if event_type == "order.confirmed":
            order.status = "confirmed"
            is_cod = meta.get("payment_method") == "cod"
            kind = "cod_order_confirm" if is_cod else "order_confirmed"
            buttons = (
                [
                    {"index": 0, "sub_type": "quick_reply", "value": f"{COD_CONFIRM}:{number}"},
                    {"index": 1, "sub_type": "quick_reply", "value": f"{COD_CANCEL}:{number}"},
                ]
                if is_cod
                else [{"index": 0, "sub_type": "url", "value": meta.get("track_code") or number}]
            )
            await self._queue_and_record(
                session, result, key=f"{number}:{kind}", kind=kind, phone=phone, order_external_id=number,
                body_params=[name, number, _money(order.total_amount)], button_params=buttons, scheduled_for=now,
            )
        elif event_type == "shipment.updated":
            await self._handle_shipment(session, result, order, event.get("shipment") or {}, name, phone, now)
        elif event_type == "order.cancelled":
            order.status = "cancelled"
            cancelled = await self._cancel_pending(session, number)
            result.skipped.append(f"cancelled_{cancelled}_pending")
        else:
            raise EventValidationError(f"Unsupported event type: {event_type}")

        await self._dispatch_immediate(session, result, now)
        return result

    async def _queue_and_record(self, session: AsyncSession, result: EventResult, **kwargs) -> WhatsAppNotification | None:
        notification = await self.queue(session, **kwargs)
        if notification is None:
            result.skipped.append(f"duplicate:{kwargs['key']}")
        else:
            result.queued.append(kwargs["key"])
        return notification

    async def _handle_shipment(
        self,
        session: AsyncSession,
        result: EventResult,
        order: Order,
        shipment: dict,
        name: str,
        phone: str,
        now: datetime,
    ) -> None:
        status = str(shipment.get("status") or "").lower()
        kind = SHIPMENT_KINDS.get(status)
        number = order.external_order_id
        meta = order.metadata_json or {}
        if kind is None:
            result.skipped.append(f"ignored_status:{status or 'missing'}")
            return
        send_at = self.next_send_time(now)
        track_button = [{"index": 0, "sub_type": "url", "value": meta.get("track_code") or number}]

        if kind == "order_shipped":
            order.status = "shipped"
            courier = str(shipment.get("courier") or "").strip() or "our courier partner"
            awb = str(shipment.get("awb") or "").strip() or "available on your tracking page"
            await self._queue_and_record(
                session, result, key=f"{number}:order_shipped", kind=kind, phone=phone, order_external_id=number,
                body_params=[name, number, courier, awb], button_params=track_button, scheduled_for=send_at,
            )
        elif kind == "out_for_delivery":
            amount = (
                f"₹{_money(order.total_amount)} (Cash on Delivery)"
                if meta.get("payment_method") == "cod" and meta.get("cod_status") != "cancelled"
                else "₹0 (already paid)"
            )
            await self._queue_and_record(
                session, result, key=f"{number}:out_for_delivery", kind=kind, phone=phone, order_external_id=number,
                body_params=[name, number, amount], scheduled_for=send_at,
            )
        elif kind == "delivery_failed":
            day = now.astimezone(self.tz).strftime("%Y%m%d")
            await self._queue_and_record(
                session, result, key=f"{number}:delivery_failed:{day}", kind=kind, phone=phone, order_external_id=number,
                body_params=[name, number], scheduled_for=send_at,
            )
        elif kind == "order_delivered":
            order.status = "delivered"
            delivered_at = _parse_time(shipment.get("delivered_at")) or now
            order.metadata_json = {**meta, "delivered_at": delivered_at.isoformat()}
            # Anything still waiting from earlier stages is now stale.
            await self._cancel_pending(session, number, {"order_shipped", "out_for_delivery", "delivery_failed"})
            await self._queue_and_record(
                session, result, key=f"{number}:order_delivered", kind=kind, phone=phone, order_external_id=number,
                body_params=[name, number], scheduled_for=send_at,
            )
            await self._schedule_after_delivery(session, result, order, name, phone, delivered_at)

    async def _schedule_after_delivery(
        self, session: AsyncSession, result: EventResult, order: Order, name: str, phone: str, delivered_at: datetime
    ) -> None:
        number = order.external_order_id
        lines = [line for line in (order.line_items or []) if isinstance(line, dict)]
        label = _product_label(lines)
        meta = order.metadata_json or {}

        await self._queue_and_record(
            session, result, key=f"{number}:usage_guide", kind="usage_guide", phone=phone, order_external_id=number,
            body_params=[name, label], scheduled_for=self.at_local_time(delivered_at, 2, 10, 30),
        )
        if meta.get("review_token"):
            await self._queue_and_record(
                session, result, key=f"{number}:review_request", kind="review_request", phone=phone,
                order_external_id=number, body_params=[name, label],
                button_params=[{"index": 0, "sub_type": "url", "value": meta["review_token"]}],
                scheduled_for=self.at_local_time(delivered_at, 14, 11, 0),
            )

        supplied = [line for line in lines if line.get("slug") and int(line.get("supply_days") or 0) > 0]
        if supplied:
            first_out = min(supplied, key=lambda line: int(line["supply_days"]))
            days = max(int(first_out["supply_days"]) - 5, 7)
            await self._queue_and_record(
                session, result, key=f"{number}:reorder_reminder", kind="reorder_reminder", phone=phone,
                order_external_id=number, body_params=[name, _product_label([first_out])],
                button_params=[{"index": 0, "sub_type": "url", "value": first_out["slug"]}],
                scheduled_for=self.at_local_time(delivered_at, days, 11, 0),
            )

    async def _handle_abandoned(self, session: AsyncSession, checkout: dict, now: datetime, result: EventResult) -> None:
        cart_key = str(checkout.get("cart_key") or "").strip()
        customer = checkout.get("customer") or {}
        phone = normalize_phone(customer.get("phone"))
        if not cart_key or not phone:
            result.skipped.append("abandoned_missing_cart_or_phone")
            return
        contact = await self.upsert_contact(session, phone, first_name=customer.get("first_name"), email=customer.get("email"))
        items = [item for item in (checkout.get("items") or []) if isinstance(item, dict)]
        await self._queue_and_record(
            session, result, key=f"cart:{cart_key}", kind="checkout_reminder", phone=phone,
            body_params=[_first_name(contact.first_name), _product_label(items)],
            scheduled_for=self.next_send_time(now + timedelta(hours=1)),
            metadata={"cart_key": cart_key, "abandoned_at": now.isoformat()},
        )

    # ---------------------------------------------------------------- dispatch
    async def _dispatch_immediate(self, session: AsyncSession, result: EventResult, now: datetime) -> None:
        if not result.queued:
            return
        rows = (
            await session.execute(
                select(WhatsAppNotification).where(
                    WhatsAppNotification.idempotency_key.in_(result.queued),
                    WhatsAppNotification.scheduled_for <= now,
                )
            )
        ).scalars().all()
        if not rows:
            return
        provider = await get_whatsapp_provider(session)
        for row in rows:
            if await self._send(session, row, provider, now):
                result.sent.append(row.idempotency_key)

    async def dispatch_due(self, session: AsyncSession, limit: int = 50, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        stmt = (
            select(WhatsAppNotification)
            .where(WhatsAppNotification.status.in_(PENDING_STATUSES), WhatsAppNotification.scheduled_for <= now)
            .order_by(WhatsAppNotification.scheduled_for.asc())
            .limit(limit)
        )
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        rows = (await session.execute(stmt)).scalars().all()
        counts = {"due": len(rows), "sent": 0, "skipped": 0, "failed": 0, "deferred": 0}
        if not rows:
            return counts
        provider = await get_whatsapp_provider(session)
        for row in rows:
            ok = await self._send(session, row, provider, now)
            if ok:
                counts["sent"] += 1
            elif row.status in {"scheduled", "retrying"}:
                counts["deferred"] += 1
            elif row.status == "skipped":
                counts["skipped"] += 1
            else:
                counts["failed"] += 1
        return counts

    async def _skip_reason(
        self, session: AsyncSession, row: WhatsAppNotification, template: WhatsAppTemplate | None
    ) -> str | None:
        contact = await self.get_contact(session, row.phone)
        if contact is None:
            return "no_contact"
        if contact.opted_out_at is not None:
            return "opted_out"
        consent = template.consent if template else ("marketing" if row.category == "marketing" else "transactional")
        if consent == "marketing" and not contact.marketing_opt_in:
            return "no_marketing_opt_in"
        if consent == "transactional" and not contact.transactional_opt_in:
            return "no_transactional_opt_in"
        if row.kind == "checkout_reminder":
            abandoned_at = _aware(row.created_at) or datetime.now(UTC)
            purchased = await session.scalar(
                select(Order.id).where(Order.customer_phone == row.phone, Order.created_at >= abandoned_at).limit(1)
            )
            if purchased:
                return "purchased_after_abandon"
        if row.order_external_id and row.kind in {"usage_guide", "review_request", "reorder_reminder"}:
            order = await session.scalar(select(Order).where(Order.external_order_id == row.order_external_id))
            if order is not None and order.status in {"cancelled", "returned"}:
                return f"order_{order.status}"
        return None

    async def _send(self, session: AsyncSession, row: WhatsAppNotification, provider, now: datetime) -> bool:
        template = _template_for(row)
        reason = await self._skip_reason(session, row, template)
        if reason:
            row.status = "skipped"
            row.error = reason
            return False
        immediate = bool(template and template.immediate)
        if not immediate and self.in_quiet_hours(now):
            row.scheduled_for = self.next_send_time(now)
            return False

        row.attempts = (row.attempts or 0) + 1
        language = (row.metadata_json or {}).get("language") or self.settings.whatsapp_template_language
        sender = getattr(provider, "send_template", None)
        if sender is None:
            row.status = "failed"
            row.error = "provider_cannot_send_templates"
            return False
        response = await sender(row.phone, row.template_name, language, row.body_params or [], row.button_params or [])
        if response.ok:
            row.status = "sent"
            row.provider_message_id = response.provider_action_id or None
            row.sent_at = now
            row.error = None
            return True

        code = _error_code(response.response)
        row.error = (response.error or "send_failed")[:2000]
        if code == 131050:
            # The customer turned off marketing messages from us inside WhatsApp.
            contact = await self.get_contact(session, row.phone)
            if contact:
                contact.marketing_opt_in = False
        if code in PERMANENT_ERROR_CODES or row.attempts >= MAX_ATTEMPTS:
            row.status = "failed"
        else:
            row.status = "retrying"
            row.scheduled_for = now + timedelta(minutes=10 * row.attempts)
        logger.warning("whatsapp_template_send_failed", kind=row.kind, key=row.idempotency_key, code=code, attempts=row.attempts)
        return False

    # ----------------------------------------------------------------- inbound
    async def handle_inbound_webhook(self, session: AsyncSession, payload: dict, now: datetime | None = None) -> set[str]:
        """Apply delivery statuses, service-window tracking, STOP/START and COD replies.

        Returns WhatsApp message ids that were fully handled here, so the AI
        reply pipeline can skip them.
        """
        now = now or datetime.now(UTC)
        consumed: set[str] = set()
        replies: list[tuple[str, str]] = []
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for status in value.get("statuses") or []:
                    await self._apply_status(session, status)
                profile_names = {
                    str(c.get("wa_id")): ((c.get("profile") or {}).get("name"))
                    for c in value.get("contacts") or []
                    if c.get("wa_id")
                }
                for message in value.get("messages") or []:
                    phone = normalize_phone("+" + str(message.get("from") or "")) or str(message.get("from") or "")
                    if not phone:
                        continue
                    contact = await self.get_contact(session, phone)
                    if contact is None:
                        contact = await self.upsert_contact(session, phone, first_name=profile_names.get(phone))
                        contact.transactional_opt_in_source = contact.transactional_opt_in_source or "inbound_message"
                    contact.last_inbound_at = now
                    reply = await self._handle_customer_message(session, contact, message, now)
                    if reply:
                        consumed.add(str(message.get("id") or ""))
                        replies.append((phone, reply))

        if replies:
            provider = await get_whatsapp_provider(session)
            for phone, text in replies:
                # Free-form text is allowed: the customer messaged us seconds ago.
                await provider.send_whatsapp_text(phone, text)
        consumed.discard("")
        return consumed

    async def _apply_status(self, session: AsyncSession, status: dict) -> None:
        message_id = status.get("id")
        if not message_id:
            return
        row = await session.scalar(select(WhatsAppNotification).where(WhatsAppNotification.provider_message_id == message_id))
        if row is None:
            return
        when = _parse_time(status.get("timestamp")) or datetime.now(UTC)
        state = status.get("status")
        if state == "delivered":
            row.delivered_at = row.delivered_at or when
            if row.status == "sent":
                row.status = "delivered"
        elif state == "read":
            row.read_at = row.read_at or when
            row.delivered_at = row.delivered_at or when
            row.status = "read"
        elif state == "failed":
            row.status = "failed"
            errors = status.get("errors") or []
            row.error = str(errors[0] if errors else "delivery_failed")[:2000]

    async def _handle_customer_message(
        self, session: AsyncSession, contact: WhatsAppContact, message: dict, now: datetime
    ) -> str | None:
        message_type = message.get("type")
        payload = ""
        text = ""
        if message_type == "button":
            payload = str((message.get("button") or {}).get("payload") or "")
            text = str((message.get("button") or {}).get("text") or "")
        elif message_type == "interactive":
            reply = (message.get("interactive") or {}).get("button_reply") or {}
            payload, text = str(reply.get("id") or ""), str(reply.get("title") or "")
        elif message_type == "text":
            text = str((message.get("text") or {}).get("body") or "")

        if payload.startswith(f"{COD_CONFIRM}:") or payload.startswith(f"{COD_CANCEL}:"):
            action, _, number = payload.partition(":")
            return await self._apply_cod_response(session, contact, number, action == COD_CONFIRM, now)

        keyword = text.strip().lower().strip(".! ")
        if keyword in STOP_KEYWORDS:
            contact.marketing_opt_in = False
            contact.transactional_opt_in = False
            contact.opted_out_at = now
            await self._sync_lead_opt_in(session, contact.phone, False)
            return (
                "You've been unsubscribed from Rootellect WhatsApp updates. "
                "Reply START anytime to receive order updates and offers again."
            )
        if keyword in START_KEYWORDS:
            self.set_marketing_opt_in(contact, "whatsapp_keyword", now)
            await self._sync_lead_opt_in(session, contact.phone, True)
            return (
                "You're subscribed to Rootellect updates on WhatsApp: order updates, reorder reminders and occasional offers. "
                "Reply STOP anytime to opt out."
            )
        return None

    async def _apply_cod_response(
        self, session: AsyncSession, contact: WhatsAppContact, number: str, confirmed: bool, now: datetime
    ) -> str:
        order = await session.scalar(
            select(Order).where(Order.external_order_id == number, Order.source == "rootellect")
        )
        name = _first_name(contact.first_name)
        if order is None or (order.customer_phone and order.customer_phone != contact.phone):
            return "Thanks for your reply. Our team will check this order and get back to you here shortly."
        # Assign a new dict: in-place JSON mutation is not change-tracked.
        order.metadata_json = {
            **(order.metadata_json or {}),
            "cod_status": "confirmed" if confirmed else "cancelled",
            "cod_responded_at": now.isoformat(),
        }
        if confirmed:
            return f"Thank you, {name}! Your order {number} is confirmed. We'll share tracking details as soon as it ships."
        await self._cancel_pending(session, number)
        return (
            f"Noted, {name}. We've received your request to cancel order {number}. "
            "Our team will process it and confirm here shortly."
        )

    async def _sync_lead_opt_in(self, session: AsyncSession, phone: str, value: bool) -> None:
        leads = (
            await session.execute(select(Lead).where(Lead.phone.in_([phone, f"+{phone}", phone[2:]])))
        ).scalars().all()
        for lead in leads:
            lead.whatsapp_opt_in = value


def _template_for(row: WhatsAppNotification) -> WhatsAppTemplate | None:
    try:
        template = get_template(row.kind)
    except KeyError:
        return None
    return template if template.name == row.template_name else None


def _parse_time(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, int | float) or (isinstance(value, str) and value.isdigit()):
            return datetime.fromtimestamp(int(value), tz=UTC)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _error_code(response: dict | None) -> int | None:
    error = (response or {}).get("error") if isinstance(response, dict) else None
    if isinstance(error, dict):
        try:
            return int(error.get("code"))
        except (TypeError, ValueError):
            return None
    return None
