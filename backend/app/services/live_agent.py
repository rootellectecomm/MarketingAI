"""Live-agent handover for WhatsApp.

When a customer asks for a person, sends a catalog cart, or the bot cannot
answer safely, the conversation is handed to the Rootellect team:

1. The bot pauses for that customer (state lives on ``WhatsAppContact.metadata_json``,
   so no schema change is needed).
2. The customer is told a person is coming, with support hours when the team is offline.
3. The team gets a WhatsApp alert on their own phones (``LIVE_AGENT_TEAM_PHONES``).
4. The team replies from the dashboard inbox; the bot stays paused while they chat
   and resumes on its own after ``LIVE_AGENT_IDLE_HOURS`` without team activity,
   or when the team taps "Resume bot".
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.product_knowledge import ROOTELLECT_PRODUCT_CATALOG
from app.core.config import get_settings
from app.models.entities import Conversation, Message, WhatsAppContact

logger = structlog.get_logger(__name__)

STATE_KEY = "live_agent"

# Phrases that mean "let me talk to a person". Matched on word boundaries,
# lower-cased, in English and common Hinglish.
_HUMAN_PATTERNS = (
    r"\b(talk|speak|chat|connect)\s+(to|with)\s+(a\s+)?(human|person|someone|agent|team|executive|expert|representative)\b",
    r"\b(real|live)\s+(person|human|agent)\b",
    r"\bhuman\b",
    r"\b(customer\s+)?(care|support)\s+(team|executive|number)\b",
    r"\bcustomer\s+care\b",
    r"\bcall\s+me\b",
    r"\b(connect|transfer)\s+me\b",
    r"\bcall\s+back\b",
    r"\bagent\b",
    r"\bkisi\s+se\s+baat\b",
    r"\bbaat\s+karni\b",
    r"\bbaat\s+karwa\b",
)
_HUMAN_RE = re.compile("|".join(_HUMAN_PATTERNS), re.IGNORECASE)
_HELP_COMMANDS = {"/help", "help", "/agent", "/team"}

# Catalog content IDs (Commerce Manager) -> product.
_RETAILER_ID_PRODUCTS = {
    "rtl-mind-30c": "Mind Calm",
    "rtl-women-60c": "Women Balance",
    "rtl-pcos-60c": "PCOS Support",
    "rtl-peri-60c": "Perimenopause Support",
}
_PRODUCT_LABELS = {
    "Mind Calm": "Mind Calm",
    "Women Balance": "Women Balance",
    "PCOS Support": "PCOS/PCOD Support",
    "Perimenopause Support": "Perimenopause Support",
}
_WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def wants_human(text: str) -> bool:
    cleaned = (text or "").strip().lower()
    if cleaned in _HELP_COMMANDS:
        return True
    return bool(_HUMAN_RE.search(cleaned))


def team_phones(settings=None) -> set[str]:
    raw = (settings or get_settings()).live_agent_team_phones or ""
    phones = set()
    for part in re.split(r"[,;\n]+", raw):
        digits = re.sub(r"\D", "", part)
        if len(digits) == 10:
            digits = "91" + digits
        if digits:
            phones.add(digits)
    return phones


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return _aware(datetime.fromisoformat(value))
    except ValueError:
        return None


class LiveAgentService:
    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()

    # ----- state -------------------------------------------------------------
    def state(self, contact: WhatsAppContact | None) -> dict:
        if contact is None:
            return {}
        return dict((contact.metadata_json or {}).get(STATE_KEY) or {})

    def _save(self, contact: WhatsAppContact, state: dict) -> None:
        metadata = dict(contact.metadata_json or {})
        metadata[STATE_KEY] = state
        contact.metadata_json = metadata  # reassign so SQLAlchemy sees the JSON change

    def is_active(self, contact: WhatsAppContact | None, now: datetime | None = None) -> bool:
        state = self.state(contact)
        if not state.get("active"):
            return False
        now = now or datetime.now(UTC)
        last = _parse(state.get("last_team_reply_at")) or _parse(state.get("started_at"))
        if last and now - last > timedelta(hours=self.settings.live_agent_idle_hours):
            return False
        return True

    def public_state(self, contact: WhatsAppContact | None, now: datetime | None = None) -> dict:
        state = self.state(contact)
        return {
            "active": self.is_active(contact, now),
            "reason": state.get("reason"),
            "started_at": state.get("started_at"),
            "last_team_reply_at": state.get("last_team_reply_at"),
            "agent": state.get("agent"),
        }

    # ----- support hours -----------------------------------------------------
    def _tz(self) -> ZoneInfo:
        return ZoneInfo(self.settings.whatsapp_send_timezone)

    def _working_days(self) -> set[int]:
        days = set()
        for part in (self.settings.live_agent_days or "").split(","):
            part = part.strip()
            if part.isdigit():
                days.add(int(part))
        return days or {0, 1, 2, 3, 4, 5}

    def team_online(self, now: datetime | None = None) -> bool:
        local = (now or datetime.now(UTC)).astimezone(self._tz())
        return (
            local.weekday() in self._working_days()
            and self.settings.live_agent_hours_start <= local.hour < self.settings.live_agent_hours_end
        )

    def next_opening(self, now: datetime | None = None) -> datetime:
        local = (now or datetime.now(UTC)).astimezone(self._tz())
        candidate = local.replace(hour=self.settings.live_agent_hours_start, minute=0, second=0, microsecond=0)
        if candidate <= local:
            candidate += timedelta(days=1)
        for _ in range(8):
            if candidate.weekday() in self._working_days():
                return candidate
            candidate += timedelta(days=1)
        return candidate

    def _hours_label(self) -> str:
        def fmt(hour: int) -> str:
            suffix = "AM" if hour < 12 else "PM"
            return f"{(hour % 12) or 12} {suffix}"

        days = sorted(self._working_days())
        if days == [0, 1, 2, 3, 4, 5]:
            day_label = "Monday to Saturday"
        elif days == list(range(7)):
            day_label = "every day"
        else:
            day_label = ", ".join(_WEEKDAY_NAMES[d] for d in days)
        return f"{fmt(self.settings.live_agent_hours_start)} – {fmt(self.settings.live_agent_hours_end)}, {day_label}"

    def customer_notice(self, now: datetime | None = None) -> str:
        now = now or datetime.now(UTC)
        if self.team_online(now):
            return (
                "I'm connecting you to the Rootellect team. A team member will reply right here shortly, "
                "so please keep this chat open. 🌿"
            )
        opening = self.next_opening(now)
        local_now = now.astimezone(self._tz())
        if opening.date() == local_now.date():
            when = f"today after {opening.strftime('%-I %p')}"
        elif opening.date() == (local_now + timedelta(days=1)).date():
            when = f"tomorrow after {opening.strftime('%-I %p')}"
        else:
            when = f"on {_WEEKDAY_NAMES[opening.weekday()]} after {opening.strftime('%-I %p')}"
        return (
            f"Thanks for reaching out! Our team is available {self._hours_label()}. "
            f"We've shared your message with them and a team member will reply right here {when}. 🌿"
        )

    # ----- catalog carts -----------------------------------------------------
    @staticmethod
    def cart_lines(message: dict) -> list[dict]:
        order = message.get("order") or {}
        lines = []
        for item in order.get("product_items") or []:
            retailer_id = str(item.get("product_retailer_id") or "")
            product_key = _RETAILER_ID_PRODUCTS.get(retailer_id.lower())
            product = ROOTELLECT_PRODUCT_CATALOG.get(product_key) if product_key else None
            try:
                quantity = int(item.get("quantity") or 1)
            except (TypeError, ValueError):
                quantity = 1
            try:
                price = float(item.get("item_price") or 0)
            except (TypeError, ValueError):
                price = 0.0
            lines.append(
                {
                    "retailer_id": retailer_id,
                    "name": _PRODUCT_LABELS.get(product_key or "", retailer_id or "Item"),
                    "url": product.url if product else None,
                    "quantity": quantity,
                    "price": price,
                }
            )
        return lines

    def cart_summary(self, lines: list[dict]) -> str:
        if not lines:
            return "your cart"
        return ", ".join(f"{line['quantity']} × {line['name']}" for line in lines)

    def cart_reply(self, lines: list[dict], now: datetime | None = None) -> str:
        total = sum(line["quantity"] * line["price"] for line in lines)
        items = "\n".join(
            f"• {line['quantity']} × {line['name']}" + (f" – ₹{line['price'] * line['quantity']:,.0f}" if line["price"] else "")
            for line in lines
        ) or "• Your selected items"
        links = [line["url"] for line in lines if line.get("url")]
        link_text = ""
        if len(links) == 1:
            link_text = f"\n\nTo order now, you can check out here: {links[0]}"
        elif links:
            link_text = f"\n\nTo order now, you can check out on our website: {self.settings.rootellect_site_url}"
        total_text = f"\nEstimated total: ₹{total:,.0f}" if total else ""
        online = self.team_online(now)
        team_text = (
            "Our team will also message you here shortly to help you complete your order."
            if online
            else f"Our team ({self._hours_label()}) will message you here to help you complete your order."
        )
        return f"Thank you! We've received your cart:\n{items}{total_text}{link_text}\n\n{team_text}"

    # ----- handover ----------------------------------------------------------
    async def start(
        self,
        session: AsyncSession,
        provider,
        contact: WhatsAppContact,
        conversation: Conversation | None,
        *,
        reason: str,
        customer_text: str,
        customer_reply: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Pause the bot, tell the customer, alert the team."""
        now = now or datetime.now(UTC)
        already_active = self.is_active(contact, now)
        state = self.state(contact) if already_active else {}
        state.update(
            {
                "active": True,
                "reason": reason if not already_active else state.get("reason", reason),
                "started_at": state.get("started_at") or now.isoformat(),
                "last_customer_at": now.isoformat(),
            }
        )
        self._save(contact, state)

        reply = customer_reply if customer_reply is not None else self.customer_notice(now)
        if reply:
            result = await provider.send_whatsapp_text(contact.phone, reply)
            if result.ok and conversation is not None:
                session.add(
                    Message(
                        conversation_id=conversation.id,
                        direction="outbound",
                        body=reply,
                        channel="whatsapp_message",
                        metadata_json={"automated": True, "live_agent": "handover_notice"},
                    )
                )
            elif not result.ok:
                logger.warning("live_agent_customer_notice_failed", phone=contact.phone, error=result.error)

        await self.alert_team(session, provider, contact, reason=reason, snippet=customer_text, now=now)

    async def note_customer_message(
        self,
        session: AsyncSession,
        provider,
        contact: WhatsAppContact,
        text: str,
        now: datetime | None = None,
    ) -> None:
        """Customer wrote again while a person owns the chat: stay quiet, nudge the team if they have not replied."""
        now = now or datetime.now(UTC)
        state = self.state(contact)
        state["last_customer_at"] = now.isoformat()
        self._save(contact, state)
        last_alert = _parse(state.get("last_alert_at"))
        last_team = _parse(state.get("last_team_reply_at"))
        waiting = last_team is None or last_team < (_parse(state.get("last_customer_at")) or now)
        if waiting and (last_alert is None or now - last_alert >= timedelta(minutes=self.settings.live_agent_realert_minutes)):
            await self.alert_team(session, provider, contact, reason="customer_still_waiting", snippet=text, now=now)

    async def alert_team(
        self,
        session: AsyncSession,
        provider,
        contact: WhatsAppContact,
        *,
        reason: str,
        snippet: str,
        now: datetime | None = None,
    ) -> int:
        now = now or datetime.now(UTC)
        phones = team_phones(self.settings)
        state = self.state(contact)
        state["last_alert_at"] = now.isoformat()
        self._save(contact, state)
        if not phones:
            logger.warning("live_agent_no_team_phones", customer=contact.phone, reason=reason)
            return 0
        name = contact.first_name or "Customer"
        reason_label = REASON_LABELS.get(reason, reason.replace("_", " "))
        short = re.sub(r"\s+", " ", snippet or "").strip()[:200] or "(no text)"
        inbox = f"{self.settings.frontend_url.rstrip('/')}/conversations" if self.settings.frontend_url else ""
        text = (
            f"🔔 Rootellect customer needs a person\n"
            f"Customer: {name} (+{contact.phone})\n"
            f"Reason: {reason_label}\n"
            f"Message: {short}"
            + (f"\n\nReply from the dashboard: {inbox}" if inbox else "")
        )
        sent = 0
        for phone in phones:
            if phone == contact.phone:
                continue
            result = await provider.send_whatsapp_text(phone, text)
            if not result.ok and self.settings.live_agent_alert_template:
                # Outside the team member's 24h window WhatsApp only allows templates.
                result = await provider.send_whatsapp_template(
                    phone,
                    self.settings.live_agent_alert_template,
                    [name[:60], f"+{contact.phone}", reason_label[:60], short[:200]],
                )
            if result.ok:
                sent += 1
            else:
                logger.warning("live_agent_team_alert_failed", team_phone=phone, error=result.error)
        logger.info("live_agent_team_alerted", customer=contact.phone, reason=reason, sent=sent)
        return sent

    def record_team_reply(self, contact: WhatsAppContact, agent: str | None, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        state = self.state(contact) if self.is_active(contact, now) else {"reason": "team_started", "started_at": now.isoformat()}
        state.update({"active": True, "last_team_reply_at": now.isoformat(), "agent": agent})
        self._save(contact, state)

    def resume_bot(self, contact: WhatsAppContact, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        state = self.state(contact)
        state.update({"active": False, "ended_at": now.isoformat()})
        self._save(contact, state)

    def pause_bot(self, contact: WhatsAppContact, agent: str | None, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        state = {"active": True, "reason": "paused_by_team", "started_at": now.isoformat(),
                 "last_team_reply_at": now.isoformat(), "agent": agent}
        self._save(contact, state)


REASON_LABELS = {
    "asked_for_person": "Asked to talk to a person",
    "catalog_cart": "Sent a cart from the WhatsApp catalog",
    "bot_could_not_answer": "Bot could not answer safely",
    "medical_question": "Health or medicine question",
    "customer_still_waiting": "Customer is still waiting for a reply",
}
