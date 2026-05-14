# API Reference

Base URL: `/api/v1`

## Auth

- `POST /auth/bootstrap` creates the first owner from environment variables when no users exist.
- `POST /auth/login` returns a JWT access token.
- `GET /me` returns the current user.

## Dashboard

- `GET /dashboard/metrics` returns comment volume, lead count, automated action count, escalation count, confidence average, sentiment distribution, and latest AI activity.

## Social Operations

- `GET /comments` lists processed Instagram comments.
- `GET /conversations` lists conversation summaries.
- `GET /conversations/{conversation_id}/messages` lists messages.
- `GET /webhooks/logs` lists raw webhook deliveries and processing status.

## CRM And Campaigns

- `GET /leads` lists leads by score.
- `PATCH /leads/{lead_id}` updates lifecycle, phone, opt-in, or tags.
- `GET /campaigns` lists campaigns.
- `POST /campaigns` creates a campaign.

## AI And Safety

- `GET /ai-logs` lists AI decisions and confidence scores.
- `GET /moderation` lists moderation actions.
- `GET /knowledge` lists knowledge entries.
- `POST /knowledge` creates a knowledge entry.

## Provider Settings

- `GET /settings/providers` returns Meta, WhatsApp, OpenAI, and Chroma readiness.

## Meta Webhooks

- `GET /webhooks/meta/instagram` verifies Instagram subscriptions.
- `POST /webhooks/meta/instagram` receives Instagram comments, mentions, and DMs.
- `GET /webhooks/meta/whatsapp` verifies WhatsApp subscriptions.
- `POST /webhooks/meta/whatsapp` receives WhatsApp messages and statuses.

## Realtime

- `WS /ws/events` is reserved for dashboard events such as new comments, AI decisions, lead-score updates, and action failures.
