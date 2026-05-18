# Deployment Guide

## Target Architecture

- Frontend: Vercel project pointed at `frontend/`.
- Backend: Docker Compose on a VPS running API, worker, Postgres, Redis, ChromaDB, and Nginx.
- DNS: public HTTPS domain terminates at a reverse proxy or load balancer in front of the VPS.

## Required Production Environment

Set strong values for:

- `JWT_SECRET_KEY`
- `ENCRYPTION_SECRET`
- `DATABASE_URL`
- `REDIS_URL`
- `META_VERIFY_TOKEN`
- `META_APP_SECRET`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`

Set OpenAI defaults:

- `OPENAI_MODEL=gpt-5.4-mini`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

Set Meta credentials after app review:

- `META_APP_ID`
- `META_APP_SECRET`
- `META_OAUTH_REDIRECT_URI=https://api.example.com/api/v1/meta/callback`
- `META_CONNECT_SUCCESS_URL=https://app.example.com/settings`
- `PROVIDER_MODE=facebook_page_backed`
- provider access tokens stored through encrypted credentials
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`

## VPS Steps

1. Install Docker and Docker Compose.
2. Copy `.env.example` to `.env` and replace all secrets.
3. Run `docker compose up -d --build`.
4. Confirm `http://SERVER_IP:8080/health`.
5. Run `POST /api/v1/auth/bootstrap` once.
6. Configure Meta webhook callback URLs:
   - `https://api.example.com/webhooks/meta/instagram`
   - `https://api.example.com/webhooks/meta/whatsapp`
7. Configure Vercel env:
   - `NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1`
   - `NEXT_PUBLIC_WS_URL=wss://api.example.com/ws/events`

## Operational Notes

- Keep `PROVIDER_MODE=mock` until Meta permissions and webhook subscriptions are approved.
- In production, invalid `X-Hub-Signature-256` webhook signatures are rejected.
- Rotate provider tokens regularly and store them encrypted.
- Review AI logs during launch to tune `AI_MIN_AUTOSEND_CONFIDENCE`.
