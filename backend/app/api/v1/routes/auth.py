from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database.init_db import ensure_schema
from app.database.session import get_session
from app.models.entities import User
from app.models.enums import UserRole
from app.schemas.auth import BootstrapResponse, LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_admin(session: AsyncSession = Depends(get_session)) -> BootstrapResponse:
    try:
        await ensure_schema()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database setup failed. Check DATABASE_URL on Vercel: {exc}",
        ) from exc

    settings = get_settings()
    admin_email = settings.admin_email.lower()
    existing = await session.scalar(select(User).where(User.email == admin_email))
    if existing:
        return BootstrapResponse(created=False, user=UserRead.model_validate(existing))

    user = User(
        email=admin_email,
        full_name="Rootellect Owner",
        role=UserRole.owner,
        password_hash=hash_password(settings.admin_password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return BootstrapResponse(created=True, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    try:
        await ensure_schema()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable. Check DATABASE_URL on Vercel: {exc}",
        ) from exc

    user = await session.scalar(select(User).where(User.email == payload.email.lower(), User.is_active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=user.id, email=user.email, role=user.role.value)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))

