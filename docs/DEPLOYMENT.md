# Deployment Guide

## Target Architecture

- Frontend: Vercel project pointed at `frontend/`.
- Backend: Docker Compose on a VPS running API, worker, Postgres, Redis, ChromaDB, and Nginx.
- DNS: public HTTPS domain terminates at Nginx on the VPS.

## Required Production Environment

Copy [`.env.production.example`](../.env.production.example) to `.env` on the VPS and set:

- `ENVIRONMENT=production`
- `PROVIDER_MODE=facebook_page_backed`
- `JWT_SECRET_KEY`, `ENCRYPTION_SECRET`
- `DATABASE_URL`, `REDIS_URL`
- `META_*` credentials and webhook verify token
- `OPENAI_API_KEY`, `OPENAI_MODEL` (e.g. `gpt-4.1-mini`)
- `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`
- `BACKEND_CORS_ORIGINS` = your frontend URL

Optional Shopify (cart recovery):

- `SHOPIFY_WEBHOOK_SECRET`
- `SHOPIFY_STORE_DOMAIN`

## VPS Steps

1. Install Docker and Docker Compose.
2. Clone the repo and copy `.env.production.example` → `.env`; fill all secrets.
3. Run `docker compose up -d --build`.
4. Run migrations: `docker compose exec api alembic upgrade head`
5. Confirm `https://api.yourdomain.com/health` (via Nginx on port 8080 or your TLS proxy).
6. Bootstrap admin once: `POST https://api.yourdomain.com/api/v1/auth/bootstrap`
7. In the dashboard **Settings**, use **Connect Facebook & Instagram** (calls authenticated `/meta/connect-url`).
8. Configure Meta App webhooks:
   - `https://api.yourdomain.com/webhooks/meta/instagram`
   - `https://api.yourdomain.com/webhooks/meta/whatsapp`
   - Subscribe: `comments`, `messages` (IG); `messages` (WA)
9. Configure Vercel frontend:
   - `NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api/v1`
   - `BACKEND_WEBHOOK_URL=https://api.yourdomain.com/webhooks/meta/instagram` (if forwarding via Vercel)

## Worker & Queue

Webhooks enqueue jobs to Redis (ARQ). The `worker` service must be running:

```bash
docker compose ps worker
docker compose logs -f worker
```

Cron jobs (funnel steps, conversation recovery, retention) run inside the worker.

## Verification

1. `GET /api/v1/settings/providers` — Instagram/WhatsApp ready after OAuth.
2. Post a real IG comment with keyword `PCOS` — check Comments + AI Logs in dashboard.
3. Reply in DM — conversation thread should show inbound + outbound messages.
4. WhatsApp inbound message — should get AI reply (not `mock-wa-*` IDs when live).

## Operational Notes

- Invalid webhook signatures are rejected in `ENVIRONMENT=production`.
- Rotate Meta tokens via OAuth reconnect.
- Tune `AI_MIN_AUTOSEND_CONFIDENCE` using AI Logs during launch.
