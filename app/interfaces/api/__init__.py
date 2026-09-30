from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.interfaces.api.auth_routes import router as auth_router
from app.interfaces.api.book_routes import router as books_router
from app.interfaces.api.reading_entry_routes import router as reading_entries_router
from app.interfaces.api.recommendation_routes import router as recommendations_router
from app.interfaces.api.smart_search_routes import router as smart_search_router
from app.interfaces.api.taste_profile_routes import router as taste_profile_router

api_router = APIRouter()

# Публичные: регистрация и вход
api_router.include_router(auth_router)

# Всё остальное — только с валидным access-токеном
protected = [Depends(get_current_user)]
api_router.include_router(reading_entries_router, dependencies=protected)
api_router.include_router(books_router, dependencies=protected)
api_router.include_router(taste_profile_router, dependencies=protected)
api_router.include_router(recommendations_router, dependencies=protected)
api_router.include_router(smart_search_router, dependencies=protected)

__all__ = ["api_router"]
