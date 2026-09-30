from common import AuthenticatedUser
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.services.auth_service import AuthService
from app.core.security import get_current_user
from app.interfaces.api.dependencies import get_auth_service
from app.interfaces.schemas.user import (
    AccessTokenSchema,
    RefreshSchema,
    RegisterSchema,
    TokenSchema,
    UserReadSchema,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserReadSchema, status_code=status.HTTP_201_CREATED)
async def register(
        data: RegisterSchema,
        service: AuthService = Depends(get_auth_service),
):
    """Регистрация. Пароль: от 8 символов, заглавная и строчная буквы, цифра, спецсимвол."""
    user = await service.register(data.email, data.password)
    return UserReadSchema.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenSchema)
async def login(
        form: OAuth2PasswordRequestForm = Depends(),
        service: AuthService = Depends(get_auth_service),
):
    """
    Вход. Форма OAuth2: `username` = email, `password`.

    Формат формы нужен, чтобы работала кнопка Authorize в Swagger UI.
    """
    user = await service.authenticate(form.username, form.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=AccessTokenSchema)
async def refresh(
        data: RefreshSchema,
        service: AuthService = Depends(get_auth_service),
):
    """Получить новый access-токен по refresh-токену."""
    return await service.refresh_access_token(data.refresh_token)


@router.get("/me", response_model=UserReadSchema)
async def me(
        current: AuthenticatedUser = Depends(get_current_user),
        service: AuthService = Depends(get_auth_service),
):
    """Текущий пользователь."""
    user = await service.get_user(current.id)
    return UserReadSchema.model_validate(user, from_attributes=True)
