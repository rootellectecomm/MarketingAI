"""Walk a fake order through every WhatsApp message, to your own number.

Sends signed events to a deployed MarketingAI backend exactly like
rootellect.com does, so you can test without placing a real order.

Usage (from backend/):
    python scripts/send_test_order_events.py --url https://<backend-domain> --phone 98XXXXXXXX
    python scripts/send_test_order_events.py --url ... --phone ... --cod
    python scripts/send_test_order_events.py --url ... --phone ... --steps confirmed,shipped
    python scripts/send_test_order_events.py --url ... --phone ... --follow-ups

Needs ROOTELLECT_EVENTS_SECRET (same value as on the backend) in the
environment or backend/.env.

--follow-ups backdates delivery by 30 days so the usage guide, feedback
request and reorder reminder are all due at once, then triggers a dispatch.
The reorder reminder is marketing, so it only arrives if your number has
opted in (send START to the business number first).

Shipping/delivered/follow-up messages respect quiet hours (21:00-09:00 IST);
run outside those hours or they will wait until 9 AM.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.webhooks.rootellect import compute_signature  # noqa: E402

STEPS = ("confirmed", "shipped", "out_for_delivery", "delivered")


def post(client: httpx.Client, url: str, secret: str, path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    response = client.post(
        f"{url}{path}",
        content=body,
        headers={
            "content-type": "application/json",
            "x-rootellect-timestamp": timestamp,
            "x-rootellect-signature": compute_signature(secret, timestamp, body),
        },
    )
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text[:500]}
    if response.status_code >= 400:
        raise SystemExit(f"{path} -> HTTP {response.status_code}: {data}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="MarketingAI backend base URL, e.g. https://api.example.com")
    parser.add_argument("--phone", required=True, help="Your WhatsApp number, e.g. 9876543210 or +919876543210")
    parser.add_argument("--name", default="Partik")
    parser.add_argument("--order", default=None, help="Order number to use (default: a fresh TEST-xxxx)")
    parser.add_argument("--cod", action="store_true", help="Test the Cash on Delivery confirm/cancel flow")
    parser.add_argument("--steps", default=",".join(STEPS), help=f"Comma list from: {', '.join(STEPS)}")
    parser.add_argument("--follow-ups", action="store_true", help="Backdate delivery 30 days to fire follow-ups now")
    parser.add_argument("--pause", type=float, default=4.0, help="Seconds between steps")
    args = parser.parse_args()

    secret = get_settings().rootellect_events_secret
    if not secret:
        print("Set ROOTELLECT_EVENTS_SECRET (same value as on the backend).", file=sys.stderr)
        return 2

    url = args.url.rstrip("/")
    number = args.order or f"TEST-{int(time.time()) % 100000:05d}"
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = set(steps) - set(STEPS)
    if unknown:
        print(f"Unknown steps: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    if args.follow_ups and "delivered" not in steps:
        steps.append("delivered")

    order = {
        "order_number": number,
        "track_code": number,
        "total": 1299,
        "currency": "INR",
        "payment_method": "cod" if args.cod else "prepaid",
        "review_token": "test-token",
        "customer": {"first_name": args.name, "phone": args.phone, "email": None},
        "lines": [{"title": "Mind Calm", "quantity": 1, "slug": "mind-calm", "supply_days": 30}],
    }
    shipments = {
        "shipped": {"status": "shipped", "courier": "Delhivery", "awb": "TESTAWB123"},
        "out_for_delivery": {"status": "out_for_delivery"},
        "delivered": {"status": "delivered"},
    }

    print(f"Test order {number} -> {args.phone} ({'COD' if args.cod else 'prepaid'})")
    with httpx.Client(timeout=30) as client:
        for index, step in enumerate(steps):
            if step == "confirmed":
                event = {"type": "order.confirmed", "event_id": f"order.confirmed:{number}", "order": order}
            else:
                shipment = dict(shipments[step])
                if step == "delivered" and args.follow_ups:
                    shipment["delivered_at"] = (datetime.now(UTC) - timedelta(days=30)).isoformat()
                event = {"type": "shipment.updated", "event_id": f"shipment.updated:{number}:{step}", "order": order,
                         "shipment": shipment}
            event["occurred_at"] = datetime.now(UTC).isoformat()
            result = post(client, url, secret, "/webhooks/rootellect/events", event)
            print(f"  {step:<17} queued={result.get('queued')} sent={result.get('sent')} skipped={result.get('skipped')}")
            if index < len(steps) - 1:
                time.sleep(args.pause)

        result = post(client, url, secret, "/webhooks/cron/whatsapp-dispatch", {})
        print(f"  dispatch          {result}")

    print("\nCheck progress in Neon's SQL editor:")
    print(f"  select kind, status, error, scheduled_for, sent_at from whatsapp_notifications "
          f"where order_external_id = '{number}' order by created_at;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
