from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models  # noqa: F401
from app.core.config import Settings
from app.core.public_paths import is_public_webhook_path
from app.database.base import Base
from app.models.entities import Order, WhatsAppContact, WhatsAppNotification
from app.services import whatsapp_orders
from app.services.providers.base import ProviderActionResult
from app.services.whatsapp_orders import WhatsAppOrderService, normalize_phone
from app.services.whatsapp_templates import TEMPLATES, meta_template_payload
from app.webhooks.rootellect import compute_signature, verify_rootellect_signature

# 2026-11-02 11:00 IST, inside the send window
DAYTIME = datetime(2026, 11, 2, 5, 30, tzinfo=UTC)
# 2026-11-02 23:30 IST, quiet hours
NIGHT = datetime(2026, 11, 2, 18, 0, tzinfo=UTC)


class FakeProvider:
    def __init__(self) -> None:
        self.templates: list[dict] = []
        self.texts: list[tuple[str, str]] = []
        self.next_results: list[ProviderActionResult] = []

    async def send_template(self, phone, template_name, language, body_params=None, button_params=None):
        self.templates.append(
            {"phone": phone, "name": template_name, "language": language, "body": body_params, "buttons": button_params}
        )
        if self.next_results:
            return self.next_results.pop(0)
        return ProviderActionResult(ok=True, provider_action_id=f"wamid.{len(self.templates)}")

    async def send_whatsapp_text(self, phone, message):
        self.texts.append((phone, message))
        return ProviderActionResult(ok=True, provider_action_id="wamid.text")


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


@pytest.fixture
def provider(monkeypatch):
    fake = FakeProvider()

    async def factory(_session=None):
        return fake

    monkeypatch.setattr(whatsapp_orders, "get_whatsapp_provider", factory)
    return fake


@pytest.fixture
def service():
    return WhatsAppOrderService(Settings(_env_file=None))


def order_event(event_type="order.confirmed", *, payment="prepaid", number="RT-1001", **extra):
    return {
        "type": event_type,
        "event_id": f"{event_type}:{number}",
        "order": {
            "order_number": number,
            "track_code": number,
            "total": 1299,
            "payment_method": payment,
            "review_token": "tok123",
            "customer": {"first_name": "Ananya Rao", "phone": "+91 98765 43210", "email": "a@example.com"},
            "lines": [
                {"title": "Mind Calm", "quantity": 2, "slug": "mind-calm", "supply_days": 60},
                {"title": "Women Balance", "quantity": 1, "slug": "women-balance", "supply_days": 30},
            ],
        },
        **extra,
    }


def test_normalize_phone():
    assert normalize_phone("+91 98765 43210") == "919876543210"
    assert normalize_phone("09876543210") == "919876543210"
    assert normalize_phone("9876543210") == "919876543210"
    assert normalize_phone("919876543210") == "919876543210"
    assert normalize_phone("+1 415 555 0100") == "14155550100"
    assert normalize_phone("12345") is None
    assert normalize_phone(None) is None


def test_templates_follow_meta_body_rules():
    for template in TEMPLATES.values():
        body = template.body.strip()
        assert not body.startswith("{{") and not body.endswith("}}"), template.name
        assert body.count("{{") == len(template.body_examples), template.name
        payload = meta_template_payload(template, "en")
        assert payload["category"] in {"UTILITY", "MARKETING"}
        for word in ("cure", "treat", "fix ", "reverse"):
            assert word not in body.lower(), (template.name, word)


async def test_prepaid_order_sends_confirmation_once(session, provider, service):
    result = await service.handle_event(session, order_event(), now=DAYTIME)
    assert result.sent == ["RT-1001:order_confirmed"]
    sent = provider.templates[0]
    assert sent["name"] == "rootellect_order_confirmed_v1"
    assert sent["phone"] == "919876543210"
    assert sent["body"] == ["Ananya", "RT-1001", "1,299"]
    assert sent["buttons"] == [{"index": 0, "sub_type": "url", "value": "RT-1001"}]

    again = await service.handle_event(session, order_event(), now=DAYTIME)
    assert again.sent == [] and again.skipped == ["duplicate:RT-1001:order_confirmed"]
    assert len(provider.templates) == 1


async def test_order_confirmation_is_sent_even_at_night(session, provider, service):
    result = await service.handle_event(session, order_event(), now=NIGHT)
    assert result.sent == ["RT-1001:order_confirmed"]


async def test_cod_order_asks_for_confirmation_with_buttons(session, provider, service):
    await service.handle_event(session, order_event(payment="cod"), now=DAYTIME)
    sent = provider.templates[0]
    assert sent["name"] == "rootellect_cod_order_confirm_v1"
    assert sent["buttons"] == [
        {"index": 0, "sub_type": "quick_reply", "value": "COD_CONFIRM:RT-1001"},
        {"index": 1, "sub_type": "quick_reply", "value": "COD_CANCEL:RT-1001"},
    ]


