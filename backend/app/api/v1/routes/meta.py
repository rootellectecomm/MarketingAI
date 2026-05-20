from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.database.session import get_session
from app.services.meta_oauth import MetaOAuthService
from app.services.meta_sync import MetaSyncService

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/connect-url")
async def connect_meta_url(_: str = Depends(get_current_user)) -> dict:
    settings = get_settings()
    missing = [
        key
        for key, value in {
            "META_APP_ID": settings.meta_app_id,
            "META_APP_SECRET": settings.meta_app_secret,
            "META_OAUTH_REDIRECT_URI": settings.meta_oauth_redirect_uri,
        }.items()
        if not value or str(value).startswith("replace-")
    ]
    if missing:
        return {"status": "setup_required", "missing_or_placeholder_env": missing}
    return {"status": "ok", "url": MetaOAuthService().authorization_url()}


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
                    "BACKEND_CORS_ORIGINS": "https://marketing-ai-gamma-virid.vercel.app",
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
        facebook_pages = len(result["facebook_pages"])
        instagram_accounts = len(result["instagram_accounts"])
        warning = ""
        if facebook_pages == 0:
            scopes = ",".join((result.get("diagnostics") or {}).get("debug_token", {}).get("scopes", []))
            warning = (
                "&warning=no_facebook_pages"
                "&message=Meta%20did%20not%20return%20any%20Facebook%20Pages.%20"
                "This%20usually%20means%20the%20token%20is%20missing%20pages_show_list%20or%20business_management%2C%20"
                "or%20the%20selected%20Facebook%20user%20does%20not%20have%20full%20control%20of%20the%20Page."
                f"&scopes={scopes}"
            )
        elif instagram_accounts == 0:
            warning = (
                "&warning=no_instagram_account"
                "&message=Facebook%20Page%20connected%2C%20but%20Meta%20did%20not%20return%20a%20linked%20Instagram%20Professional%20account."
            )
        return RedirectResponse(
            f"{success_url}{separator}meta=connected&facebook_pages={facebook_pages}"
            f"&instagram_accounts={instagram_accounts}{warning}",
            status_code=302,
        )
    return JSONResponse(result)


@router.post("/sync/comments", dependencies=[Depends(get_current_user)])
async def sync_meta_comments(
    media_limit: int = Query(default=25, ge=1, le=50),
    comments_per_media: int = Query(default=25, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await MetaSyncService().sync_recent_comments(
        session,
        media_limit=media_limit,
        comments_per_media=comments_per_media,
    )
