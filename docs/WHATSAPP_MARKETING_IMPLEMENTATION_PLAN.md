# WhatsApp Marketing Automation Implementation Plan

This plan moves Rootellect from local simulation toward real, opt-in WhatsApp marketing automation. The production path is the WhatsApp Business Platform Cloud API. Do not build automation around WhatsApp Web, personal WhatsApp, browser QR sessions, or unofficial OTP login flows. Those paths are fragile, hard to audit, and can violate WhatsApp rules.

## Current State

- Frontend data is live by default. Mock dashboard data is used only when `NEXT_PUBLIC_USE_MOCK_DATA=true`.
- Backend provider mode is still commonly set to `mock` in example env files for local development.
- WhatsApp send paths now await the async provider factory.
- Live provider modes no longer fall back to fake WhatsApp send results when credentials are missing.
- Provider readiness now checks active WhatsApp Cloud credentials saved in the database as well as env vars.

## Required Production Decisions

1. Use official Cloud API for all WhatsApp automation.
2. Use OTP only for registering or migrating a business phone number in Meta, not for logging into WhatsApp Web.
3. Require clear customer opt-in before promotional or nurture messages.
4. Use approved WhatsApp templates for business-initiated messages and messages outside the customer service window.
5. Use free-form replies only inside the active customer service window after the user messages the business.
6. Keep mock mode for local development, but never enable it in staging or production.

## Meta Setup

1. Create or verify the Meta Business portfolio.
2. Create the Meta Developer app and add WhatsApp.
3. Create or connect the WhatsApp Business Account.
4. Register the business phone number through Meta's OTP flow.
5. Store the resulting `WHATSAPP_PHONE_NUMBER_ID` and long-lived access token in backend secrets.
6. Configure webhook callback:
   - `https://<backend-domain>/webhooks/meta/whatsapp`
   - Subscribe to WhatsApp `messages`.
7. Create and submit approved templates:
   - Opt-in confirmation template.
   - Product education follow-up template.
   - Cart recovery template.
   - Post-purchase check-in template.
8. Add test numbers and run inbound and outbound tests before app review/live rollout.

Useful official docs:

- WhatsApp Cloud API overview: https://developers.facebook.com/docs/whatsapp/cloud-api/
- Business phone number registration: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/registration/
- Send messages: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages/
- Message templates: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates/
- Webhooks: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/

## Data Model And Real Inputs

Real automation needs these inputs before any WhatsApp campaign is activated:

- Brand: Rootellect legal entity, support contact, website, privacy policy, shipping and refund policy.
- Products: names, approved claims, price, variants, stock status, product URLs.
- Audience: consent source, phone number, source channel, lifecycle stage, tags.
- Campaign: target Instagram media URLs or IDs, trigger keywords, product focus, allowed channels.
- WhatsApp: opt-in status, template name, language code, last inbound message time, unsubscribe status.
- Commerce: Shopify customer phone, cart URL, order status, purchased products.

Do not seed production with sample leads, sample comments, fake participants, or fake analytics. Development seed files can stay for local testing, but production must start empty and fill only from webhooks, admin-created knowledge, uploaded contacts with consent, and commerce integrations.

## Automation Rules

1. Inbound WhatsApp message:
   - Normalize webhook message.
   - Upsert conversation, lead, and inbound message.
   - Mark WhatsApp opt-in true only because the user messaged the business or because consent was imported with proof.
   - Generate an AI decision using RAG, moderation, campaign gates, and lead history.
   - Send free-form reply only if inside the customer service window.

2. Instagram comment to DM:
   - Match active campaign by media and keyword.
   - Public reply only if campaign allows public replies.
   - Send private reply only if campaign allows DMs.
   - Ask for WhatsApp opt-in rather than jumping straight to WhatsApp.

3. WhatsApp follow-up:
   - If the user is opted in and inside service window, send free-form text.
   - If outside service window, send an approved template.
   - If no opt-in, do not send promotional content.

4. Cart recovery:
   - Require Shopify webhook signature in production.
   - Require customer phone and consent.
   - Include checkout link only in an approved template or within an active service window.

5. Retention:
   - Trigger only from real order records.
   - Use day 0, day 7, and day 21 check-ins.
   - Stop if user unsubscribes or asks not to be contacted.

## Dashboard Requirements

- Settings must show WhatsApp connected only when an active Cloud credential and phone number exist.
- Campaigns must warn if WhatsApp follow-up is enabled while WhatsApp is not ready.
- Leads must show opt-in source, opt-in time, and unsubscribe state.
- Conversations must identify whether a reply is free-form eligible or requires a template.
- Analytics must be calculated only from real database records.

## Environment Checklist

Production backend:

```env
ENVIRONMENT=production
PROVIDER_MODE=facebook_page_backed
META_APP_ID=<real app id>
META_APP_SECRET=<real secret>
META_OAUTH_REDIRECT_URI=https://<backend-domain>/api/v1/meta/callback
META_CONNECT_SUCCESS_URL=https://<frontend-domain>/settings
WHATSAPP_PHONE_NUMBER_ID=<real phone number id>
WHATSAPP_ACCESS_TOKEN=<real long-lived token>
WHATSAPP_OPT_IN_TEMPLATE_NAME=<approved template name>
OPENAI_API_KEY=<real key>
```

Production frontend:

```env
NEXT_PUBLIC_API_BASE_URL=https://<backend-domain>/api/v1
BACKEND_API_BASE_URL=https://<backend-domain>/api/v1
NEXT_PUBLIC_USE_MOCK_DATA=false
```

## Acceptance Tests

1. `/api/v1/settings/providers` returns `whatsapp_ready=true`.
2. Posting a real inbound WhatsApp message creates a conversation, lead, inbound message, AI log, and outbound provider action.
3. Live outbound actions return real Meta message IDs, never `mock-wa-*`.
4. Removing WhatsApp credentials makes sends fail with "Missing WhatsApp credentials" instead of succeeding.
5. Campaign dashboards show empty states on a fresh production database instead of sample data.
6. A user with no opt-in never receives promotional WhatsApp automation.
7. A user who unsubscribes is excluded from all WhatsApp follow-ups.

## Next Engineering Milestones

1. Add consent fields to the lead model: `whatsapp_opt_in_source`, `whatsapp_opt_in_at`, `whatsapp_unsubscribed_at`.
2. Track `last_inbound_at` for WhatsApp conversations and enforce template-only sends outside the service window.
3. Add an admin template registry so campaigns choose from approved template names instead of free text.
4. Add a production guard that blocks startup when `ENVIRONMENT=production` and `PROVIDER_MODE=mock`.
5. Replace remaining local seed knowledge placeholders with Rootellect-approved policy copy.
6. Add end-to-end tests using recorded Meta webhook fixtures and mocked Meta HTTP responses.