async def test_shipping_update_at_night_waits_for_morning(session, provider, service):
    await service.handle_event(session, order_event(), now=DAYTIME)
    shipped = order_event("shipment.updated", shipment={"status": "shipped", "courier": "Delhivery", "awb": "AWB1"})
    result = await service.handle_event(session, shipped, now=NIGHT)
    assert result.queued == ["RT-1001:order_shipped"] and result.sent == []

    row = await session.scalar(select(WhatsAppNotification).where(WhatsAppNotification.kind == "order_shipped"))
    assert row.scheduled_for.replace(tzinfo=UTC) == datetime(2026, 11, 3, 3, 30, tzinfo=UTC)  # 09:00 IST

    counts = await service.dispatch_due(session, now=datetime(2026, 11, 3, 3, 35, tzinfo=UTC))
    assert counts["sent"] == 1
    assert provider.templates[-1]["body"] == ["Ananya", "RT-1001", "Delhivery", "AWB1"]


async def test_out_for_delivery_shows_cod_amount(session, provider, service):
    await service.handle_event(session, order_event(payment="cod"), now=DAYTIME)
    ofd = order_event("shipment.updated", payment="cod", shipment={"status": "out_for_delivery"})
    await service.handle_event(session, ofd, now=DAYTIME)
    assert provider.templates[-1]["body"][2] == "₹1,299 (Cash on Delivery)"


async def test_delivery_schedules_follow_ups_and_respects_marketing_consent(session, provider, service):
    await service.handle_event(session, order_event(), now=DAYTIME)
    delivered = order_event("shipment.updated", shipment={"status": "delivered"})
    result = await service.handle_event(session, delivered, now=DAYTIME)
    assert set(result.queued) == {
        "RT-1001:order_delivered",
        "RT-1001:usage_guide",
        "RT-1001:review_request",
        "RT-1001:reorder_reminder",
    }
    assert result.sent == ["RT-1001:order_delivered"]

    rows = {r.kind: r for r in (await session.execute(select(WhatsAppNotification))).scalars()}
    # Reorder is timed on the product that runs out first (Women Balance, 30 days) minus 5 days.
    assert rows["reorder_reminder"].body_params == ["Ananya", "Rootellect Women Balance"]
    assert rows["reorder_reminder"].button_params == [{"index": 0, "sub_type": "url", "value": "women-balance"}]
    assert rows["usage_guide"].body_params == ["Ananya", "Mind Calm and Women Balance"]

    later = DAYTIME + timedelta(days=40)
    await service.dispatch_due(session, now=later)
    rows = {r.kind: r for r in (await session.execute(select(WhatsAppNotification))).scalars()}
    assert (rows["usage_guide"].status, rows["usage_guide"].error) == ("skipped", "no_marketing_opt_in")
    assert rows["review_request"].status == "sent"
    assert rows["reorder_reminder"].status == "skipped"
    assert rows["reorder_reminder"].error == "no_marketing_opt_in"


async def test_reorder_sent_when_customer_opted_in(session, provider, service):
    await service.handle_event(session, order_event(), now=DAYTIME)
    contact = await session.scalar(select(WhatsAppContact))
    service.set_marketing_opt_in(contact, "test")
    await service.handle_event(session, order_event("shipment.updated", shipment={"status": "delivered"}), now=DAYTIME)
    await service.dispatch_due(session, now=DAYTIME + timedelta(days=40))
    row = await session.scalar(select(WhatsAppNotification).where(WhatsAppNotification.kind == "reorder_reminder"))
    assert row.status == "sent"


def inbound(message: dict, phone="919876543210"):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": phone, "profile": {"name": "Ananya"}}],
                            "messages": [{"from": phone, "id": message.pop("id", "wamid.in1"), **message}],
                        }
                    }
                ]
            }
        ]
    }


async def test_stop_opts_out_and_blocks_future_sends(session, provider, service):
    await service.handle_event(session, order_event(), now=DAYTIME)
    await service.handle_event(session, order_event("shipment.updated", shipment={"status": "delivered"}), now=DAYTIME)

    consumed = await service.handle_inbound_webhook(session, inbound({"type": "text", "text": {"body": "STOP"}}), now=DAYTIME)
    assert consumed == {"wamid.in1"}
    assert "unsubscribed" in provider.texts[-1][1]
    contact = await session.scalar(select(WhatsAppContact))
    assert contact.opted_out_at is not None and not contact.transactional_opt_in

    await service.dispatch_due(session, now=DAYTIME + timedelta(days=40))
    statuses = {r.kind: (r.status, r.error) for r in (await session.execute(select(WhatsAppNotification))).scalars()}
    assert statuses["usage_guide"] == ("skipped", "opted_out")

    start = inbound({"type": "text", "text": {"body": "start"}, "id": "wamid.in2"})
    await service.handle_inbound_webhook(session, start, now=DAYTIME)
    assert contact.marketing_opt_in and contact.opted_out_at is None


