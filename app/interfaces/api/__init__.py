from fastapi import APIRouter
from app.interfaces.api.book_routes import router as books_router
from app.interfaces.api.reading_entry_routes import router as reading_entries_router
from app.interfaces.api.taste_profile_routes import router as taste_profile_router
from app.interfaces.api.recommendation_routes import router as recommendations_router

api_router = APIRouter()
api_router.include_router(reading_entries_router)
api_router.include_router(books_router)
api_router.include_router(taste_profile_router)
api_router.include_router(recommendations_router)

__all__ = ["api_router"]