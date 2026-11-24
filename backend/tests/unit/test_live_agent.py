from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models  # noqa: F401
from app.core.config import Settings
from app.database.base import Base
from app.models.entities import Conversation, Message, WhatsAppContact, WhatsAppNotification
from app.models.enums import EventType, ProviderType
from app.schemas.social import NormalizedEvent
from app.services import event_processor as ep
from app.services.live_agent import LiveAgentService, team_phones, wants_human
from app.services.providers.base import ProviderActionResult
from app.services.whatsapp_orders import WhatsAppOrderService

# Tue 24 Nov 2026, 12:00 IST (team online) / 21:00 IST (offline) / Sun 29 Nov 12:00 IST (offline)
ONLINE = datetime(2026, 11, 24, 6, 30, tzinfo=UTC)
EVENING = datetime(2026, 11, 24, 15, 30, tzinfo=UTC)
SUNDAY = datetime(2026, 11, 29, 6, 30, tzinfo=UTC)
SATURDAY_NIGHT = datetime(2026, 11, 28, 15, 30, tzinfo=UTC)
CUSTOMER = "917503331986"
TEAM = "919800000001"


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, live_agent_team_phones=TEAM, **overrides)


class FakeProvider:
    def __init__(self) -> None:
        self.texts: list[tuple[str, str]] = []
        self.templates: list[tuple[str, str, list]] = []
        self.fail_text_to: set[str] = set()

    async def send_whatsapp_text(self, phone, message):
        self.texts.append((phone, message))
        if phone in self.fail_text_to:
            return ProviderActionResult(ok=False, error="(#131047) Re-engagement message", response={"error": {"code": 131047}})
        return ProviderActionResult(ok=True, provider_action_id="wamid.text")

    async def send_whatsapp_template(self, phone, template_name, variables=None):
        self.templates.append((phone, template_name, variables or []))
        return ProviderActionResult(ok=True, provider_action_id="wamid.tpl")


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


@pytest.mark.parametrize(
    "text",
    ["I want to talk to a person", "connect me with your team", "Customer care number?", "/help", "call me please",
     "kisi se baat karni hai", "real person please"],
)
def test_detects_requests_for_a_person(text):
    assert wants_human(text)


@pytest.mark.parametrize("text", ["which product helps with stress", "Hello", "price of mind calm", "is it safe"])
def test_normal_questions_stay_with_the_bot(text):
    assert not wants_human(text)


def test_team_phones_accepts_ten_digit_numbers():
    assert team_phones(Settings(_env_file=None, live_agent_team_phones="98000 00001, +91 98000-00002")) == {
        "919800000001",
        "919800000002",
    }


def test_customer_notice_matches_support_hours():
    agent = LiveAgentService(make_settings())
    assert agent.team_online(ONLINE)
    assert "reply right here shortly" in agent.customer_notice(ONLINE)
    evening = agent.customer_notice(EVENING)
    assert "10 AM – 7 PM, Monday to Saturday" in evening and "tomorrow after 10 AM" in evening
    assert "tomorrow after 10 AM" in agent.customer_notice(SUNDAY)
    assert "on Monday after 10 AM" in agent.customer_notice(SATURDAY_NIGHT)


def test_cart_reply_lists_items_and_checkout_link():
    agent = LiveAgentService(make_settings())
    lines = agent.cart_lines(
        {"type": "order", "order": {"product_items": [
            {"product_retailer_id": "RTL-PCOS-60C", "quantity": 1, "item_price": 799, "currency": "INR"}
        ]}}
    )
    reply = agent.cart_reply(lines, ONLINE)
    assert "1 × PCOS/PCOD Support – ₹799" in reply
    assert "https://www.rootellect.com/products/pcos-pcod-support" in reply
    assert "Estimated total: ₹799" in reply


async def test_handover_pauses_bot_alerts_team_and_expires(session):
    agent = LiveAgentService(make_settings())
    provider = FakeProvider()
    contact = WhatsAppContact(phone=CUSTOMER, first_name="Partik")
    session.add(contact)
    await session.flush()

    await agent.start(session, provider, contact, None, reason="asked_for_person", customer_text="talk to a person", now=ONLINE)
    assert agent.is_active(contact, ONLINE)
    assert provider.texts[0][0] == CUSTOMER and "connecting you" in provider.texts[0][1]
    assert provider.texts[1][0] == TEAM and "Partik (+917503331986)" in provider.texts[1][1]

    # Team member outside their 24h window: falls back to the approved alert template.
    provider.fail_text_to.add(TEAM)
    await agent.alert_team(session, provider, contact, reason="catalog_cart", snippet="Cart: 1 × Mind Calm", now=ONLINE)
    assert provider.templates[-1][1] == "rootellect_team_alert_v1"

    agent.record_team_reply(contact, "Mona", ONLINE + timedelta(minutes=5))
    assert agent.is_active(contact, ONLINE + timedelta(hours=23))
    assert not agent.is_active(contact, ONLINE + timedelta(hours=25))

    agent.pause_bot(contact, "Mona", ONLINE)
    agent.resume_bot(contact, ONLINE)
    assert not agent.is_active(contact, ONLINE)


