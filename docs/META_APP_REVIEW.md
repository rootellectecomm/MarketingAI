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

## If Facebook Shows "Feature Unavailable"

This error is returned by Meta before the app reaches our callback URL. Fix it in Meta App Dashboard:

1. Add **Facebook Login for Business** to the Meta app.
2. Create a Login for Business configuration and add the permissions used by the backend:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata`,
   `pages_manage_engagement`, `instagram_basic`, `instagram_manage_comments`,
   and `instagram_manage_messages`.
3. Copy the configuration ID into `META_LOGIN_CONFIG_ID`.
4. Add the exact Valid OAuth Redirect URI:
   `https://marketing-ai-gymu.vercel.app/api/v1/meta/callback`
5. If the app is in development mode, add the Facebook account you are using as an
   Admin, Developer, or Tester under **App Roles**.
6. For public users, switch the app to Live mode and complete any required business
   verification/app review for advanced permissions.

