from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_session
from app.services.meta_oauth import MetaOAuthService

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/connect")
async def connect_meta() -> RedirectResponse:
    return RedirectResponse(MetaOAuthService().authorization_url(), status_code=302)


@router.get("/callback")
async def meta_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse | dict:
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
    return result
