from common import JWTService, create_auth_dependency

from app.core.config import settings

jwt_service = JWTService(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)

# FastAPI-зависимость «текущий пользователь» (из Bearer access-токена)
get_current_user = create_auth_dependency(jwt_service, token_url="/auth/login")
