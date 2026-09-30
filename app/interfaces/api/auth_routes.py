from common import AuthenticatedUser
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.services.auth_service import AuthService
from app.core.security import get_current_user
from app.interfaces.api.client_ip import get_client_ip
from app.interfaces.api.dependencies import get_auth_service
from app.interfaces.schemas.user import (
    LogoutSchema,
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
        request: Request,
        form: OAuth2PasswordRequestForm = Depends(),
        service: AuthService = Depends(get_auth_service),
):
    """
    Вход. Форма OAuth2: `username` = email, `password`.

    Формат формы нужен, чтобы работала кнопка Authorize в Swagger UI.
    После нескольких неудачных попыток — 429 с заголовком `Retry-After`.
    """
    return await service.login(form.username, form.password, get_client_ip(request))


@router.post("/refresh", response_model=TokenSchema)
async def refresh(
        data: RefreshSchema,
        service: AuthService = Depends(get_auth_service),
):
    """
    Обменять refresh-токен на новую пару токенов.

    Refresh одноразовый: использованный токен больше не работает, сохрани новый.
    """
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
        data: LogoutSchema | None = None,
        current: AuthenticatedUser = Depends(get_current_user),
        service: AuthService = Depends(get_auth_service),
):
    """Выход: отзывает текущий access-токен и, если передан, refresh-токен."""
    await service.logout(current, data.refresh_token if data else None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserReadSchema)
async def me(
        current: AuthenticatedUser = Depends(get_current_user),
        service: AuthService = Depends(get_auth_service),
):
    """Текущий пользователь."""
    user = await service.get_user(current.id)
    return UserReadSchema.model_validate(user, from_attributes=True)
