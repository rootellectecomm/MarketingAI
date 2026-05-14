# Security Notes

- Webhooks validate `X-Hub-Signature-256` against the raw request body.
- Admin APIs require JWT bearer tokens.
- Passwords are hashed with Argon2.
- Provider credentials are encrypted before storage.
- Production responses include security headers and HSTS.
- Rate limiting is applied to admin API routes.
- Prompt injection, spam, abuse, and medical-risk language are safety-gated before actions are sent.
- The AI prompt forbids diagnosis, cure guarantees, unsafe advice, invented product claims, and repetitive spam-like replies.
- OpenAI responses are requested through structured outputs and validated against the backend Pydantic decision schema before any action is executed.

## Production Hardening Checklist

- Replace every default secret before deploy.
- Enforce HTTPS at the edge.
- Restrict database and Redis access to private networking.
- Configure backups for PostgreSQL and ChromaDB volumes.
- Review dashboard roles before adding non-admin agents.
- Enable provider token rotation and audit-log review.