@pytest.fixture
def processor(monkeypatch):
    provider = FakeProvider()

    async def factory(_session=None):
        return provider

    monkeypatch.setattr(ep, "get_whatsapp_provider", factory)
    proc = ep.EventProcessor()
    proc.live_agent = LiveAgentService(make_settings())
    return proc, provider


def wa_event(message: dict, phone: str = CUSTOMER) -> NormalizedEvent:
    return NormalizedEvent(
        provider=ProviderType.whatsapp_cloud,
        event_type=EventType.whatsapp_message,
        provider_event_id=message["id"],
        actor_id=phone,
        actor_username=phone,
        text=(message.get("text") or {}).get("body") or "",
        provider_message_id=message["id"],
        payload=message,
    )


async def _conversation(session, phone=CUSTOMER) -> Conversation:
    conversation = Conversation(external_user_id=phone, username=phone, channel="whatsapp_message")
    session.add(conversation)
    await session.flush()
    return conversation


async def test_catalog_cart_gets_a_reply_and_team_alert(session, processor):
    proc, provider = processor
    conversation = await _conversation(session)
    event = ep.SocialEvent(provider=ProviderType.whatsapp_cloud, event_type=EventType.whatsapp_message,
                           provider_event_id="wamid.cart", payload={})
    message = {"id": "wamid.cart", "type": "order", "order": {"product_items": [
        {"product_retailer_id": "RTL-MIND-30C", "quantity": 2, "item_price": 799}]}}
    handled = await proc._route_live_agent(session, event, wa_event(message), conversation, "")
    assert handled
    assert "2 × Mind Calm – ₹1,598" in provider.texts[0][1]
    assert provider.texts[1][0] == TEAM and "Sent a cart" in provider.texts[1][1]
    stored = (await session.scalars(select(Message))).all()
    assert any(m.body == "[Cart] 2 × Mind Calm" for m in stored)


async def test_messages_while_team_owns_chat_get_no_bot_reply(session, processor):
    proc, provider = processor
    conversation = await _conversation(session)
    event = ep.SocialEvent(provider=ProviderType.whatsapp_cloud, event_type=EventType.whatsapp_message,
                           provider_event_id="wamid.1", payload={})
    msg = {"id": "wamid.1", "type": "text", "text": {"body": "I want to talk to a person"}}
    assert await proc._route_live_agent(session, event, wa_event(msg), conversation, "I want to talk to a person")
    sent_before = len(provider.texts)
    msg2 = {"id": "wamid.2", "type": "text", "text": {"body": "hello?"}}
    assert await proc._route_live_agent(session, event, wa_event(msg2), conversation, "hello?")
    # No customer-facing reply while a person owns the chat (team nudge is rate-limited to once an hour).
    assert all(phone != CUSTOMER for phone, _ in provider.texts[sent_before:])


async def test_regular_question_goes_to_the_bot(session, processor):
    proc, _ = processor
    conversation = await _conversation(session)
    event = ep.SocialEvent(provider=ProviderType.whatsapp_cloud, event_type=EventType.whatsapp_message,
                           provider_event_id="wamid.3", payload={})
    msg = {"id": "wamid.3", "type": "text", "text": {"body": "which product helps with stress"}}
    assert not await proc._route_live_agent(session, event, wa_event(msg), conversation, "which product helps with stress")


async def test_team_member_messages_are_never_answered_by_the_bot(session, processor):
    proc, provider = processor
    conversation = await _conversation(session, TEAM)
    event = ep.SocialEvent(provider=ProviderType.whatsapp_cloud, event_type=EventType.whatsapp_message,
                           provider_event_id="wamid.4", payload={})
    msg = {"id": "wamid.4", "type": "text", "text": {"body": "hi"}}
    assert await proc._route_live_agent(session, event, wa_event(msg, TEAM), conversation, "hi")
    assert provider.texts == []


async def test_test_orders_and_late_reminders_are_not_sent(session):
    settings = Settings(_env_file=None)
    service = WhatsAppOrderService(settings)
    contact = WhatsAppContact(phone=CUSTOMER, marketing_opt_in=True)
    session.add(contact)
    test_reorder = WhatsAppNotification(
        idempotency_key="reorder:TEST-37278", phone=CUSTOMER, kind="reorder_reminder",
        template_name="rootellect_reorder_reminder_v2", category="marketing", order_external_id="TEST-37278",
        scheduled_for=ONLINE, status="scheduled",
    )
    late_cart = WhatsAppNotification(
        idempotency_key="checkout:abc", phone=CUSTOMER, kind="checkout_reminder",
        template_name="rootellect_checkout_reminder_v2", category="marketing",
        scheduled_for=ONLINE - timedelta(hours=2), status="scheduled",
    )
    session.add_all([test_reorder, late_cart])
    await session.flush()
    counts = await service.dispatch_due(session, now=ONLINE + timedelta(minutes=1))
    assert counts["sent"] == 0
    assert (test_reorder.status, test_reorder.error) == ("skipped", "test_order")
    assert (late_cart.status, late_cart.error) == ("skipped", "stale_too_late")
