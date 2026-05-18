from pydantic import BaseModel

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}


class BootstrapResponse(BaseModel):
    created: bool
    user: UserRead


class ResetAdminResponse(BaseModel):
    email: str
    reset: bool
    message: str
