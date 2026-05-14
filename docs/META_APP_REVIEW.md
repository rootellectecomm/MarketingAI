# Meta App Review Readiness

The codebase uses mock adapters locally so development can continue before Meta app review is complete.

## Evidence To Prepare

- Screen recording of webhook receipt and dashboard log.
- Screen recording of a user comment producing a public reply and private reply in mock mode.
- Explanation of safety gates for spam, abuse, prompt injection, and medical-risk comments.
- Privacy policy and data deletion instructions.
- WhatsApp opt-in flow and approved template examples.

## Permissions Likely Needed

Exact permissions depend on whether Rootellect uses Instagram Professional Login or Facebook Page-backed Instagram Business setup. The provider layer supports both paths, but only one should be active per deployment.

## Live Cutover

1. Keep `PROVIDER_MODE=mock` while app review is pending.
2. Store approved credentials through the encrypted provider credential flow.
3. Switch `PROVIDER_MODE`.
4. Send test webhooks.
5. Watch `/api/v1/webhooks/logs`, `/api/v1/ai-logs`, and `/api/v1/moderation`.

