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
| How to take it | Delivered + 2 days, 10:30 IST | Scheduled | Marketing (re-classified by Meta) | Marketing opt-ins only |
| Feedback request | Delivered + 14 days, 11:00 IST | Scheduled | Utility | Customers with a review link |
| Reorder reminder | 5 days before the first product runs out | Scheduled | Marketing | Marketing opt-ins only |
| Welcome + first-order voucher | `customer.welcome` (new account, WhatsApp opt-in ticked) | Next send window | Marketing | Opted-in new customers |
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
4. **Test without a real order.** From `backend/`, with `ROOTELLECT_EVENTS_SECRET` set:
   ```bash
   python scripts/send_test_order_events.py --url https://<backend-domain> --phone <your number>          # prepaid journey
   python scripts/send_test_order_events.py --url https://<backend-domain> --phone <your number> --cod    # COD buttons
   python scripts/send_test_order_events.py --url https://<backend-domain> --phone <your number> --follow-ups
   ```
   Then place one real order to your own number from rootellect.com.

## Event contract (rootellect.com → MarketingAI)

`POST /webhooks/rootellect/events`

Headers: `X-Rootellect-Timestamp: <unix seconds>`, `X-Rootellect-Signature: sha256=<hex HMAC-SHA256 of "<timestamp>.<raw body>">`. Requests older than 5 minutes are rejected.

```json
{
  "type": "order.confirmed | shipment.updated | order.cancelled | checkout.abandoned | customer.welcome",
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
  "customer": { "customer_code": "RT-0042", "first_name": "Meera", "phone": "+91…", "whatsapp_marketing_opt_in": true, "voucher": { "code": "WELCOME…", "percent_off": 10, "expires_on": "8 Dec 2026" } },
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

## Live agent handover

Customers can reach a person at any time. The bot hands a WhatsApp chat to the team when:

- the customer asks for a person ("talk to a person", "customer care", "call me", "/help", "kisi se baat karni hai"),
- the customer sends a cart from the WhatsApp catalog (they get an item summary + checkout link first),
- the bot cannot answer safely (low confidence, AI unavailable, health/medicine questions).

What happens:

1. The bot pauses for that customer only. Everyone else keeps getting bot replies.
2. The customer is told a person is coming. Outside support hours (10 AM – 7 PM, Monday to Saturday, IST)
   they are told when the team will reply.
3. Every number in `LIVE_AGENT_TEAM_PHONES` gets a WhatsApp alert from the business number with the customer's
   name, number, reason and message. If a team member hasn't messaged the business number in the last 24 hours,
   WhatsApp only allows a template, so the `rootellect_team_alert_v1` template is sent instead.
   Tip: each team member can send "hi" to the business number once a day to keep alerts free-form.
   Messages from team numbers are never answered by the bot.
4. The team replies from **Dashboard → Conversations**. Chats waiting for a person show **Needs team** at the top.
   Replies only work within 24 hours of the customer's last message (a WhatsApp rule).
5. The bot resumes when the team taps **Resume bot**, or on its own 24 hours after the last team reply.
   **Take over chat** pauses the bot for any customer manually.

Settings (backend env): `LIVE_AGENT_TEAM_PHONES` (comma-separated, with country code, e.g. `919876543210,919812345678`),
`LIVE_AGENT_HOURS_START=10`, `LIVE_AGENT_HOURS_END=19`, `LIVE_AGENT_DAYS=0,1,2,3,4,5` (0 = Monday),
`LIVE_AGENT_IDLE_HOURS=24`, `LIVE_AGENT_ENABLED=true`, `FRONTEND_URL` (dashboard link in alerts).

## Scheduled message safeguards

- Scheduled messages are also sent whenever a WhatsApp webhook arrives (at most every 10 minutes), so reminders
  flow on Vercel without a worker. For full reliability also set the GitHub Actions scheduler
  (`.github/workflows/whatsapp-dispatch.yml`): add the repository secret `MARKETINGAI_CRON_SECRET` (same value as the
  backend's `CRON_SECRET`) and the repository variable `MARKETINGAI_BACKEND_URL`.
- A scheduled message more than 6 hours late (cart reminders: 60 minutes) is skipped as `stale_too_late`
  instead of being sent at an odd time.
- Follow-ups for `TEST-*` orders (from `scripts/send_test_order_events.py`) are skipped as `test_order`.
  Immediate messages (order confirmed, COD) still go out so the test journey can be checked.