async def test_ordinary_messages_reach_the_ai_and_open_the_window(session, provider, service):
    consumed = await service.handle_inbound_webhook(
        session, inbound({"type": "text", "text": {"body": "Is Mind Calm safe with coffee?"}}), now=DAYTIME
    )
    assert consumed == set()
    contact = await session.scalar(select(WhatsAppContact))
    assert contact.last_inbound_at is not None


async def test_cod_cancel_button_records_response(session, provider, service):
    await service.handle_event(session, order_event(payment="cod"), now=DAYTIME)
    tap = inbound({"type": "button", "button": {"payload": "COD_CANCEL:RT-1001", "text": "Cancel order"}})
    consumed = await service.handle_inbound_webhook(session, tap, now=DAYTIME)
    assert consumed == {"wamid.in1"}
    order = await session.scalar(select(Order))
    assert order.metadata_json["cod_status"] == "cancelled"
    assert "cancel order RT-1001" in provider.texts[-1][1]


async def test_cod_button_from_another_number_does_not_change_order(session, provider, service):
    await service.handle_event(session, order_event(payment="cod"), now=DAYTIME)
    tap = inbound({"type": "button", "button": {"payload": "COD_CANCEL:RT-1001"}}, phone="919999999999")
    await service.handle_inbound_webhook(session, tap, now=DAYTIME)
    order = await session.scalar(select(Order))
    assert "cod_status" not in order.metadata_json


async def test_delivery_status_webhook_updates_notification(session, provider, service):
    await service.handle_event(session, order_event(), now=DAYTIME)
    status = {"id": "wamid.1", "status": "read", "timestamp": "1793600000"}
    payload = {"entry": [{"changes": [{"value": {"statuses": [status]}}]}]}
    await service.handle_inbound_webhook(session, payload, now=DAYTIME)
    row = await session.scalar(select(WhatsAppNotification))
    assert row.status == "read" and row.read_at is not None


async def test_failed_send_retries_then_gives_up(session, provider, service):
    provider.next_results = [ProviderActionResult(ok=False, error="timeout", response={})] * 3
    await service.handle_event(session, order_event(), now=DAYTIME)
    row = await session.scalar(select(WhatsAppNotification))
    assert row.status == "retrying" and row.attempts == 1
    await service.dispatch_due(session, now=DAYTIME + timedelta(minutes=11))
    await service.dispatch_due(session, now=DAYTIME + timedelta(minutes=40))
    assert row.status == "failed" and row.attempts == 3


async def test_permanent_meta_error_fails_immediately(session, provider, service):
    provider.next_results = [ProviderActionResult(ok=False, error="bad template", response={"error": {"code": 132001}})]
    await service.handle_event(session, order_event(), now=DAYTIME)
    row = await session.scalar(select(WhatsAppNotification))
    assert row.status == "failed" and row.attempts == 1


async def test_abandoned_checkout_needs_consent_and_skips_buyers(session, provider, service):
    checkout = {
        "type": "checkout.abandoned",
        "checkout": {
            "cart_key": "c1",
            "customer": {"phone": "9876543210", "first_name": "Ananya"},
            "items": [{"title": "Mind Calm"}],
        },
    }
    result = await service.handle_event(session, checkout, now=DAYTIME)
    assert result.queued == ["cart:c1"] and result.sent == []

    await service.dispatch_due(session, now=DAYTIME + timedelta(hours=2))
    row = await session.scalar(select(WhatsAppNotification))
    assert (row.status, row.error) == ("skipped", "no_marketing_opt_in")


async def test_order_cancelled_cancels_pending(session, provider, service):
    await service.handle_event(session, order_event(), now=DAYTIME)
    await service.handle_event(session, order_event("shipment.updated", shipment={"status": "shipped"}), now=NIGHT)
    await service.handle_event(session, order_event("order.cancelled"), now=NIGHT)
    row = await session.scalar(select(WhatsAppNotification).where(WhatsAppNotification.kind == "order_shipped"))
    assert row.status == "cancelled"


async def test_missing_phone_is_skipped(session, provider, service):
    event = order_event()
    event["order"]["customer"]["phone"] = ""
    result = await service.handle_event(session, event, now=DAYTIME)
    assert result.skipped == ["no_valid_phone"]


def test_signature_verification():
    body = b'{"type":"order.confirmed"}'
    signature = compute_signature("s3cret", "1793600000", body)
    assert verify_rootellect_signature("s3cret", "1793600000", signature, body, now=1793600010)
    assert not verify_rootellect_signature("s3cret", "1793600000", signature, body + b" ", now=1793600010)
    assert not verify_rootellect_signature("other", "1793600000", signature, body, now=1793600010)
    assert not verify_rootellect_signature("s3cret", "1793600000", signature, body, now=1793600000 + 600)
    assert not verify_rootellect_signature(None, "1793600000", signature, body, now=1793600010)


def test_rootellect_paths_skip_dashboard_auth_but_not_api():
    assert is_public_webhook_path("/webhooks/rootellect/events")
    assert is_public_webhook_path("/webhooks/cron/whatsapp-dispatch")
    assert not is_public_webhook_path("/api/v1/whatsapp/notifications")
