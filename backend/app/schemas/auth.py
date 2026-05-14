from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}


class BootstrapResponse(BaseModel):
    created: bool
    user: UserRead

