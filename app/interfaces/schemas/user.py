from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterSchema(BaseModel):
    email: EmailStr
    # сложность (заглавные, цифры, спецсимвол) проверяет AuthService
    password: str = Field(..., min_length=8, max_length=128)


class RefreshSchema(BaseModel):
    refresh_token: str


class UserReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    created_at: datetime


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutSchema(BaseModel):
    """Refresh-токен можно передать, чтобы отозвать и его (иначе отзывается только access)."""
    refresh_token: Optional[str] = None
