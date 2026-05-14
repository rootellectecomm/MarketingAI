from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.entities import User
from app.schemas.auth import UserRead

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserRead)
async def read_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)

