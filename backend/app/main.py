from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_cors_origin_regex, get_cors_origins, get_settings
from app.core.logging import configure_logging
from app.database.session import dispose_engine, get_engine
from app.middleware.cors import VercelCorsMiddleware
from app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.realtime import manager
from app.webhooks.routes import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield
    await dispose_engine()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(settings),
    allow_origin_regex=get_cors_origin_regex(settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(VercelCorsMiddleware)

app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(webhook_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "docs": f"{settings.api_v1_prefix}/docs",
        "health": "/health",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/debug/config")
async def debug_config() -> dict:
    return {
        "environment": settings.environment,
        "database_configured": bool(settings.database_url),
        "redis_configured": bool(settings.redis_url),
        "openai_configured": bool(settings.openai_api_key),
        "meta_app_id_configured": bool(settings.meta_app_id),
        "meta_app_secret_configured": bool(settings.meta_app_secret),
        "provider_mode": settings.provider_mode,
    }


@app.get("/ready")
async def ready() -> dict:
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
