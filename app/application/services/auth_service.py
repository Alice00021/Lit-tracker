from datetime import timedelta

from common import JWTService, PasswordService, get_logger

from app.core.config import settings
from app.domain.entities.user import UserEntity
from app.domain.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.domain.interfaces.user_repository import IUserRepository

logger = get_logger(__name__)

# Роль зашита в токен (формат common.JWTService); в проекте пока одна роль
DEFAULT_ROLE = "user"
# bcrypt учитывает только первые 72 байта пароля
MAX_PASSWORD_BYTES = 72

_dummy_hash: str | None = None


def _get_dummy_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = PasswordService.hash_password("dummy-password-for-timing")
    return _dummy_hash


class AuthService:
    def __init__(self, user_repo: IUserRepository, jwt_service: JWTService):
        self.user_repo = user_repo
        self.jwt = jwt_service

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    async def register(self, email: str, password: str) -> UserEntity:
        if len(password.encode()) > MAX_PASSWORD_BYTES:
            raise ValidationError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        ok, reason = PasswordService.validate_password_strength(password)
        if not ok:
            raise ValidationError(reason)

        email = self._normalize_email(email)
        if await self.user_repo.get_by_email(email):
            raise ConflictError("Email already registered")

        user = await self.user_repo.create(email, PasswordService.hash_password(password))
        logger.info(f"User registered: id={user.id}")
        return user

    async def authenticate(self, email: str, password: str) -> UserEntity:
        """Проверить email+пароль. Причину отказа наружу не раскрываем."""
        user = await self.user_repo.get_by_email(self._normalize_email(email))

        # Хеш проверяем всегда (даже для несуществующего email), чтобы время ответа
        # не выдавало, зарегистрирован ли адрес.
        hashed = user.hashed_password if user else _get_dummy_hash()
        try:
            valid = PasswordService.verify_password(password, hashed)
        except ValueError:  # в БД лежит не bcrypt-хеш (например, заглушка из старого seed)
            valid = False

        if not user or not valid:
            raise UnauthorizedError("Incorrect email or password")
        return user

    def issue_tokens(self, user: UserEntity) -> dict:
        access = self.jwt.create_access_token(
            user.id, DEFAULT_ROLE, timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh = self.jwt.create_refresh_token(
            user.id, DEFAULT_ROLE, timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

    async def refresh_access_token(self, refresh_token: str) -> dict:
        payload = self.jwt.verify_token(refresh_token, "refresh")
        user = None
        if payload:
            try:
                user = await self.user_repo.get_by_id(int(payload["sub"]))
            except (KeyError, TypeError, ValueError):
                user = None
        if not user:  # токен неверный/просрочен или пользователь удалён
            raise UnauthorizedError("Invalid refresh token")

        access = self.jwt.create_access_token(
            user.id, DEFAULT_ROLE, timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access, "token_type": "bearer"}

    async def get_user(self, user_id: int) -> UserEntity:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User no longer exists")
        return user
