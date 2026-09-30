from datetime import timedelta
from typing import Optional

from common import (
    AuthenticatedUser,
    JWTService,
    PasswordService,
    TokenBlacklist,
    get_logger,
    seconds_until,
)

from app.core.config import settings
from app.domain.entities.user import UserEntity
from app.domain.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.domain.interfaces.user_repository import IUserRepository
from app.infrastructure.cache.login_rate_limiter import LoginRateLimiter

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
    def __init__(
            self,
            user_repo: IUserRepository,
            jwt_service: JWTService,
            blacklist: TokenBlacklist,
            login_limiter: LoginRateLimiter,
    ):
        self.user_repo = user_repo
        self.jwt = jwt_service
        self.blacklist = blacklist
        self.login_limiter = login_limiter

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

    async def login(self, email: str, password: str, ip: str) -> dict:
        """Вход с защитой от подбора: при превышении попыток пароль даже не проверяется."""
        email = self._normalize_email(email)
        await self.login_limiter.check(ip, email)
        try:
            user = await self.authenticate(email, password)
        except UnauthorizedError:
            await self.login_limiter.record_failure(ip, email)
            raise
        await self.login_limiter.reset(ip, email)
        return self.issue_tokens(user)

    def issue_tokens(self, user: UserEntity) -> dict:
        access = self.jwt.create_access_token(
            user.id, DEFAULT_ROLE, timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh = self.jwt.create_refresh_token(
            user.id, DEFAULT_ROLE, timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

    async def refresh(self, refresh_token: str) -> dict:
        """
        Обменять refresh-токен на НОВУЮ пару токенов. Refresh одноразовый:
        старый сразу отзывается, повторное предъявление отклоняется.
        """
        payload = self.jwt.verify_token(refresh_token, "refresh")
        jti = payload.get("jti") if payload else None
        if not jti:  # неверный/просроченный токен или выданный до появления jti
            raise UnauthorizedError("Invalid refresh token")

        try:
            user = await self.user_repo.get_by_id(int(payload["sub"]))
        except (KeyError, TypeError, ValueError):
            user = None
        if not user:  # пользователь удалён
            raise UnauthorizedError("Invalid refresh token")

        # Атомарно «погасить» токен: из двух параллельных обменов пройдёт один
        if not await self.blacklist.revoke(jti, seconds_until(payload.get("exp"))):
            logger.warning(f"Refresh token reuse detected: user_id={user.id}")
            raise UnauthorizedError("Invalid refresh token")

        return self.issue_tokens(user)

    async def logout(self, current: AuthenticatedUser, refresh_token: Optional[str] = None) -> None:
        """Отозвать текущий access-токен и (если передан) refresh-токен этого же пользователя."""
        if current.token_id:
            await self.blacklist.revoke(current.token_id, seconds_until(current.token_expires_at))

        if refresh_token:
            payload = self.jwt.verify_token(refresh_token, "refresh")
            # чужой или невалидный refresh молча игнорируем: отзывать можно только свои токены
            if payload and payload.get("jti") and payload.get("sub") == str(current.id):
                await self.blacklist.revoke(payload["jti"], seconds_until(payload.get("exp")))

    async def get_user(self, user_id: int) -> UserEntity:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User no longer exists")
        return user
