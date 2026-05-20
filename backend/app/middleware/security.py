from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.rate_limit import InMemoryTokenBucket


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if get_settings().environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        settings = get_settings()
        self.bucket = InMemoryTokenBucket(settings.rate_limit_requests, settings.rate_limit_window_seconds)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in {"/health", "/ready", "/webhook"} or request.url.path.startswith("/webhooks/meta"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        if not self.bucket.allow(client):
            return Response("Rate limit exceeded", status_code=429)
        return await call_next(request)

