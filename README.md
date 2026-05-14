# Rootellect Instagram AI Automation

Production-grade monorepo for Rootellect's AI-powered Instagram and WhatsApp automation platform.

## What Is Included

- FastAPI backend with async SQLAlchemy, PostgreSQL, Redis queue worker, JWT auth, rate limiting, security headers, webhook validation, and audit-ready data models.
- OpenAI-ready AI pipeline with deterministic local fallback, structured decision schema, moderation, RAG retrieval, lead scoring, and action execution.
- Provider adapter layer for mock Meta, Instagram Professional Login, Facebook Page-backed Instagram, and WhatsApp Cloud API.
- Next.js App Router dashboard with TypeScript, TailwindCSS, shadcn-style UI primitives, dark mode, analytics, comments, leads, campaigns, moderation, knowledge, webhooks, and settings.
- Docker Compose for API, worker, Postgres, Redis, ChromaDB, and Nginx.
- Alembic migration, env templates, CI workflow, seed knowledge, API docs, and deployment notes.

## Local Backend

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis chroma
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Bootstrap the first admin after the API is running:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/v1/auth/bootstrap
```

For live AI generation, set `OPENAI_API_KEY` in the backend environment. Without it, the backend uses a deterministic local fallback so the webhook and dashboard flow still works.

## Local Frontend

```powershell
cd frontend
$env:npm_config_strict_ssl='false'
npm install
npm run dev
```

Dashboard: `http://localhost:3000`

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

API: `http://localhost:8000`
Reverse proxy: `http://localhost:8080`

## Webhook Smoke Payload

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/webhooks/meta/instagram `
  -ContentType 'application/json' `
  -Body '{"entry":[{"id":"rootellect","changes":[{"field":"comments","value":{"id":"comment_1","text":"Need price for Mind Calm","from":{"id":"user_1","username":"riya"},"media_id":"reel_1"}}]}]}'
```

In local mode, missing signatures are logged but not rejected. In production, invalid signatures return `401`.
