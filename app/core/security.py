from common import JWTService, TokenBlacklist, create_auth_dependency

from app.core.config import settings

jwt_service = JWTService(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)

# Отозванные токены (logout, ротация refresh) — по jti в Redis
token_blacklist = TokenBlacklist()

# FastAPI-зависимость «текущий пользователь» (Bearer access-токен, отозванные отклоняются)
get_current_user = create_auth_dependency(
    jwt_service, token_url="/auth/login", is_revoked=token_blacklist.is_revoked,
)
