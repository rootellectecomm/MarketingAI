# WhatsApp Order Notifications

Automated WhatsApp messages for rootellect.com orders, sent through the WhatsApp Cloud API connection this platform already uses.

## What gets sent

| Message | Trigger | Timing | Category | Who receives it |
|---|---|---|---|---|
| Order confirmed (prepaid) | `order.confirmed` | Immediately | Utility | Every customer |
| COD confirmation with Confirm / Cancel buttons | `order.confirmed` (COD) | Immediately | Utility | Every COD customer |
| Shipped + tracking | `shipment.updated` → `shipped` | Next send window | Utility | Every customer |
| Out for delivery (+ COD amount) | `shipment.updated` → `out_for_delivery` | Next send window | Utility | Every customer |
| Delivery attempt failed | `shipment.updated` → `delivery_failed` | Next send window, max once a day | Utility | Every customer |
| Delivered | `shipment.updated` → `delivered` | Next send window | Utility | Every customer |
| How to take it | Delivered + 2 days, 10:30 IST | Scheduled | Utility | Every customer |
| Feedback request | Delivered + 14 days, 11:00 IST | Scheduled | Utility | Customers with a review link |
| Reorder reminder | 5 days before the first product runs out | Scheduled | Marketing | Marketing opt-ins only |
| Cart reminder | `checkout.abandoned` + 1 hour | Scheduled | Marketing | Marketing opt-ins only, skipped if they bought |
| Offer broadcasts | `POST /api/v1/whatsapp/broadcasts` | You choose | Marketing | Marketing opt-ins only |

The send window is 09:00–21:00 IST (`WHATSAPP_QUIET_HOURS_START/END`, `WHATSAPP_SEND_TIMEZONE`). Order and COD confirmations ignore it because the customer just acted.

Template copy lives in `backend/app/services/whatsapp_templates.py`. It is the single source for both submission to Meta and sending.

## Consent rules

- **Order updates (utility):** sent to anyone who places an order, unless they reply STOP.
- **Marketing:** only to contacts with `marketing_opt_in = true`. Consent comes from: the customer messaging START / JOIN / SUBSCRIBE, `whatsapp_marketing_opt_in: true` in an order event (once rootellect.com collects it at checkout), or `POST /api/v1/whatsapp/contacts/opt-in` with a real consent source.
- **STOP / UNSUBSCRIBE** turns off everything, including the older funnel flows. **START** turns it back on.
- Consent is checked when a message is sent, not when it is scheduled.
- If Meta reports error 131050 (customer blocked marketing in WhatsApp), marketing opt-in is switched off automatically.

## Setup

1. **Secrets.** Generate one random secret and set it in both places:
   - MarketingAI backend: `ROOTELLECT_EVENTS_SECRET`
   - rootellect.com: `MARKETINGAI_EVENTS_SECRET`, plus `MARKETINGAI_EVENTS_URL=https://<backend-domain>`
2. **Templates.** Set `WHATSAPP_BUSINESS_ACCOUNT_ID` (WhatsApp Manager → Account tools → Phone numbers shows the WABA ID), then from `backend/`:
   ```bash
   python scripts/create_whatsapp_templates.py --dry-run   # review
   python scripts/create_whatsapp_templates.py             # submit
   ```
   Approval usually takes minutes to a day. Messages for templates that are not approved yet fail with a template error and are marked `failed`.
3. **Scheduler.** Scheduled messages are sent by `/webhooks/cron/whatsapp-dispatch`. Any one of these works:
   - rootellect.com's Shiprocket cron pings it after every run (built in, uses the shared signed secret).
   - An external scheduler (e.g. cron-job.org) every 10–15 minutes with `Authorization: Bearer <CRON_SECRET>`.
   - On the Docker/VPS deployment, the ARQ worker runs it every 10 minutes.
4. **Deploy and test** with a real order to your own number.

## Event contract (rootellect.com → MarketingAI)

`POST /webhooks/rootellect/events`

Headers: `X-Rootellect-Timestamp: <unix seconds>`, `X-Rootellect-Signature: sha256=<hex HMAC-SHA256 of "<timestamp>.<raw body>">`. Requests older than 5 minutes are rejected.

```json
{
  "type": "order.confirmed | shipment.updated | order.cancelled | checkout.abandoned",
  "event_id": "order.confirmed:RT-1001",
  "occurred_at": "2026-11-02T05:30:00Z",
  "order": {
    "order_number": "RT-1001",
    "track_code": "RT-1001",
    "total": 1299,
    "currency": "INR",
    "payment_method": "prepaid | cod",
    "review_token": "<signed review token, optional>",
    "customer": { "first_name": "Ananya", "phone": "+919876543210", "email": "a@example.com", "whatsapp_marketing_opt_in": false },
    "lines": [{ "title": "Mind Calm", "quantity": 2, "slug": "mind-calm", "supply_days": 60 }]
  },
  "shipment": { "status": "shipped | out_for_delivery | delivered | delivery_failed", "courier": "Delhivery", "awb": "123", "delivered_at": "…" },
  "checkout": { "cart_key": "abc", "customer": { "first_name": "Ananya", "phone": "+91…" }, "items": [{ "title": "Mind Calm" }] }
}
```

Every event is idempotent: each message has a key such as `RT-1001:order_shipped`, so repeats are ignored.

## Dashboard API (JWT)

- `GET /api/v1/whatsapp/notifications?status=&order=&kind=`: send log with delivery/read status
- `GET /api/v1/whatsapp/cod-responses`: COD orders and whether the customer confirmed, cancelled or hasn't replied
- `GET /api/v1/whatsapp/templates`
- `POST /api/v1/whatsapp/contacts/opt-in`
- `POST /api/v1/whatsapp/broadcasts`: `dry_run` defaults to `true` and only counts recipients
- `POST /api/v1/whatsapp/dispatch`: send due messages now
