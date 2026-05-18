from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_cors_origins, get_settings


def _is_allowed_origin(origin: str) -> bool:
    settings = get_settings()
    if origin in get_cors_origins(settings):
        return True
    if origin.endswith(".vercel.app") and origin.startswith("https://"):
        return True
    return False


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With",
        "Vary": "Origin",
    }


class VercelCorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        origin = request.headers.get("origin")

        if request.method == "OPTIONS" and origin and _is_allowed_origin(origin):
            return Response(status_code=204, headers=_cors_headers(origin))

        response = await call_next(request)

        if origin and _is_allowed_origin(origin):
            for key, value in _cors_headers(origin).items():
                response.headers[key] = value

        return response
