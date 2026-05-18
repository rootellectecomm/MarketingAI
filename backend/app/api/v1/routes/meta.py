from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.database.session import get_session
from app.services.meta_oauth import MetaOAuthService
from app.services.meta_sync import MetaSyncService

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/connect", response_model=None)
async def connect_meta() -> Response:
    settings = get_settings()
    missing = [
        key
        for key, value in {
            "META_APP_ID": settings.meta_app_id,
            "META_APP_SECRET": settings.meta_app_secret,
            "META_OAUTH_REDIRECT_URI": settings.meta_oauth_redirect_uri,
            "JWT_SECRET_KEY": settings.jwt_secret_key,
        }.items()
        if not value or str(value).startswith("change-me") or str(value).startswith("replace-")
    ]
    if missing:
        return JSONResponse(
            {
                "status": "setup_required",
                "missing_or_placeholder_env": missing,
                "required_backend_env": {
                    "META_APP_ID": "from Meta App Dashboard",
                    "META_APP_SECRET": "from Meta App Dashboard",
                    "META_OAUTH_REDIRECT_URI": "https://marketing-ai-gymu.vercel.app/api/v1/meta/callback",
                    "META_CONNECT_SUCCESS_URL": "https://marketing-ai-gamma-virid.vercel.app/settings",
                    "PROVIDER_MODE": "facebook_page_backed",
                },
            },
            status_code=200,
        )

    try:
        return RedirectResponse(MetaOAuthService().authorization_url(), status_code=302)
    except Exception as exc:
        return JSONResponse(
            {
                "status": "meta_connect_error",
                "message": str(exc),
            },
            status_code=500,
        )


@router.get("/callback", response_model=None)
async def meta_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if error:
        raise HTTPException(status_code=400, detail=error_description or error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing Meta OAuth code or state")

    service = MetaOAuthService()
    service.verify_state(state)
    result = await service.connect_from_code(session, code)

    success_url = get_settings().meta_connect_success_url
    if success_url:
        separator = "&" if "?" in success_url else "?"
        return RedirectResponse(
            f"{success_url}{separator}meta=connected&instagram_accounts={len(result['instagram_accounts'])}",
            status_code=302,
        )
    return JSONResponse(result)


@router.post("/sync/comments", dependencies=[Depends(get_current_user)])
async def sync_meta_comments(
    media_limit: int = Query(default=8, ge=1, le=25),
    comments_per_media: int = Query(default=25, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await MetaSyncService().sync_recent_comments(
        session,
        media_limit=media_limit,
        comments_per_media=comments_per_media,
    )
